"""Members of active GitLab.com projects tagged with the JD's technologies.

Needs GITLAB_TOKEN (read_api): GitLab refuses anonymous user and member lookups.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.scoring_service import infer_level
from app.services.skill_vocabulary import GITHUB_LANGUAGES, as_topic, canonical_list, jd_terms, single_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    by_frequency,
    merge_terms,
    parse_time,
    truncate,
)
from app.services.sources.github import infer_experience


logger = logging.getLogger(__name__)

_API = "https://gitlab.com/api/v4"
_MAX_TOPICS = 2
_PROJECTS_PER_TOPIC = 10
_MEMBERS_PER_PROJECT = 20
_MAX_USERS = 20
_PROJECTS_PER_USER = 3
_MAX_SKILLS = 20
_CONCURRENCY = 8
_DEVELOPER_ACCESS = 30
_ACTIVE_WITHIN = timedelta(days=180)
# GitLab's own bots and project/group access-token users ("project_123_bot_ab12").
_BOT_NAME = re.compile(r"(^|[-_])bot($|[-_])|^(project|group)_\d+_bot", re.IGNORECASE)


class GitLabSourceToolAdapter(SourceToolAdapter):
    def __init__(self, token: Optional[str], transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.GITLAB, transport)
        self._token = token

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        if not self._token:
            logger.warning("GITLAB_TOKEN not configured — skipping GitLab sourcing")
            return []
        terms = [*single_terms(query_terms), *jd_terms(parsed_jd)]
        # Projects are rarely tagged with a bare language, so frameworks and tools come first.
        topics = merge_terms(
            (as_topic(term) for term in terms if term not in GITHUB_LANGUAGES),
            (as_topic(term) for term in terms),
            limit=_MAX_TOPICS,
        )
        if not topics:
            return []

        async with self._client(headers={"PRIVATE-TOKEN": self._token}) as client:
            api = _Api(client)
            active_after = (datetime.now(timezone.utc) - _ACTIVE_WITHIN).isoformat()

            # user id -> (username, the topics and projects they were found through)
            leads: dict[int, tuple[str, list[str], list[str]]] = {}
            for topic in topics:
                try:
                    projects = await api.get("/projects", {
                        "topic": topic, "order_by": "star_count", "sort": "desc", "visibility": "public",
                        "last_activity_after": active_after, "per_page": _PROJECTS_PER_TOPIC, "simple": "true",
                    })
                except Exception as exc:
                    logger.warning("GitLab projects for topic %r failed: %s", topic, exc)
                    continue
                for project in projects:
                    for user_id, username in await _project_people(api, project):
                        lead = leads.setdefault(user_id, (username, [], []))
                        lead[1].append(topic)
                        lead[2].append(project.get("path_with_namespace") or "")
                    if len(leads) >= _MAX_USERS:
                        break

            semaphore = asyncio.Semaphore(_CONCURRENCY)

            async def load(user_id: int) -> tuple[dict, list[list[str]]]:
                async with semaphore:
                    profile = await api.get(f"/users/{user_id}")
                    projects = await api.get(f"/users/{user_id}/projects", {
                        "order_by": "last_activity_at", "per_page": _PROJECTS_PER_USER, "simple": "true",
                    })
                    languages = []
                    for project in projects[:_PROJECTS_PER_USER]:
                        try:
                            languages.append(list(await api.get(f"/projects/{project['id']}/languages")))
                        except Exception:
                            continue
                    return profile, languages

            user_ids = list(leads)[:_MAX_USERS]
            results = await asyncio.gather(*(load(user_id) for user_id in user_ids), return_exceptions=True)

        candidates = []
        for user_id, result in zip(user_ids, results):
            if isinstance(result, BaseException):
                logger.debug("GitLab profile fetch failed for %s: %s", user_id, result)
                continue
            profile, languages = result
            _, found_topics, found_projects = leads[user_id]
            if profile.get("bot") or profile.get("state", "active") != "active":
                continue
            candidates.append(_to_candidate(profile, languages, found_topics, found_projects))
        logger.info("GitLab adapter fetched %d candidates for topics %s", len(candidates), topics)
        return candidates


class _Api:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        response = await self._client.get(f"{_API}{path}", params=params)
        response.raise_for_status()
        return response.json()


async def _project_people(api: _Api, project: dict) -> list[tuple[int, str]]:
    """Developers and above on the project, plus its owner when it lives in a personal namespace."""
    people: list[tuple[int, str]] = []
    try:
        members = await api.get(f"/projects/{project['id']}/members/all", {"per_page": _MEMBERS_PER_PROJECT})
    except Exception as exc:
        logger.debug("GitLab members for %s failed: %s", project.get("id"), exc)
        members = []
    for member in members:
        username = member.get("username") or ""
        if (
            member.get("id")
            and username
            and member.get("state") == "active"
            and int(member.get("access_level") or 0) >= _DEVELOPER_ACCESS
            and not _BOT_NAME.search(username)
        ):
            people.append((member["id"], username))

    namespace = project.get("namespace") or {}
    if namespace.get("kind") == "user" and namespace.get("path") and all(name != namespace["path"] for _, name in people):
        try:
            owners = await api.get("/users", {"username": namespace["path"]})
        except Exception:
            owners = []
        people.extend((owner["id"], owner["username"]) for owner in owners[:1] if owner.get("id"))
    return people


def _to_candidate(profile: dict, languages: list[list[str]], topics: list[str], projects: list[str]) -> RawCandidate:
    username = profile.get("username", "")
    job_title = (profile.get("job_title") or "").strip()
    # A job title ("Senior Backend Engineer") is the best seniority signal any source gives.
    experience = job_title if infer_level(job_title) else infer_experience(
        parse_time(profile.get("created_at")), 0, int(profile.get("followers") or 0), None
    )

    signals = [f"Member of {project}" for project in dict.fromkeys(projects) if project][:2]
    if job_title:
        org = (profile.get("organization") or "").strip()
        signals.insert(0, f"{job_title} at {org}" if org else job_title)
    if profile.get("website_url"):
        signals.append(f"Website: {profile['website_url']}")

    return RawCandidate(
        name=profile.get("name") or username,
        profile_url=profile.get("web_url") or f"https://gitlab.com/{quote(username)}",
        source_username=username,
        source=SourcePlatform.GITLAB,
        skills=by_frequency([canonical_list(topics), *(canonical_list(group) for group in languages)], _MAX_SKILLS),
        # `public_email` is the address the user chose to show on their profile.
        email=profile.get("public_email") or None,
        avatar_url=profile.get("avatar_url") or None,
        bio=truncate(profile.get("bio"), 300),
        location=truncate(profile.get("location"), 100),
        experience=experience,
        signals=signals[:MAX_SIGNALS],
    )
