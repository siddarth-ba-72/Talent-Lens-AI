from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import User
from app.db.postgres import get_session
from app.dependencies import get_jd_parser_service
from app.models.common_models import PageResponse
from app.models.search_models import (
    CreateSearchRequest,
    SearchResponse,
    SearchSummaryResponse,
    SourcingRequest,
    SourcingStatusResponse,
)
from app.security.auth import get_current_user, require_recruiter
from app.services import search_service, sourcing_service
from app.services.jd_parser_service import JdParserService
from app.services.search_service import SearchFilterParams


router = APIRouter(prefix="/api/searches", tags=["searches"])


def is_descending(sort_order: Optional[str], sort_dir: Optional[str]) -> bool:
    return (sort_order or sort_dir or "desc").lower() == "desc"


@router.post("/jd-file", response_model=SearchResponse, status_code=status.HTTP_201_CREATED)
async def create_search_from_file(
    jdFile: UploadFile = File(...),
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    parser: JdParserService = Depends(get_jd_parser_service),
) -> SearchResponse:
    search = await search_service.create_search(session, settings, parser, user, jd_file=jdFile)
    return SearchResponse.from_search(search)


@router.post("/jd-text", response_model=SearchResponse, status_code=status.HTTP_201_CREATED)
async def create_search_from_text(
    request: CreateSearchRequest,
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    parser: JdParserService = Depends(get_jd_parser_service),
) -> SearchResponse:
    search = await search_service.create_search(session, settings, parser, user, jd_text=request.jdText)
    return SearchResponse.from_search(search)


@router.get("", response_model=PageResponse[SearchSummaryResponse])
async def list_searches(
    keyword: Optional[str] = None,
    status_filter: list[str] = Query(default_factory=list, alias="status"),
    dateFrom: Optional[datetime] = None,
    dateTo: Optional[datetime] = None,
    sortBy: str = "createdAt",
    sortOrder: Optional[str] = None,
    sortDir: Optional[str] = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PageResponse[SearchSummaryResponse]:
    params = SearchFilterParams(keyword=keyword, statuses=status_filter, date_from=dateFrom, date_to=dateTo)
    searches, total = await search_service.list_searches(
        session,
        user,
        params,
        page=page,
        size=size,
        sort_by=sortBy,
        descending=is_descending(sortOrder, sortDir),
    )
    items = [SearchSummaryResponse.from_search(search, include_parsed_jd=True) for search in searches]
    return PageResponse.of(items, total, page, size)


@router.get("/{search_id}", response_model=SearchResponse)
async def get_search(
    search_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    return SearchResponse.from_search(await search_service.get_search(session, user, search_id))


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_search(
    search_id: str,
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
) -> None:
    await search_service.delete_search(session, user, search_id)


@router.post("/{search_id}/source", response_model=SourcingStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sourcing(
    search_id: str,
    request: SourcingRequest,
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
) -> SourcingStatusResponse:
    task = await sourcing_service.trigger_sourcing(session, user, search_id, request.platforms)
    return SourcingStatusResponse.from_task(task)


@router.get("/{search_id}/source-status", response_model=SourcingStatusResponse)
async def get_source_status(
    search_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SourcingStatusResponse:
    return SourcingStatusResponse.from_task(await sourcing_service.get_status(session, user, search_id))


@router.get("/{search_id}/runs", response_model=list[SourcingStatusResponse])
async def list_sourcing_runs(
    search_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SourcingStatusResponse]:
    runs = await sourcing_service.list_runs(session, user, search_id)
    return [SourcingStatusResponse.from_task(run) for run in runs]
