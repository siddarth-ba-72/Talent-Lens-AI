from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any, Optional

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.documents import CandidateDocument
from app.db.models import SourcingTask, TaskStatus, User
from app.errors import ForbiddenError, ResourceNotFoundError
from app.models.candidate_models import CandidateResponse
from app.services.search_service import get_viewable_search
from app.services.skill_vocabulary import canonical


_SORT_FIELDS = {"matchScore", "createdAt", "sourcedAt", "name"}


@dataclass
class CandidateFilterParams:
    skills: list[str] = field(default_factory=list)
    source: Optional[str] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    keyword: Optional[str] = None
    run_id: Optional[str] = None


def to_response(candidate: CandidateDocument) -> CandidateResponse:
    return CandidateResponse(
        id=str(candidate.id),
        searchId=candidate.searchId,
        runId=candidate.runId,
        name=candidate.name,
        email=candidate.email,
        avatarUrl=candidate.avatarUrl,
        profileUrl=candidate.profileUrl,
        source=candidate.source.value,
        sourceUsername=candidate.sourceUsername,
        skills=candidate.skills,
        bio=candidate.bio,
        location=candidate.location,
        signals=candidate.signals,
        openToWork=candidate.openToWork,
        matchScore=candidate.matchScore,
        scoreBreakdown=candidate.scoreBreakdown,
        sourcedAt=candidate.sourcedAt,
    )


def build_filter(search_id: str, params: CandidateFilterParams) -> dict[str, Any]:
    conditions: list[dict[str, Any]] = [{"searchId": search_id}, {"isActive": True}]

    if params.run_id:
        conditions.append({"runId": params.run_id})
    if params.skills:
        # Sourced skills are stored in canonical form ("postgresql"); older runs kept the platform's spelling.
        wanted = list(dict.fromkeys([*params.skills, *(canonical(skill) for skill in params.skills)]))
        conditions.append({"skills": {"$in": wanted}})
    if params.source and params.source.strip():
        conditions.append({"source": params.source})
    if params.min_score is not None:
        conditions.append({"matchScore": {"$gte": params.min_score}})
    if params.max_score is not None:
        conditions.append({"matchScore": {"$lte": params.max_score}})
    if params.keyword and params.keyword.strip():
        # Escaped so the keyword is matched literally, not run as a user-supplied regex.
        pattern = {"$regex": re.escape(params.keyword.strip()), "$options": "i"}
        conditions.append({"$or": [{"name": pattern}, {"bio": pattern}, {"sourceUsername": pattern}]})

    return {"$and": conditions}


async def latest_completed_run_id(session: AsyncSession, search_id: str) -> Optional[str]:
    return await session.scalar(
        select(SourcingTask.run_id)
        .where(SourcingTask.search_id == search_id, SourcingTask.status == TaskStatus.COMPLETED)
        .order_by(SourcingTask.started_at.desc(), SourcingTask.id)
        .limit(1)
    )


async def _with_default_run(session: AsyncSession, search_id: str, params: CandidateFilterParams) -> CandidateFilterParams:
    """Without an explicit run, use the latest completed one (or every run, before any has completed)."""
    if params.run_id:
        return params
    return replace(params, run_id=await latest_completed_run_id(session, search_id))


async def list_candidates(
    session: AsyncSession,
    user: User,
    search_id: str,
    params: CandidateFilterParams,
    *,
    page: int,
    size: int,
    sort_by: str,
    descending: bool,
) -> tuple[list[CandidateDocument], int]:
    search = await get_viewable_search(session, user, search_id)
    query = build_filter(search.id, await _with_default_run(session, search.id, params))

    sort_field = sort_by if sort_by in _SORT_FIELDS else "matchScore"
    direction = DESCENDING if descending else ASCENDING
    candidates = (
        await CandidateDocument.find(query)
        .sort([(sort_field, direction), ("_id", ASCENDING)])
        .skip(page * size)
        .limit(size)
        .to_list()
    )
    total = await CandidateDocument.find(query).count()
    return candidates, total


async def find_all(
    session: AsyncSession, user: User, search_id: str, params: CandidateFilterParams
) -> tuple[str, list[CandidateDocument]]:
    """Every active candidate matching the filters, for export."""
    search = await get_viewable_search(session, user, search_id)
    query = build_filter(search.id, await _with_default_run(session, search.id, params))
    return search.id, await CandidateDocument.find(query).to_list()


async def soft_delete(session: AsyncSession, user: User, search_id: str, candidate_id: str) -> None:
    search = await get_viewable_search(session, user, search_id)
    if search.user_id != user.id:
        raise ForbiddenError("Only the search owner can delete candidates")

    candidate = None
    if ObjectId.is_valid(candidate_id):
        candidate = await CandidateDocument.find_one({"_id": ObjectId(candidate_id), "searchId": search.id})
    if candidate is None:
        raise ResourceNotFoundError(f"Candidate not found: {candidate_id}")

    candidate.isActive = False
    await candidate.save()
