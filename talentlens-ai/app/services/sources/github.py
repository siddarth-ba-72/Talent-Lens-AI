from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import GITHUB_LANGUAGES, as_topic, canonical_list, jd_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    by_frequency,
    compact_number,
    parse_time,
    years_since,
)


logger = logging.getLogger(__name__)

_API = "https://api.github.com"
_USER_QUERIES = 3
_USERS_PER_QUERY = 10
_REPO_QUERIES = 2
_REPOS_PER_QUERY = 5
_CONTRIBUTORS_PER_REPO = 15
_MIN_CONTRIBUTIONS = 5
_MAX_LOGINS = 30
_MAX_SKILLS = 20
_CONCURRENCY = 10
# Repos larger than this are mostly maintained by people least likely to move.
_REPO_STARS = "50..5000"
_REPO_PUSHED_WITHIN = timedelta(days=180)
_INACTIVE_AFTER = timedelta(days=365)


class _RateLimited(Exception):
    pass


@dataclass
class _Lead:
    """Why a login was picked, before its profile is fetched."""

    skills: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    contributor: bool = False


class _Api:
    """One run's GitHub calls; stops calling once the rate limit is used up."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        self.exhausted = False

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        if self.exhausted:
            raise _RateLimited()
        response = await self._client.get(f"{_API}{path}", params=params)
        if response.status_code in (403, 429) and response.headers.get("X-RateLimit-Remaining") == "0":
            if not self.exhausted:
                logger.warning("GitHub rate limit reached; returning the candidates found so far")
            self.exhausted = True
            raise _RateLimited()
        response.raise_for_status()
        return response.json()


class GitHubSourceToolAdapter(SourceToolAdapter):
    def __init__(self, token: Optional[str], transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.GITHUB, transport)
        self._token = token

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        if not self._token:
            logger.warning("GITHUB_TOKEN not configured — skipping GitHub sourcing")
            return []

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with self._client(headers=headers) as client:
            api = _Api(client)
            # Contributors first: committing to a project in the JD's stack is
            # stronger evidence than a profile that matches a keyword search.
            leads = await _contributor_leads(api, parsed_jd)
            for login in await _searched_logins(api, query_terms, parsed_jd):
                leads.setdefault(login, _Lead())
            logins = list(leads)[:_MAX_LOGINS]

            semaphore = asyncio.Semaphore(_CONCURRENCY)

            async def load(login: str) -> tuple[dict, list[dict]]:
                async with semaphore:
                    profile = await api.get(f"/users/{login}")
                    repos = await api.get(f"/users/{login}/repos", {"sort": "pushed", "per_page": 30})
                    return profile, repos

            results = await asyncio.gather(*(load(login) for login in logins), return_exceptions=True)

        now = datetime.now(timezone.utc)
        candidates: list[RawCandidate] = []
        for login, result in zip(logins, results):
            if isinstance(result, BaseException):
                logger.debug("GitHub profile fetch failed for %s: %s", login, result)
                continue
            candidate = _to_candidate(*result, leads[login], now)
            if candidate is not None:
                candidates.append(candidate)

        logger.info("GitHub adapter fetched %d candidates from %d logins", len(candidates), len(logins))
        return candidates


async def _searched_logins(api: _Api, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[str]:
    queries = [query for query in query_terms if query.strip()][:_USER_QUERIES]
    language = _jd_language(parsed_jd)
    if language and len(queries) < _USER_QUERIES:
        # Works even when the LLM fell back to a plain keyword phrase.
        queries.append(f"language:{language} repos:>5 followers:>10")

    logins: list[str] = []
    for query in queries:
        try:
            # No `sort`: best match. Sorting by followers surfaces famous
            # developers, the people least likely to be looking.
            body = await api.get("/search/users", {"q": query, "per_page": _USERS_PER_QUERY})
        except _RateLimited:
            break
        except Exception as exc:
            logger.warning("GitHub user search %r failed: %s", query, exc)
            continue
        for item in body.get("items", []):
            login = item.get("login")
            if login and item.get("type", "User") == "User" and login not in logins:
                logins.append(login)
    return logins


async def _contributor_leads(api: _Api, parsed_jd: ParsedJdModel) -> dict[str, _Lead]:
    leads: dict[str, _Lead] = {}
    pushed_after = (datetime.now(timezone.utc) - _REPO_PUSHED_WITHIN).date().isoformat()
    language = _jd_language(parsed_jd)

    repos: list[dict] = []
    for query in _repo_queries(parsed_jd, language, pushed_after):
        try:
            body = await api.get("/search/repositories", {"q": query, "sort": "stars", "per_page": _REPOS_PER_QUERY})
        except _RateLimited:
            return leads
        except Exception as exc:
            logger.warning("GitHub repo search %r failed: %s", query, exc)
            continue
        for repo in body.get("items", []):
            if repo.get("full_name") and all(repo["full_name"] != seen["full_name"] for seen in repos):
                repos.append(repo)

    for repo in repos:
        try:
            contributors = await api.get(
                f"/repos/{repo['full_name']}/contributors", {"per_page": _CONTRIBUTORS_PER_REPO}
            )
        except _RateLimited:
            break
        except Exception as exc:
            logger.debug("GitHub contributors fetch failed for %s: %s", repo["full_name"], exc)
            continue
        repo_skills = canonical_list([repo.get("language") or "", *(repo.get("topics") or [])])
        for contributor in contributors if isinstance(contributors, list) else []:
            login = contributor.get("login") or ""
            commits = contributor.get("contributions") or 0
            if (
                not login
                or contributor.get("type") != "User"
                or login.lower().endswith("[bot]")
                or commits < _MIN_CONTRIBUTIONS
            ):
                continue
            lead = leads.setdefault(login, _Lead(contributor=True))
            lead.skills.extend(repo_skills)
            lead.signals.append(f"Contributor to {repo['full_name']} ({commits} commits)")
    return leads


def _repo_queries(parsed_jd: ParsedJdModel, language: Optional[str], pushed_after: str) -> list[str]:
    topics = [as_topic(term) for term in jd_terms(parsed_jd) if term not in GITHUB_LANGUAGES]
    language_filter = f" language:{language}" if language else ""
    suffix = f"{language_filter} stars:{_REPO_STARS} pushed:>{pushed_after}"
    queries = [f"topic:{topic}{suffix}" for topic in dict.fromkeys(topics) if topic][:_REPO_QUERIES]
    if not queries and language:
        queries.append(suffix.strip())
    return queries


def _jd_language(parsed_jd: ParsedJdModel) -> Optional[str]:
    for term in jd_terms(parsed_jd):
        if term in GITHUB_LANGUAGES:
            return GITHUB_LANGUAGES[term]
    return None


def _to_candidate(profile: dict, repos: list[dict], lead: _Lead, now: datetime) -> Optional[RawCandidate]:
    login = profile.get("login", "")
    if profile.get("type", "User") != "User":
        return None

    own_repos = [repo for repo in repos if isinstance(repo, dict) and not repo.get("fork")]
    pushes = [parse_time(repo.get("pushed_at")) for repo in own_repos]
    last_push = max((push for push in pushes if push), default=None)
    # A contributor's work may all live in other people's repos; anyone else
    # needs recent activity of their own.
    if not lead.contributor and (last_push is None or now - last_push > _INACTIVE_AFTER):
        return None

    skills = by_frequency(
        [canonical_list([repo.get("language") or "", *(repo.get("topics") or [])]) for repo in own_repos]
        + [lead.skills],
        _MAX_SKILLS,
    )
    owned_stars = sum(int(repo.get("stargazers_count") or 0) for repo in own_repos)
    followers = int(profile.get("followers") or 0)

    signals = list(dict.fromkeys(lead.signals))[:2]
    hireable = profile.get("hireable") is True
    if hireable:
        signals.insert(0, "Marked hireable on GitHub")
    if owned_stars >= 50:
        signals.append(f"{compact_number(owned_stars)} stars on own repos")
    if profile.get("blog"):
        signals.append(f"Website: {profile['blog']}")

    return RawCandidate(
        name=profile.get("name") or login,
        profile_url=profile.get("html_url") or f"https://github.com/{login}",
        source_username=login,
        source=SourcePlatform.GITHUB,
        skills=skills,
        email=profile.get("email") or None,
        avatar_url=profile.get("avatar_url") or None,
        bio=profile.get("bio") or None,
        location=profile.get("location") or None,
        experience=infer_experience(parse_time(profile.get("created_at")), owned_stars, followers, last_push, now),
        signals=signals[:MAX_SIGNALS],
        open_to_work=hireable,
    )


def infer_experience(
    created_at: Optional[datetime],
    owned_stars: int,
    followers: int,
    last_push: Optional[datetime],
    now: Optional[datetime] = None,
) -> Optional[str]:
    """A rough seniority from account age and reach. None (scored as neutral) when unclear."""
    now = now or datetime.now(timezone.utc)
    account_years = years_since(created_at, now)
    if account_years is None:
        return None
    if account_years >= 8 and (owned_stars >= 200 or followers >= 100):
        return "senior"
    if account_years >= 4 and last_push is not None and now - last_push <= _INACTIVE_AFTER:
        return "mid"
    if account_years < 2:
        return "junior"
    return None

