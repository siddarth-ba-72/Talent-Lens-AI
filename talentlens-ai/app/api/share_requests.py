from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.postgres import get_session
from app.models.common_models import PageResponse
from app.models.search_models import SearchSummaryResponse
from app.models.share_models import CreateShareRequestRequest, RecruiterResponse, ShareRequestResponse
from app.security.auth import require_hiring_manager, require_recruiter
from app.services import share_request_service


router = APIRouter(prefix="/api/share-requests", tags=["share-requests"])


@router.get("/recruiters", response_model=PageResponse[RecruiterResponse])
async def list_recruiters(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_hiring_manager),
    session: AsyncSession = Depends(get_session),
) -> PageResponse[RecruiterResponse]:
    recruiters, total = await share_request_service.list_recruiters(session, page=page, size=size)
    return PageResponse.of([RecruiterResponse.from_user(r) for r in recruiters], total, page, size)


@router.get("/recruiters/{recruiter_id}/searches", response_model=PageResponse[SearchSummaryResponse])
async def list_recruiter_searches(
    recruiter_id: str,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=50, ge=1, le=100),
    user: User = Depends(require_hiring_manager),
    session: AsyncSession = Depends(get_session),
) -> PageResponse[SearchSummaryResponse]:
    searches, total = await share_request_service.list_recruiter_searches(
        session, recruiter_id, page=page, size=size
    )
    return PageResponse.of([SearchSummaryResponse.from_search(s) for s in searches], total, page, size)


@router.post("", response_model=ShareRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    request: CreateShareRequestRequest,
    user: User = Depends(require_hiring_manager),
    session: AsyncSession = Depends(get_session),
) -> ShareRequestResponse:
    return await share_request_service.create_request(session, user, request)


@router.get("/incoming", response_model=PageResponse[ShareRequestResponse])
async def list_incoming(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
) -> PageResponse[ShareRequestResponse]:
    requests, total = await share_request_service.list_incoming(session, user, page=page, size=size)
    return PageResponse.of(requests, total, page, size)


@router.get("/outgoing", response_model=PageResponse[ShareRequestResponse])
async def list_outgoing(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_hiring_manager),
    session: AsyncSession = Depends(get_session),
) -> PageResponse[ShareRequestResponse]:
    requests, total = await share_request_service.list_outgoing(session, user, page=page, size=size)
    return PageResponse.of(requests, total, page, size)


@router.post("/{request_id}/approve", response_model=ShareRequestResponse)
async def approve(
    request_id: str,
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
) -> ShareRequestResponse:
    return await share_request_service.approve(session, user, request_id)


@router.post("/{request_id}/reject", response_model=ShareRequestResponse)
async def reject(
    request_id: str,
    user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_session),
) -> ShareRequestResponse:
    return await share_request_service.reject(session, user, request_id)
