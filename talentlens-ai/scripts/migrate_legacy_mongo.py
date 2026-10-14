"""One-off migration from the Spring Boot era MongoDB layout to the current stores.

Before the backend moved to FastAPI, everything lived in MongoDB: the collections
`users`, `searches`, `sourcing_tasks`, `share_requests` and `candidates`, keyed by
ObjectId. This script moves the first four into PostgreSQL and re-keys the
candidates to the new search ids.

Run from talentlens-ai/:

    uv run python -m scripts.migrate_legacy_mongo            # dry run: reports, writes nothing
    uv run python -m scripts.migrate_legacy_mongo --apply    # performs the migration

Where it reads and writes (environment or .env):

    LEGACY_MONGODB_URI, LEGACY_MONGODB_DATABASE   source; default to MONGODB_URI / MONGODB_DATABASE
    DATABASE_URL                                  target PostgreSQL
    MONGODB_URI, MONGODB_DATABASE                 target MongoDB (candidates)

If source and target MongoDB are the same database, candidates are re-keyed in
place; otherwise they are copied. Legacy users/searches/tasks/share-request
collections are only ever read.

Safe to re-run: new ids are derived from the legacy ids, so rows that already
exist are left alone and only what is missing is added. Passwords keep working
(bcrypt hashes are carried over as-is); everyone has to sign in again.

The legacy collections are read with plain pymongo because they have no model in
this codebase; everything written goes through the ORM/ODM models.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, TypeVar

from beanie import init_beanie
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError
from sqlalchemy import select
from sqlalchemy.exc import DataError, DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.documents import CandidateDocument
from app.db.models import (
    AuthProvider,
    Role,
    Search,
    SearchShare,
    ShareRequest,
    ShareRequestStatus,
    SourcingStatus,
    SourcingTask,
    TaskStatus,
    User,
)
from app.db.postgres import Base, dispose_engine, init_engine, session_factory
from app.models.jd_models import ParsedJdModel


LEGACY_COLLECTIONS = ("users", "searches", "sourcing_tasks", "share_requests", "candidates")

# Fixed namespace: the same legacy id always maps to the same new id, which is
# what makes the migration repeatable.
_ID_NAMESPACE = uuid.UUID("6f0d7c1e-3b52-4c8a-9a51-1f4d5e0b7a2c")
_INTERRUPTED = "Interrupted before the data was migrated"
_MAX_REPORTED = 10

E = TypeVar("E", bound=Enum)


class LegacySource(BaseSettings):
    uri: Optional[str] = Field(default=None, alias="LEGACY_MONGODB_URI")
    database: Optional[str] = Field(default=None, alias="LEGACY_MONGODB_DATABASE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@dataclass
class Tally:
    label: str
    migrated: int = 0
    already_present: int = 0
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def skip(self, legacy_id: Any, reason: str) -> None:
        self.skipped.append(f"{legacy_id}: {reason}")

    def lines(self, verb: str) -> list[str]:
        out = [
            f"{self.label:<15} {self.migrated:>6} {verb}, {self.already_present} already present, "
            f"{len(self.skipped)} skipped"
        ]
        out += [f"    note: {note}" for note in self.notes]
        out += [f"    skipped {entry}" for entry in self.skipped[:_MAX_REPORTED]]
        if len(self.skipped) > _MAX_REPORTED:
            out.append(f"    ... and {len(self.skipped) - _MAX_REPORTED} more")
        return out


def derive_id(kind: str, legacy_id: str) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, f"{kind}:{legacy_id}"))


def as_text(value: Any) -> Optional[str]:
    """Legacy references are ObjectId hex strings, occasionally real ObjectIds."""
    return None if value is None else str(value)


def as_datetime(value: Any, fallback: datetime) -> datetime:
    if not isinstance(value, datetime):
        return fallback
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def parse_enum(enum_cls: type[E], value: Any) -> Optional[E]:
    try:
        return enum_cls(str(value))
    except ValueError:
        return None


def without_nulls(document: dict[str, Any]) -> dict[str, Any]:
    """Drop nulls (so model defaults apply) and Spring Data's `_class` marker."""
    return {key: value for key, value in document.items() if value is not None and key != "_class"}


def mask(uri: str) -> str:
    return re.sub(r"//[^@/]+@", "//***@", uri).split("?", 1)[0]


def _db_error(exc: DBAPIError) -> str:
    return str(exc.orig).strip().splitlines()[0]


async def _insert(session: AsyncSession, entity: Any) -> Optional[str]:
    """Insert one row in its own savepoint; a rejected row must not sink the rest.

    Only constraint and data errors count as "this row is bad". Anything else
    (a dropped connection, say) propagates and aborts the run.
    """
    try:
        async with session.begin_nested():
            session.add(entity)
            await session.flush()
    except (IntegrityError, DataError) as exc:
        return _db_error(exc)
    return None


async def migrate_users(session: AsyncSession, source: AsyncDatabase) -> tuple[dict[str, str], Tally]:
    tally = Tally("users")
    mapping: dict[str, str] = {}
    existing_ids = set(await session.scalars(select(User.id)))
    taken_emails = set(await session.scalars(select(User.email)))
    now = datetime.now(timezone.utc)

    # Oldest first, so that if two legacy accounts differ only by letter case the original one wins.
    async for doc in source["users"].find().sort([("createdAt", 1), ("_id", 1)]):
        legacy_id = str(doc["_id"])
        target_id = derive_id("user", legacy_id)
        if target_id in existing_ids:
            mapping[legacy_id] = target_id
            tally.already_present += 1
            continue

        email = str(doc.get("email") or "").strip().lower()
        role = parse_enum(Role, doc.get("role"))
        if not email:
            tally.skip(legacy_id, "no email")
            continue
        if role is None:
            tally.skip(legacy_id, f"unknown role {doc.get('role')!r} ({email})")
            continue
        if email in taken_emails:
            # Never merged automatically: emails were not verified at registration,
            # so a matching address does not prove it is the same person.
            tally.skip(legacy_id, f"email {email} already belongs to another account")
            continue

        password_hash = doc.get("password") or None
        google_id = doc.get("googleId") or None
        providers = [p for p in doc.get("authProviders") or [] if parse_enum(AuthProvider, p)]
        if not providers:
            providers = [AuthProvider.GOOGLE.value if google_id and not password_hash else AuthProvider.LOCAL.value]

        created_at = as_datetime(doc.get("createdAt"), now)
        error = await _insert(
            session,
            User(
                id=target_id,
                email=email,
                password_hash=password_hash,
                name=str(doc.get("name") or email)[:200],
                role=role,
                google_id=google_id,
                auth_providers=providers,
                email_verified=bool(doc.get("emailVerified", False)),
                avatar_url=doc.get("avatarUrl") or None,
                created_at=created_at,
                updated_at=as_datetime(doc.get("updatedAt"), created_at),
            ),
        )
        if error:
            tally.skip(legacy_id, f"{email}: {error}")
            continue

        mapping[legacy_id] = target_id
        taken_emails.add(email)
        tally.migrated += 1
    return mapping, tally


async def migrate_searches(
    session: AsyncSession, source: AsyncDatabase, users: dict[str, str]
) -> tuple[dict[str, str], Tally]:
    tally = Tally("searches")
    mapping: dict[str, str] = {}
    existing_ids = set(await session.scalars(select(Search.id)))
    now = datetime.now(timezone.utc)
    interrupted = dropped_shares = 0

    async for doc in source["searches"].find().sort([("createdAt", 1), ("_id", 1)]):
        legacy_id = str(doc["_id"])
        target_id = derive_id("search", legacy_id)
        if target_id in existing_ids:
            mapping[legacy_id] = target_id
            tally.already_present += 1
            continue

        owner_id = users.get(as_text(doc.get("userId")) or "")
        if owner_id is None:
            tally.skip(legacy_id, f"owner {doc.get('userId')} was not migrated")
            continue
        try:
            parsed_jd = ParsedJdModel.model_validate(without_nulls(doc.get("parsedJd") or {}))
        except ValidationError as exc:
            tally.skip(legacy_id, f"parsedJd is not usable ({exc.errors()[0]['msg']})")
            continue

        status = parse_enum(SourcingStatus, doc.get("sourcingStatus")) or SourcingStatus.IDLE
        if status == SourcingStatus.IN_PROGRESS:
            # The process that was running it no longer exists; left as-is it could never be re-run.
            status = SourcingStatus.FAILED
            interrupted += 1

        shared_with = [as_text(user_id) or "" for user_id in doc.get("sharedWith") or []]
        grantees = list(dict.fromkeys(users[u] for u in shared_with if u in users and users[u] != owner_id))
        dropped_shares += sum(1 for u in shared_with if u not in users)

        created_at = as_datetime(doc.get("createdAt"), now)
        error = await _insert(
            session,
            Search(
                id=target_id,
                user_id=owner_id,
                title=str(doc.get("title") or "Search")[:300],
                raw_jd_text=doc.get("rawJdText"),
                jd_file_name=doc.get("jdFileName"),
                parsed_jd=parsed_jd.model_dump(mode="json"),
                sourcing_status=status,
                sourcing_platforms=[str(p) for p in doc.get("sourcingPlatforms") or []],
                candidate_count=int(doc.get("candidateCount") or 0),
                created_at=created_at,
                updated_at=as_datetime(doc.get("updatedAt"), created_at),
                shares=[SearchShare(user_id=user_id, created_at=created_at) for user_id in grantees],
            ),
        )
        if error:
            tally.skip(legacy_id, error)
            continue

        mapping[legacy_id] = target_id
        tally.migrated += 1

    if interrupted:
        tally.notes.append(f"{interrupted} search(es) caught mid-sourcing: marked FAILED so they can be re-run")
    if dropped_shares:
        tally.notes.append(f"{dropped_shares} share grant(s) to users that are not migrated: dropped")
    return mapping, tally


async def migrate_tasks(session: AsyncSession, source: AsyncDatabase, searches: dict[str, str]) -> Tally:
    tally = Tally("sourcing tasks")
    existing_ids = set(await session.scalars(select(SourcingTask.id)))
    now = datetime.now(timezone.utc)

    async for doc in source["sourcing_tasks"].find().sort([("startedAt", 1), ("_id", 1)]):
        legacy_id = str(doc["_id"])
        target_id = derive_id("task", legacy_id)
        if target_id in existing_ids:
            tally.already_present += 1
            continue

        search_id = searches.get(as_text(doc.get("searchId")) or "")
        if search_id is None:
            tally.skip(legacy_id, f"search {doc.get('searchId')} was not migrated")
            continue

        status = parse_enum(TaskStatus, doc.get("status")) or TaskStatus.FAILED
        error_text = doc.get("error")
        started_at = as_datetime(doc.get("startedAt"), now)
        completed_at = doc.get("completedAt")
        if status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
            status, error_text, completed_at = TaskStatus.FAILED, error_text or _INTERRUPTED, completed_at or now

        error = await _insert(
            session,
            SourcingTask(
                id=target_id,
                search_id=search_id,
                run_id=str(doc.get("runId") or "run_unknown")[:64],
                platforms=[str(p) for p in doc.get("platforms") or []],
                status=status,
                candidates_found=int(doc.get("candidatesFound") or 0),
                error=error_text,
                started_at=started_at,
                completed_at=as_datetime(completed_at, now) if completed_at else None,
            ),
        )
        if error:
            tally.skip(legacy_id, error)
        else:
            tally.migrated += 1
    return tally


async def migrate_share_requests(
    session: AsyncSession, source: AsyncDatabase, users: dict[str, str], searches: dict[str, str]
) -> Tally:
    tally = Tally("share requests")
    existing_ids = set(await session.scalars(select(ShareRequest.id)))
    now = datetime.now(timezone.utc)

    async for doc in source["share_requests"].find().sort([("requestedAt", 1), ("_id", 1)]):
        legacy_id = str(doc["_id"])
        target_id = derive_id("share-request", legacy_id)
        if target_id in existing_ids:
            tally.already_present += 1
            continue

        search_id = searches.get(as_text(doc.get("searchId")) or "")
        requester_id = users.get(as_text(doc.get("requesterUserId")) or "")
        owner_id = users.get(as_text(doc.get("ownerUserId")) or "")
        status = parse_enum(ShareRequestStatus, doc.get("status"))
        missing = [
            name
            for name, value in (("search", search_id), ("requester", requester_id), ("owner", owner_id), ("status", status))
            if value is None
        ]
        if missing:
            tally.skip(legacy_id, f"{', '.join(missing)} not available after migration")
            continue

        resolved_at = doc.get("resolvedAt")
        note = doc.get("note")
        error = await _insert(
            session,
            ShareRequest(
                id=target_id,
                search_id=search_id,
                requester_user_id=requester_id,
                owner_user_id=owner_id,
                status=status,
                requested_at=as_datetime(doc.get("requestedAt"), now),
                resolved_at=as_datetime(resolved_at, now) if resolved_at else None,
                resolved_by=users.get(as_text(doc.get("resolvedBy")) or ""),
                note=str(note)[:500] if note else None,
            ),
        )
        if error:
            tally.skip(legacy_id, error)
        else:
            tally.migrated += 1
    return tally


async def migrate_candidates(
    source: AsyncDatabase, searches: dict[str, str], known_search_ids: set[str], *, apply: bool
) -> Tally:
    """Re-key each legacy candidate to its search's new id, keeping its own `_id`.

    Writing by `_id` covers both layouts with one code path: in the same database it
    updates the document where it is, in a different one it inserts a copy.
    """
    tally = Tally("candidates")

    for legacy_search_id, target_search_id in searches.items():
        # Materialised first: the documents leave this query's result set as they are re-keyed.
        legacy_docs = await source["candidates"].find({"searchId": legacy_search_id}).to_list()
        if not legacy_docs:
            continue
        in_target = {c.id for c in await CandidateDocument.find({"searchId": target_search_id}).to_list()}

        for raw in legacy_docs:
            if raw["_id"] in in_target:
                tally.already_present += 1
                continue
            try:
                candidate = CandidateDocument.model_validate({**without_nulls(raw), "searchId": target_search_id})
            except ValidationError as exc:
                problem = exc.errors()[0]
                where = ".".join(str(part) for part in problem["loc"])
                tally.skip(raw["_id"], f"does not fit the candidate model ({where}: {problem['msg']})")
                continue
            if apply:
                try:
                    await candidate.save()
                except DuplicateKeyError:
                    tally.skip(raw["_id"], "the same profile already exists for this search run in the target")
                    continue
            tally.migrated += 1

    accounted_for = list(searches) + list(known_search_ids)
    orphaned = await source["candidates"].count_documents({"searchId": {"$nin": accounted_for}})
    if orphaned:
        tally.notes.append(f"{orphaned} candidate(s) belong to searches that are not migrated: left untouched")
    return tally


async def run(apply: bool) -> int:
    settings = get_settings()
    legacy = LegacySource()
    source_uri = legacy.uri or settings.mongodb_uri
    source_name = legacy.database or settings.mongodb_database

    source_client = AsyncMongoClient(source_uri, tz_aware=True)
    target_client = AsyncMongoClient(settings.mongodb_uri, tz_aware=True)
    try:
        await source_client.admin.command("ping")
        await target_client.admin.command("ping")
        source = source_client[source_name]
        same_database = (
            sorted(source_client.nodes) == sorted(target_client.nodes) and source_name == settings.mongodb_database
        )

        print(f"mode             {'APPLY' if apply else 'DRY RUN (nothing will be written)'}")
        print(f"source MongoDB   {mask(source_uri)}  db={source_name}")
        print(f"target Postgres  {mask(settings.database_url)}")
        print(f"target MongoDB   {mask(settings.mongodb_uri)}  db={settings.mongodb_database}")
        print(f"candidates       {'re-keyed in place (same database)' if same_database else 'copied to the target'}")
        print()

        present = set(await source.list_collection_names())
        if not {"users", "searches"} & present:
            print(f"No legacy data found: db '{source_name}' has no 'users' or 'searches' collection.")
            print("Set LEGACY_MONGODB_URI / LEGACY_MONGODB_DATABASE to the old Spring Boot database.")
            return 1
        for name in LEGACY_COLLECTIONS:
            print(f"found {name:<15} {await source[name].count_documents({}):>6} document(s)")
        print()

        # A dry run must not even create indexes.
        await init_beanie(
            database=target_client[settings.mongodb_database],
            document_models=[CandidateDocument],
            skip_indexes=not apply,
        )
        init_engine(settings.database_url)

        async with session_factory()() as session:
            # Inside the transaction, so a dry run rolls the table creation back too.
            await session.run_sync(lambda sync_session: Base.metadata.create_all(sync_session.connection()))

            users, user_tally = await migrate_users(session, source)
            searches, search_tally = await migrate_searches(session, source, users)
            task_tally = await migrate_tasks(session, source, searches)
            request_tally = await migrate_share_requests(session, source, users, searches)
            known_search_ids = set(await session.scalars(select(Search.id)))

            if apply:
                await session.commit()
            else:
                await session.rollback()

        # After the commit: candidates must never point at a search that failed to land.
        candidate_tally = await migrate_candidates(source, searches, known_search_ids, apply=apply)

        verb = "migrated" if apply else "would be migrated"
        for tally in (user_tally, search_tally, task_tally, request_tally, candidate_tally):
            print("\n".join(tally.lines(verb)))
        print()
        if apply:
            print("Done. Everyone signs in again with their existing password or Google account.")
        else:
            print("Dry run only. Re-run with --apply to perform the migration.")
        return 0
    finally:
        await dispose_engine()
        await source_client.close()
        await target_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the changes (default is a dry run)")
    sys.exit(asyncio.run(run(parser.parse_args().apply)))


if __name__ == "__main__":
    main()
