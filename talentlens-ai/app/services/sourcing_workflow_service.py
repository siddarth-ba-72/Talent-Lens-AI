from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import Settings
from app.models.candidate_models import (
    RankedCandidateModel,
    ScoreBreakdownModel,
    SourcePlatform,
    SourcingRequestPayloadModel,
    SourcingResultPayloadModel,
    SourcingStatus,
)
from app.models.jd_models import ParsedJdModel
from app.providers.base import LlmProvider
from app.services.scoring_service import compute_experience_match, compute_match_score, compute_skill_match
from app.services.skill_vocabulary import jd_terms
from app.services.sources.base import RawCandidate, SourceToolAdapter
from app.services.sources.registry import PLATFORMS, build_adapters


logger = logging.getLogger(__name__)

MAX_RANKED = 20
# Each platform that found anyone keeps this many of the top places, so sources
# whose profiles rarely list JD terms verbatim (papers, packages) still show up.
RESERVED_PER_PLATFORM = 3

# Tie-break order between platforms (registry order: general sources first).
PLATFORM_PRIORITY: dict[SourcePlatform, int] = {platform: index for index, platform in enumerate(PLATFORMS)}


class SourcingWorkflowService:
    def __init__(
        self,
        provider: LlmProvider,
        settings: Settings,
        adapters: Optional[dict[SourcePlatform, SourceToolAdapter]] = None,
    ):
        self._provider = provider
        self._adapters = adapters if adapters is not None else build_adapters(settings)

    async def run(self, payload: SourcingRequestPayloadModel) -> SourcingResultPayloadModel:
        platforms = [platform for platform in payload.platforms if platform in self._adapters]
        # The provider call blocks; keep it off the event loop.
        queries_by_platform = await asyncio.to_thread(
            self._provider.generate_queries, payload.parsedJd, [platform.value for platform in platforms]
        )

        raw_candidates, errors = await self._source_candidates(queries_by_platform, platforms, payload.parsedJd)
        ranked = self._score_and_rank(raw_candidates, payload)

        status = SourcingStatus.COMPLETED
        error_message = "; ".join(errors) if errors else None
        if errors and not ranked:
            status = SourcingStatus.FAILED

        return SourcingResultPayloadModel(
            taskId=payload.taskId,
            searchId=payload.searchId,
            runId=payload.runId,
            status=status,
            candidates=ranked,
            error=error_message,
            completedAt=datetime.now(timezone.utc),
        )

    async def _source_candidates(
        self,
        queries_by_platform: dict[str, list[str]],
        platforms: list[SourcePlatform],
        parsed_jd: ParsedJdModel,
    ) -> tuple[list[RawCandidate], list[str]]:
        if not platforms:
            return [], []

        gathered = await asyncio.gather(
            *(
                self._adapters[platform].fetch_candidates(queries_by_platform.get(platform.value, []), parsed_jd)
                for platform in platforms
            ),
            return_exceptions=True,
        )
        raw: list[RawCandidate] = []
        errors: list[str] = []
        for platform, item in zip(platforms, gathered):
            if isinstance(item, BaseException):
                logger.warning("Sourcing from %s failed: %s", platform.value, item, exc_info=item)
                errors.append(f"{platform.value}: {item}")
                continue
            raw.extend(item)
        return raw, errors

    def _score_and_rank(
        self,
        raw_candidates: list[RawCandidate],
        payload: SourcingRequestPayloadModel,
    ) -> list[RankedCandidateModel]:
        jd_skills = jd_terms(payload.parsedJd)

        ranked: list[RankedCandidateModel] = []
        for raw in raw_candidates:
            skill_match = compute_skill_match(jd_skills, raw.skills)
            experience_match = compute_experience_match(payload.parsedJd.experienceLevel, raw.experience)
            match_score = compute_match_score(skill_match, experience_match)

            ranked.append(
                RankedCandidateModel(
                    name=raw.name,
                    email=raw.email,
                    avatarUrl=raw.avatar_url,
                    profileUrl=raw.profile_url,
                    source=raw.source,
                    sourceUsername=raw.source_username,
                    skills=raw.skills,
                    bio=raw.bio,
                    location=raw.location,
                    experience=raw.experience,
                    signals=raw.signals,
                    openToWork=raw.open_to_work,
                    matchScore=match_score,
                    scoreBreakdown=ScoreBreakdownModel(
                        skillMatch=skill_match,
                        experienceMatch=experience_match,
                        overallFit=match_score,
                    ),
                )
            )

        ranked.sort(key=self._sort_key)
        return select_top(ranked, MAX_RANKED, RESERVED_PER_PLATFORM, self._sort_key)

    @staticmethod
    def _sort_key(candidate: RankedCandidateModel) -> tuple[int, int, int, int, str]:
        return (
            -candidate.matchScore,
            # Among equal scores, people who say they are looking come first.
            -int(candidate.openToWork),
            -candidate.scoreBreakdown.skillMatch,
            PLATFORM_PRIORITY.get(candidate.source, 99),
            candidate.sourceUsername.lower(),
        )


def select_top(ranked: list[RankedCandidateModel], limit: int, per_platform: int, sort_key) -> list[RankedCandidateModel]:
    """The best `limit` candidates, keeping each platform's best `per_platform` among them.

    `ranked` must already be sorted best first.
    """
    # The same profile can be found twice on one platform (e.g. by two queries).
    unique: dict[tuple[SourcePlatform, str], RankedCandidateModel] = {}
    for candidate in ranked:
        unique.setdefault((candidate.source, candidate.sourceUsername.lower()), candidate)
    ranked = list(unique.values())

    taken: list[int] = []
    per_source: dict[SourcePlatform, int] = {}
    for index, candidate in enumerate(ranked):
        if per_source.get(candidate.source, 0) < per_platform:
            per_source[candidate.source] = per_source.get(candidate.source, 0) + 1
            taken.append(index)
    # With more platforms than limit / per_platform, the reserved places themselves go by rank.
    chosen = set(taken[:limit])
    for index in range(len(ranked)):
        if len(chosen) >= limit:
            break
        chosen.add(index)
    return sorted((ranked[index] for index in chosen), key=sort_key)
