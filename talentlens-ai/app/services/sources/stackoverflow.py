from __future__ import annotations

import asyncio
import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import as_so_tag, canonical, canonical_list, jd_terms, single_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    compact_number,
    parse_time,
    strip_html,
    truncate,
)


logger = logging.getLogger(__name__)

_API = "https://api.stackexchange.com/2.3"
_SITE = "stackoverflow"
# Default user fields plus `about_me`. Created once via /filters/create;
# filters are immutable, so the id never changes.
USER_FILTER = "!SyjNqbwGU2NWZ1y5pj"
_MAX_TAGS = 4
_ANSWERERS_PER_TAG = 20
_MAX_USERS = 25
_TOP_TAGS_PER_USER = 15
_CONCURRENCY = 5
_INACTIVE_AFTER = timedelta(days=365)


class _Api:
    """One run's Stack Exchange calls, honouring the API's `backoff` requests."""

    def __init__(self, client: httpx.AsyncClient, key: Optional[str]):
        self._client = client
        self._key = key
        self._backoff_until = 0.0
        self.quota_remaining: Optional[int] = None

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> list[dict]:
        loop = asyncio.get_running_loop()
        wait = self._backoff_until - loop.time()
        if wait > 0:
            await asyncio.sleep(wait)

        query = {"site": _SITE, **(params or {})}
        if self._key:
            query["key"] = self._key
        response = await self._client.get(f"{_API}{path}", params=query)
        body = response.json() if response.content else {}
        if body.get("backoff"):
            self._backoff_until = max(self._backoff_until, loop.time() + float(body["backoff"]))
        if "quota_remaining" in body:
            self.quota_remaining = body["quota_remaining"]
        if response.status_code >= 400 or body.get("error_id"):
            raise RuntimeError(f"Stack Exchange {path}: {body.get('error_message') or response.status_code}")
        return body.get("items", [])


class StackOverflowSourceToolAdapter(SourceToolAdapter):
    def __init__(self, key: Optional[str], transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.STACKOVERFLOW, transport)
        self._key = key

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        if not self._key:
            logger.warning("STACKEXCHANGE_KEY not set — Stack Overflow is limited to 300 requests/day per IP")

        async with self._client() as client:
            api = _Api(client, self._key)
            tags = await _resolve_tags(api, [*single_terms(query_terms), *jd_terms(parsed_jd)])
            if not tags:
                return []

            # Top answerers of all time: monthly lists are nearly empty for
            # most tags. Inactive accounts are dropped below instead.
            answerer_lists = await asyncio.gather(
                *(api.get(f"/tags/{quote(tag, safe='')}/top-answerers/all_time", {"pagesize": _ANSWERERS_PER_TAG})
                  for tag in tags),
                return_exceptions=True,
            )
            topped: dict[int, list[str]] = {}
            scores: dict[int, int] = {}
            for tag, answerers in zip(tags, answerer_lists):
                if isinstance(answerers, BaseException):
                    logger.warning("Stack Overflow top answerers for [%s] failed: %s", tag, answerers)
                    continue
                for item in answerers:
                    user = item.get("user") or {}
                    user_id = user.get("user_id")
                    if not user_id or user.get("user_type") != "registered":
                        continue
                    topped.setdefault(user_id, []).append(tag)
                    scores[user_id] = scores.get(user_id, 0) + int(item.get("score") or 0)
            if not topped:
                return []

            ids = ";".join(str(user_id) for user_id in topped)
            users = await api.get(f"/users/{ids}", {"filter": USER_FILTER, "pagesize": 100})
            cutoff = datetime.now(timezone.utc) - _INACTIVE_AFTER
            active = [user for user in users if _is_active(user, cutoff)]
            active.sort(key=lambda user: (-len(topped.get(user["user_id"], [])), -scores.get(user["user_id"], 0)))
            active = active[:_MAX_USERS]

            semaphore = asyncio.Semaphore(_CONCURRENCY)

            async def top_tags(user_id: int) -> list[str]:
                async with semaphore:
                    items = await api.get(f"/users/{user_id}/top-tags", {"pagesize": _TOP_TAGS_PER_USER})
                    return [item.get("tag_name", "") for item in items]

            tag_lists = await asyncio.gather(*(top_tags(user["user_id"]) for user in active), return_exceptions=True)

        if api.quota_remaining is not None:
            logger.info("Stack Exchange quota remaining: %s", api.quota_remaining)

        candidates = []
        for user, user_tags in zip(active, tag_lists):
            own_tags = topped.get(user["user_id"], [])
            skills = canonical_list([*own_tags, *([] if isinstance(user_tags, BaseException) else user_tags)])
            candidates.append(_to_candidate(user, own_tags, skills))
        logger.info("Stack Overflow adapter fetched %d candidates for tags %s", len(candidates), tags)
        return candidates


async def _resolve_tags(api: _Api, terms: list[str]) -> list[str]:
    """Up to _MAX_TAGS existing tags, in JD order. Synonyms resolve to their master tag."""
    wanted = list(dict.fromkeys(as_so_tag(term) for term in terms if term))[:20]
    if not wanted:
        return []
    try:
        items = await api.get(f"/tags/{';'.join(quote(tag, safe='') for tag in wanted)}/info", {"pagesize": 20})
    except Exception as exc:
        logger.warning("Stack Overflow tag lookup failed: %s", exc)
        return []

    # Returned names are master tags ("apache-kafka" for "kafka"); match on canonical form.
    by_canonical = {canonical(item["name"]): item["name"] for item in items if item.get("name")}
    resolved = [by_canonical[canonical(tag)] for tag in wanted if canonical(tag) in by_canonical]
    return list(dict.fromkeys(resolved))[:_MAX_TAGS]


def _is_active(user: dict, cutoff: datetime) -> bool:
    last_seen = parse_time(user.get("last_access_date"))
    return last_seen is None or last_seen > cutoff


def _to_candidate(user: dict, topped_tags: list[str], skills: list[str]) -> RawCandidate:
    name = html.unescape(user.get("display_name") or str(user["user_id"]))
    signals = [f"Top answerer in {', '.join(f'[{tag}]' for tag in topped_tags)}"]
    if user.get("reputation"):
        signals.append(f"Reputation {compact_number(int(user['reputation']))}")
    if user.get("website_url"):
        signals.append(f"Website: {user['website_url']}")

    return RawCandidate(
        name=name,
        profile_url=user.get("link") or f"https://stackoverflow.com/users/{user['user_id']}",
        # Display names aren't unique; the stored candidate key uses this field.
        source_username=str(user["user_id"]),
        source=SourcePlatform.STACKOVERFLOW,
        skills=skills,
        avatar_url=user.get("profile_image") or None,
        bio=truncate(strip_html(user.get("about_me")), 300),
        location=html.unescape(user["location"]) if user.get("location") else None,
        # Reputation measures answering, not seniority: scored as neutral.
        experience=None,
        signals=signals[:MAX_SIGNALS],
    )
