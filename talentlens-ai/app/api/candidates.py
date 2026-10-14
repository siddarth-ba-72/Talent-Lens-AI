from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.searches import is_descending
from app.db.models import User
from app.db.postgres import get_session
from app.models.candidate_models import CandidateResponse
from app.models.common_models import PageResponse
from app.security.auth import get_current_user, require_recruiter
from app.services import candidate_service, export_service
from app.services.candidate_service import CandidateFilterParams


router = APIRouter(prefix="/api/searches/{search_id}/candidates", tags=["candidates"])


def candidate_filters(
    skill: list[str] = Query(default_factory=list),
    source: Optional[str] = None,
    minScore: Optional[int] = None,
    maxScore: Optional[int] = None,
    keyword: Optional[str] = None,
    runId: Optional[str] = None,
) -> CandidateFilterParams:
    return CandidateFilterParams(
        skills=skill, source=source, min_score=minScore, max_score=maxScore, keyword=keyword, run_id=runId
    )


@router.get("", response_model=PageResponse[CandidateResponse])
async def list_candidates(
    search_id: str,
    params: CandidateFilterParams = Depends(candidate_filters),
    sortBy: str = "matchScore",
    sortOrder: Optional[str] = None,
    sortDir: Optional[str] = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PageResponse[CandidateResponse]:
    candidates, total = await candidate_service.list_candidates(
        session,
        user,
        search_id,
        params,
        page=page,
        size=size,
        sort_by=sortBy,
        descending=is_descending(sortOrder, sortDir),
    )
    return PageResponse.of([candidate_service.to_response(c) for c in candidates], total, page, size)


@router.get("/export")
async def export_candidates(
    search_id: str,
    export_format: Optional[str] = Query(default=None, alias="format"),
    params: CandidateFilterParams = Depends(candidate_filters),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    resolved = export_service.resolve_format(export_format)
    canonical_id, candidates = await candidate_service.find_all(session, user, search_id, params)
    return Response(
        content=export_service.render(resolved, candidates),
        media_type=export_service.media_type(resolved),
        headers={"Content-Disposition": f'attachment; filename="candidates-{canonical_id}.{resolved}"'},
    )


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_candidate(
    search_id: str,
    candidate_id: str,
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
) -> None:
    await candidate_service.soft_delete(session, user, search_id, candidate_id)
