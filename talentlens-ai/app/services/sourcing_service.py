from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo.errors import DuplicateKeyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.documents import CandidateDocument
from app.db.models import Search, SourcingStatus, SourcingTask, TaskStatus, User, utcnow
from app.db.postgres import session_factory
from app.dependencies import get_sourcing_workflow_service
from app.errors import InvalidFileError, ResourceNotFoundError
from app.models.candidate_models import (
    RankedCandidateModel,
    SourcePlatform,
    SourcingRequestPayloadModel,
    SourcingResultPayloadModel,
)
from app.models.candidate_models import SourcingStatus as ResultStatus
from app.models.jd_models import ParsedJdModel
from app.services.search_service import assert_ownership, get_search_or_404, get_viewable_search


logger = logging.getLogger(__name__)

ALLOWED_PLATFORMS = ("GITHUB", "STACKOVERFLOW", "LEETCODE", "PEOPLES_DATA")
MAX_CANDIDATES_PER_RUN = 20
# How long past the sourcing timeout a task may sit unfinished before it is
# considered orphaned (its worker process died).
_ORPHAN_GRACE_SECONDS = 60

# Strong references: the event loop only keeps weak ones to running tasks.
_running: set[asyncio.Task[None]] = set()


async def trigger_sourcing(session: AsyncSession, user: User, search_id: str, platforms: list[str]) -> SourcingTask:
    # Row lock so two concurrent triggers cannot both start a run.
    search = await get_search_or_404(session, search_id, for_update=True)
    assert_ownership(search, user)

    if search.sourcing_status == SourcingStatus.IN_PROGRESS:
        raise InvalidFileError("Sourcing is already in progress for this search")
    platforms = _validate_platforms(platforms)

    now = utcnow()
    run_id = f"run_{now:%Y%m%d_%H%M%S}_{now.microsecond // 1000:03d}"
    task = SourcingTask(
        search_id=search.id,
        run_id=run_id,
        platforms=platforms,
        status=TaskStatus.PENDING,
        candidates_found=0,
        started_at=now,
    )
    session.add(task)
    search.sourcing_status = SourcingStatus.IN_PROGRESS
    search.sourcing_platforms = platforms
    await session.commit()

    payload = SourcingRequestPayloadModel(
        taskId=task.id,
        searchId=search.id,
        runId=run_id,
        parsedJd=ParsedJdModel.model_validate(search.parsed_jd),
        platforms=[SourcePlatform(platform) for platform in platforms],
        timestamp=now,
    )
    background = asyncio.create_task(execute_sourcing(payload))
    _running.add(background)
    background.add_done_callback(_running.discard)
    return task


async def get_status(session: AsyncSession, user: User, search_id: str) -> SourcingTask:
    search = await get_viewable_search(session, user, search_id)
    task = await session.scalar(
        select(SourcingTask)
        .where(SourcingTask.search_id == search.id)
        .order_by(SourcingTask.started_at.desc())
        .limit(1)
    )
    if task is None:
        raise ResourceNotFoundError(f"No sourcing task found for search: {search_id}")
    return task


async def list_runs(session: AsyncSession, user: User, search_id: str) -> list[SourcingTask]:
    """Every sourcing run of a search, newest first. Each run keeps its own candidates."""
    search = await get_viewable_search(session, user, search_id)
    rows = await session.scalars(
        select(SourcingTask)
        .where(SourcingTask.search_id == search.id)
        .order_by(SourcingTask.started_at.desc(), SourcingTask.id)
    )
    return list(rows)


async def execute_sourcing(payload: SourcingRequestPayloadModel) -> None:
    settings = get_settings()
    logger.info(
        "Async sourcing started: searchId=%s, taskId=%s, platforms=%s",
        payload.searchId, payload.taskId, [platform.value for platform in payload.platforms],
    )
    try:
        workflow = get_sourcing_workflow_service()
        result = await asyncio.wait_for(workflow.run(payload), timeout=settings.sourcing_timeout_seconds)
        await _process_result(result)
    except Exception as exc:
        if isinstance(exc, asyncio.TimeoutError):
            reason = f"Sourcing timed out after {settings.sourcing_timeout_seconds} seconds"
        else:
            reason = str(exc) or type(exc).__name__
        logger.error(
            "Sourcing failed for searchId=%s, taskId=%s: %s", payload.searchId, payload.taskId, reason, exc_info=exc
        )
        try:
            await _mark_failed(payload.taskId, payload.searchId, reason)
        except Exception:
            logger.exception("Could not record sourcing failure for taskId=%s", payload.taskId)


async def fail_orphaned_tasks() -> int:
    """Fail runs that were still open when their worker process went away."""
    settings = get_settings()
    cutoff = utcnow() - timedelta(seconds=settings.sourcing_timeout_seconds + _ORPHAN_GRACE_SECONDS)
    async with session_factory()() as session:
        orphans = list(
            await session.scalars(
                select(SourcingTask).where(
                    SourcingTask.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                    SourcingTask.started_at < cutoff,
                )
            )
        )
        for task in orphans:
            task.status = TaskStatus.FAILED
            task.error = "Sourcing was interrupted before it finished"
            task.completed_at = utcnow()
            search = await session.get(Search, task.search_id)
            if search is not None and search.sourcing_status == SourcingStatus.IN_PROGRESS:
                search.sourcing_status = SourcingStatus.FAILED
        await session.commit()
    return len(orphans)


def _validate_platforms(platforms: list[str]) -> list[str]:
    for platform in platforms:
        if platform not in ALLOWED_PLATFORMS:
            raise InvalidFileError(f"Invalid platform: {platform}. Allowed: {', '.join(ALLOWED_PLATFORMS)}")
    return list(dict.fromkeys(platforms))


async def _process_result(result: SourcingResultPayloadModel) -> None:
    async with session_factory()() as session:
        task = await session.get(SourcingTask, result.taskId)
        if task is None:
            logger.warning("SourcingTask not found for taskId=%s, skipping result processing", result.taskId)
            return

        completed = result.status == ResultStatus.COMPLETED
        candidates = result.candidates[:MAX_CANDIDATES_PER_RUN] if completed else []
        if completed:
            await _persist_candidates(result.searchId, result.runId, candidates)

        task.status = TaskStatus.COMPLETED if completed else TaskStatus.FAILED
        task.candidates_found = len(candidates)
        task.error = result.error
        task.completed_at = result.completedAt

        search = await session.get(Search, result.searchId)
        if search is not None:
            search.sourcing_status = SourcingStatus.COMPLETED if completed else SourcingStatus.FAILED
            if completed:
                # A search shows its latest completed run by default, so its count is that run's.
                search.candidate_count = await CandidateDocument.find(
                    {"searchId": search.id, "runId": task.run_id, "isActive": True}
                ).count()
        await session.commit()

    logger.info(
        "Sourcing result processed: searchId=%s, status=%s, candidatesFound=%d",
        result.searchId, result.status.value, len(candidates),
    )


async def _mark_failed(task_id: str, search_id: str, error: str) -> None:
    async with session_factory()() as session:
        task = await session.get(SourcingTask, task_id)
        if task is not None:
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = utcnow()
        search = await session.get(Search, search_id)
        if search is not None:
            search.sourcing_status = SourcingStatus.FAILED
        await session.commit()


async def _persist_candidates(search_id: str, raw_run_id: Optional[str], candidates: list[RankedCandidateModel]) -> None:
    run_id = raw_run_id if raw_run_id and raw_run_id.strip() else "run_unknown"
    for candidate in candidates:
        if not candidate.profileUrl.strip() or not candidate.sourceUsername.strip():
            logger.warning("Skipping invalid candidate for searchId=%s, runId=%s", search_id, run_id)
            continue

        document = CandidateDocument(
            searchId=search_id,
            runId=run_id,
            name=candidate.name if candidate.name.strip() else candidate.sourceUsername,
            email=candidate.email,
            avatarUrl=candidate.avatarUrl,
            profileUrl=candidate.profileUrl,
            source=candidate.source,
            sourceUsername=candidate.sourceUsername,
            skills=candidate.skills,
            bio=candidate.bio,
            location=candidate.location,
            experience=candidate.experience,
            matchScore=candidate.matchScore,
            scoreBreakdown=candidate.scoreBreakdown,
            isActive=True,
            sourcedAt=candidate.sourcedAt,
            createdAt=datetime.now(timezone.utc),
        )
        try:
            await document.insert()
        except DuplicateKeyError:
            logger.debug(
                "Duplicate candidate skipped: searchId=%s, runId=%s, sourceUsername=%s",
                search_id, run_id, candidate.sourceUsername,
            )
