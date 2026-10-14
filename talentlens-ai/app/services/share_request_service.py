from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, Search, SearchShare, ShareRequest, ShareRequestStatus, User, utcnow
from app.errors import DuplicateResourceError, ForbiddenError, ResourceNotFoundError
from app.models.share_models import CreateShareRequestRequest, ShareRequestResponse
from app.services.search_service import get_search_or_404, normalize_id


async def list_recruiters(session: AsyncSession, *, page: int, size: int) -> tuple[list[User], int]:
    condition = User.role == Role.RECRUITER
    total = await session.scalar(select(func.count()).select_from(User).where(condition)) or 0
    rows = await session.scalars(
        select(User).where(condition).order_by(User.name, User.id).offset(page * size).limit(size)
    )
    return list(rows), total


async def list_recruiter_searches(
    session: AsyncSession, recruiter_id: str, *, page: int, size: int
) -> tuple[list[Search], int]:
    owner_id = normalize_id(recruiter_id)
    if owner_id is None:
        return [], 0
    condition = Search.user_id == owner_id
    total = await session.scalar(select(func.count()).select_from(Search).where(condition)) or 0
    rows = await session.scalars(
        select(Search).where(condition).order_by(Search.created_at.desc(), Search.id).offset(page * size).limit(size)
    )
    return list(rows), total


async def create_request(
    session: AsyncSession, requester: User, request: CreateShareRequestRequest
) -> ShareRequestResponse:
    if requester.role != Role.HIRING_MANAGER:
        raise ForbiddenError("Only hiring managers can request search access")

    recruiter = await session.get(User, normalize_id(request.recruiterUserId))
    if recruiter is None:
        raise ResourceNotFoundError(f"Recruiter not found: {request.recruiterUserId}")
    if recruiter.role != Role.RECRUITER:
        raise ForbiddenError("Target user is not a recruiter")

    search = await get_search_or_404(session, request.searchId)
    if search.user_id != recruiter.id:
        raise ResourceNotFoundError("Invalid search and recruiter combination")
    if requester.id in search.shared_with:
        raise DuplicateResourceError("Search is already shared with this user")

    has_pending = await session.scalar(
        select(ShareRequest.id)
        .where(
            ShareRequest.search_id == search.id,
            ShareRequest.requester_user_id == requester.id,
            ShareRequest.status == ShareRequestStatus.PENDING,
        )
        .limit(1)
    )
    if has_pending is not None:
        raise DuplicateResourceError("A pending share request already exists for this search")

    entity = ShareRequest(
        search_id=search.id,
        requester_user_id=requester.id,
        owner_user_id=recruiter.id,
        status=ShareRequestStatus.PENDING,
        note=request.note,
    )
    session.add(entity)
    await session.commit()
    return (await _to_responses(session, [entity]))[0]


async def list_incoming(
    session: AsyncSession, recruiter: User, *, page: int, size: int
) -> tuple[list[ShareRequestResponse], int]:
    conditions = (ShareRequest.owner_user_id == recruiter.id, ShareRequest.status == ShareRequestStatus.PENDING)
    return await _page(session, conditions, page=page, size=size)


async def list_outgoing(
    session: AsyncSession, requester: User, *, page: int, size: int
) -> tuple[list[ShareRequestResponse], int]:
    return await _page(session, (ShareRequest.requester_user_id == requester.id,), page=page, size=size)


async def approve(session: AsyncSession, recruiter: User, request_id: str) -> ShareRequestResponse:
    request = await _load_pending_for_owner(session, request_id, recruiter)
    search = await get_search_or_404(session, request.search_id)

    # Idempotent grant: a second approval for the same pair is a no-op.
    await session.execute(
        pg_insert(SearchShare)
        .values(search_id=search.id, user_id=request.requester_user_id)
        .on_conflict_do_nothing()
    )
    search.updated_at = utcnow()
    return await _resolve(session, request, recruiter, ShareRequestStatus.APPROVED)


async def reject(session: AsyncSession, recruiter: User, request_id: str) -> ShareRequestResponse:
    request = await _load_pending_for_owner(session, request_id, recruiter)
    return await _resolve(session, request, recruiter, ShareRequestStatus.REJECTED)


async def _resolve(
    session: AsyncSession, request: ShareRequest, recruiter: User, status: ShareRequestStatus
) -> ShareRequestResponse:
    request.status = status
    request.resolved_at = utcnow()
    request.resolved_by = recruiter.id
    await session.commit()
    return (await _to_responses(session, [request]))[0]


async def _load_pending_for_owner(session: AsyncSession, request_id: str, recruiter: User) -> ShareRequest:
    normalized = normalize_id(request_id)
    request = None
    if normalized is not None:
        request = await session.scalar(
            select(ShareRequest)
            .where(ShareRequest.id == normalized, ShareRequest.owner_user_id == recruiter.id)
            .with_for_update()
        )
    if request is None:
        raise ResourceNotFoundError(f"Share request not found: {request_id}")
    if request.status != ShareRequestStatus.PENDING:
        raise DuplicateResourceError("Share request is already resolved")
    return request


async def _page(
    session: AsyncSession, conditions: tuple, *, page: int, size: int
) -> tuple[list[ShareRequestResponse], int]:
    total = await session.scalar(select(func.count()).select_from(ShareRequest).where(*conditions)) or 0
    rows = await session.scalars(
        select(ShareRequest)
        .where(*conditions)
        .order_by(ShareRequest.requested_at.desc(), ShareRequest.id)
        .offset(page * size)
        .limit(size)
    )
    return await _to_responses(session, list(rows)), total


async def _to_responses(session: AsyncSession, requests: list[ShareRequest]) -> list[ShareRequestResponse]:
    if not requests:
        return []

    search_ids = {request.search_id for request in requests}
    user_ids = {request.requester_user_id for request in requests} | {request.owner_user_id for request in requests}
    titles = dict((await session.execute(select(Search.id, Search.title).where(Search.id.in_(search_ids)))).all())
    names = dict((await session.execute(select(User.id, User.name).where(User.id.in_(user_ids)))).all())

    return [
        ShareRequestResponse.from_request(
            request,
            search_title=titles.get(request.search_id),
            requester_name=names.get(request.requester_user_id),
            owner_name=names.get(request.owner_user_id),
        )
        for request in requests
    ]
