from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.documents import CandidateDocument
from app.db.models import Role, Search, SearchShare, SourcingStatus, User
from app.errors import (
    AiServiceError,
    FileTooLargeError,
    ForbiddenError,
    InvalidFileError,
    ResourceNotFoundError,
)
from app.models.jd_models import ParsedJdModel
from app.services.jd_parser_service import JdParserService


logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# Kept under Vercel's 4.5 MB request body cap, which rejects larger uploads before they reach the app.
MAX_JD_FILE_BYTES = 4 * 1024 * 1024

_SORT_COLUMNS = {
    "createdAt": Search.created_at,
    "updatedAt": Search.updated_at,
    "title": Search.title,
    "candidateCount": Search.candidate_count,
    "sourcingStatus": Search.sourcing_status,
}
_TITLE_BASE_MAX_CHARS = 200


@dataclass
class SearchFilterParams:
    keyword: Optional[str] = None
    statuses: list[str] = field(default_factory=list)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


def normalize_id(value: str) -> Optional[str]:
    """Canonical form of an entity id, or None when the value cannot be one."""
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        return None


def like_pattern(keyword: str) -> str:
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def get_search_or_404(session: AsyncSession, search_id: str, *, for_update: bool = False) -> Search:
    normalized = normalize_id(search_id)
    search = await session.get(Search, normalized, with_for_update=for_update) if normalized else None
    if search is None:
        raise ResourceNotFoundError(f"Search not found: {search_id}")
    return search


def assert_ownership(search: Search, user: User) -> None:
    if search.user_id != user.id:
        raise ForbiddenError("Access denied")


def can_view(search: Search, user: User) -> bool:
    return search.user_id == user.id or user.id in search.shared_with


async def get_viewable_search(session: AsyncSession, user: User, search_id: str) -> Search:
    """Load a search the user owns or has been granted; anything else is a 404."""
    search = await get_search_or_404(session, search_id)
    if not can_view(search, user):
        raise ResourceNotFoundError(f"Search not found: {search_id}")
    return search


async def create_search(
    session: AsyncSession,
    settings: Settings,
    parser: JdParserService,
    user: User,
    *,
    jd_file: Optional[UploadFile] = None,
    jd_text: Optional[str] = None,
) -> Search:
    if jd_file is not None and jd_file.size:
        _validate_file(jd_file)
        parsed_jd = await _parse(settings, parser.parse_jd_file(jd_file))
    elif jd_text and jd_text.strip():
        parsed_jd = await _parse(settings, asyncio.to_thread(parser.parse_jd_text, jd_text))
    else:
        raise InvalidFileError("Either jdText or jdFile must be provided")

    search = Search(
        user_id=user.id,
        title=_derive_title(parsed_jd),
        raw_jd_text=jd_text,
        jd_file_name=jd_file.filename if jd_file is not None else None,
        parsed_jd=parsed_jd.model_dump(mode="json"),
        sourcing_status=SourcingStatus.IDLE,
        sourcing_platforms=[],
        candidate_count=0,
        # Set explicitly: an unloaded relationship would lazy-load, which async sessions forbid.
        shares=[],
    )
    session.add(search)
    await session.commit()
    return search


async def list_searches(
    session: AsyncSession,
    user: User,
    params: SearchFilterParams,
    *,
    page: int,
    size: int,
    sort_by: str,
    descending: bool,
) -> tuple[list[Search], int]:
    conditions = []
    if user.role == Role.HIRING_MANAGER:
        shared_ids = select(SearchShare.search_id).where(SearchShare.user_id == user.id)
        conditions.append(Search.id.in_(shared_ids))
    else:
        conditions.append(Search.user_id == user.id)

    if params.keyword and params.keyword.strip():
        pattern = like_pattern(params.keyword.strip())
        conditions.append(
            or_(Search.title.ilike(pattern, escape="\\"), Search.raw_jd_text.ilike(pattern, escape="\\"))
        )
    if params.statuses:
        conditions.append(Search.sourcing_status.in_(params.statuses))
    if params.date_from is not None:
        conditions.append(Search.created_at >= params.date_from)
    if params.date_to is not None:
        conditions.append(Search.created_at <= params.date_to)

    total = await session.scalar(select(func.count()).select_from(Search).where(*conditions)) or 0

    column = _SORT_COLUMNS.get(sort_by, Search.created_at)
    ordering = column.desc() if descending else column.asc()
    rows = await session.scalars(
        select(Search).where(*conditions).order_by(ordering, Search.id).offset(page * size).limit(size)
    )
    return list(rows), total


async def get_search(session: AsyncSession, user: User, search_id: str) -> Search:
    search = await get_search_or_404(session, search_id)
    if user.role == Role.HIRING_MANAGER:
        if user.id not in search.shared_with:
            raise ResourceNotFoundError(f"Search not found: {search_id}")
    else:
        assert_ownership(search, user)
    return search


async def delete_search(session: AsyncSession, user: User, search_id: str) -> None:
    search = await get_search_or_404(session, search_id)
    assert_ownership(search, user)

    # Sourcing tasks, shares and share requests go with the row (ON DELETE CASCADE).
    await session.delete(search)
    await session.commit()
    await CandidateDocument.find({"searchId": search.id}).delete()


def _validate_file(jd_file: UploadFile) -> None:
    if jd_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidFileError("Unsupported file type. Allowed: .txt, .pdf, .docx")
    if jd_file.size is not None and jd_file.size > MAX_JD_FILE_BYTES:
        raise FileTooLargeError("File size exceeds the 4MB limit")


async def _parse(settings: Settings, parsing) -> ParsedJdModel:
    try:
        return await asyncio.wait_for(parsing, timeout=settings.jd_parse_timeout_seconds)
    except ValueError as exc:
        raise InvalidFileError(str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise AiServiceError("AI service is unavailable") from exc
    except Exception as exc:
        logger.error("JD parsing failed", exc_info=exc)
        raise AiServiceError("AI service is unavailable") from exc


def _derive_title(parsed_jd: ParsedJdModel) -> str:
    # Short slug from domain + experience level (falls back to "Search" if both are missing)
    parts = [
        re.sub(r"[^a-zA-Z0-9]+", "-", part.strip())
        for part in (parsed_jd.domain, parsed_jd.experienceLevel)
        if part and part.strip()
    ]
    base = "-".join(parts)[:_TITLE_BASE_MAX_CHARS] or "Search"
    return f"{base}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
