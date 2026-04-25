from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import Settings
from app.models.candidate_models import (
    RankedCandidateModel,
    ScoreBreakdownModel,
    SourcePlatform,
    SourcingRequestPayloadModel,
    SourcingResultPayloadModel,
    SourcingStatus,
)
from app.providers.base import LlmProvider
from app.services.scoring_service import compute_experience_match, compute_match_score, compute_skill_match


logger = logging.getLogger(__name__)

PLATFORM_PRIORITY: dict[SourcePlatform, int] = {
    SourcePlatform.GITHUB: 0,
    SourcePlatform.STACKOVERFLOW: 1,
    SourcePlatform.LEETCODE: 2,
    SourcePlatform.PEOPLES_DATA: 3,
    SourcePlatform.OTHER: 4,
}

_GITHUB_API = "https://api.github.com"


@dataclass
class RawCandidate:
    name: str
    profile_url: str
    source_username: str
    source: SourcePlatform
    skills: list[str]
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

async def _fetch_github_profile(client: httpx.AsyncClient, login: str) -> dict:
    resp = await client.get(f"{_GITHUB_API}/users/{login}")
    resp.raise_for_status()
    return resp.json()


async def _fetch_github_languages(client: httpx.AsyncClient, login: str) -> list[str]:
    resp = await client.get(
        f"{_GITHUB_API}/users/{login}/repos",
        params={"sort": "stars", "per_page": 10},
    )
    resp.raise_for_status()
    seen: set[str] = set()
    langs: list[str] = []
    for repo in resp.json():
        lang = repo.get("language")
        if lang and lang.lower() not in seen:
            seen.add(lang.lower())
            langs.append(lang)
    return langs


def _infer_experience(followers: int, public_repos: int) -> str:
    if followers >= 500 or public_repos >= 50:
        return "senior"
    if followers >= 100 or public_repos >= 20:
        return "mid"
    return "junior"


def _profile_to_raw(profile: dict, languages: list[str]) -> RawCandidate:
    login = profile.get("login", "")
    return RawCandidate(
        name=profile.get("name") or login,
        profile_url=profile.get("html_url") or f"https://github.com/{login}",
        source_username=login,
        source=SourcePlatform.GITHUB,
        skills=languages,
        email=profile.get("email") or None,
        avatar_url=profile.get("avatar_url") or None,
        bio=profile.get("bio") or None,
        location=profile.get("location") or None,
        experience=_infer_experience(
            profile.get("followers", 0),
            profile.get("public_repos", 0),
        ),
    )


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

class SourceToolAdapter:
    def __init__(self, platform: SourcePlatform):
        self.platform = platform

    async def fetch_candidates(self, query_terms: list[str]) -> list[RawCandidate]:
        _ = query_terms
        return []


class GitHubSourceToolAdapter(SourceToolAdapter):
    _RESULTS_PER_QUERY = 10

    def __init__(self, token: Optional[str]):
        super().__init__(SourcePlatform.GITHUB)
        self._token = token

    async def fetch_candidates(self, query_terms: list[str]) -> list[RawCandidate]:
        if not self._token:
            logger.warning("GITHUB_TOKEN not configured — skipping GitHub sourcing")
            return []

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        seen: set[str] = set()
        logins: list[str] = []

        async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
            # Step 1: collect unique logins from each query
            for query in query_terms[:3]:
                try:
                    resp = await client.get(
                        f"{_GITHUB_API}/search/users",
                        params={"q": query, "per_page": self._RESULTS_PER_QUERY, "sort": "followers"},
                    )
                    resp.raise_for_status()
                    for item in resp.json().get("items", []):
                        login = item.get("login")
                        if login and login not in seen:
                            seen.add(login)
                            logins.append(login)
                except Exception as exc:
                    logger.warning("GitHub search query %r failed: %s", query, exc)

            if not logins:
                return []

            # Step 2: fetch profiles + repo languages in parallel
            profile_results = await asyncio.gather(
                *[_fetch_github_profile(client, login) for login in logins],
                return_exceptions=True,
            )
            lang_results = await asyncio.gather(
                *[_fetch_github_languages(client, login) for login in logins],
                return_exceptions=True,
            )

        candidates: list[RawCandidate] = []
        for login, profile, langs in zip(logins, profile_results, lang_results):
            if isinstance(profile, Exception):
                logger.debug("GitHub profile fetch failed for %s: %s", login, profile)
                continue
            skills = langs if not isinstance(langs, Exception) else []
            candidates.append(_profile_to_raw(profile, skills))

        logger.info("GitHub adapter fetched %d candidates from %d queries", len(candidates), len(query_terms))
        return candidates


class SourcingWorkflowService:
    def __init__(self, provider: LlmProvider, settings: Settings):
        self._provider = provider
        self._adapters: dict[SourcePlatform, SourceToolAdapter] = {
            SourcePlatform.GITHUB: GitHubSourceToolAdapter(settings.github_token),
            SourcePlatform.STACKOVERFLOW: SourceToolAdapter(SourcePlatform.STACKOVERFLOW),
            SourcePlatform.LEETCODE: SourceToolAdapter(SourcePlatform.LEETCODE),
            SourcePlatform.PEOPLES_DATA: SourceToolAdapter(SourcePlatform.PEOPLES_DATA),
        }

    async def run(self, payload: SourcingRequestPayloadModel) -> SourcingResultPayloadModel:
        completed_at = datetime.now(timezone.utc)

        # Use the LLM to generate platform-specific search queries
        platforms_str = [p.value for p in payload.platforms]
        queries_by_platform = self._provider.generate_queries(payload.parsedJd, platforms_str)

        raw_candidates, errors = await self._source_candidates(queries_by_platform, payload.platforms)
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
            completedAt=completed_at,
        )

    async def _source_candidates(
        self,
        queries_by_platform: dict[str, list[str]],
        platforms: list[SourcePlatform],
    ) -> tuple[list[RawCandidate], list[str]]:
        tasks: list[asyncio.Task[list[RawCandidate]]] = []
        active_platforms: list[SourcePlatform] = []
        for platform in platforms:
            adapter = self._adapters.get(platform)
            if adapter is None:
                continue
            query_terms = queries_by_platform.get(platform.value, [])
            active_platforms.append(platform)
            tasks.append(asyncio.create_task(adapter.fetch_candidates(query_terms)))

        if not tasks:
            return [], []

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        raw: list[RawCandidate] = []
        errors: list[str] = []

        for idx, item in enumerate(gathered):
            platform = active_platforms[idx].value
            if isinstance(item, Exception):
                errors.append(f"{platform}: {item}")
                continue
            raw.extend(item)

        return raw, errors

    def _score_and_rank(
        self,
        raw_candidates: list[RawCandidate],
        payload: SourcingRequestPayloadModel,
    ) -> list[RankedCandidateModel]:
        jd_skills = payload.parsedJd.skills + payload.parsedJd.technologies

        ranked: list[RankedCandidateModel] = []
        for raw in raw_candidates:
            skill_match = compute_skill_match(jd_skills, raw.skills)
            experience_match = compute_experience_match(payload.parsedJd.experienceLevel, raw.experience)
            match_score = compute_match_score(skill_match, experience_match)

            breakdown = ScoreBreakdownModel(
                skillMatch=skill_match,
                experienceMatch=experience_match,
                overallFit=match_score,
            )

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
                    matchScore=match_score,
                    scoreBreakdown=breakdown,
                )
            )

        ranked.sort(key=self._sort_key)
        return ranked[:20]

    def _sort_key(self, candidate: RankedCandidateModel) -> tuple[int, int, int, str]:
        return (
            -candidate.matchScore,
            -candidate.scoreBreakdown.skillMatch,
            PLATFORM_PRIORITY.get(candidate.source, 99),
            candidate.sourceUsername.lower(),
        )
