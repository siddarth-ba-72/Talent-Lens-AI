from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import canonical, canonical_list, jd_terms, single_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    by_frequency,
    compact_number,
    merge_terms,
)


logger = logging.getLogger(__name__)

_REGISTRY = "https://registry.npmjs.org"
_MAX_KEYWORDS = 3
_PACKAGES_PER_KEYWORD = 20
_MIN_MONTHLY_DOWNLOADS = 1_000
_MAX_MAINTAINERS = 20
_MAX_SKILLS = 20
_CONCURRENCY = 5
_BOT_NAME = re.compile(r"(^|[-_.\d])bot$", re.IGNORECASE)


@dataclass(frozen=True)
class _Package:
    name: str
    monthly: int
    repository: Optional[str]
    keyword: str


class NpmSourceToolAdapter(SourceToolAdapter):
    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.NPM, transport)

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        keywords = merge_terms(
            (canonical(term) for term in [*single_terms(query_terms), *jd_terms(parsed_jd)]), limit=_MAX_KEYWORDS
        )
        if not keywords:
            return []

        async with self._client() as client:
            # maintainer -> packages they maintain among the results
            maintained: dict[str, list[_Package]] = {}
            for keyword in keywords:
                try:
                    objects = await _search(client, f"keywords:{keyword}", _PACKAGES_PER_KEYWORD)
                except Exception as exc:
                    logger.warning("npm search for %r failed: %s", keyword, exc)
                    continue
                for item in objects:
                    package = item.get("package") or {}
                    monthly = int((item.get("downloads") or {}).get("monthly") or 0)
                    if monthly < _MIN_MONTHLY_DOWNLOADS:
                        continue
                    repository = (package.get("links") or {}).get("repository")
                    for maintainer in package.get("maintainers") or []:
                        username = maintainer.get("username") or ""
                        if username and not _is_org_or_bot(username, package.get("name") or ""):
                            entry = _Package(package.get("name") or "", monthly, repository, keyword)
                            if entry not in maintained.setdefault(username, []):
                                maintained[username].append(entry)

            ranked = sorted(maintained.items(), key=lambda entry: -sum(package.monthly for package in entry[1]))
            ranked = ranked[:_MAX_MAINTAINERS]

            semaphore = asyncio.Semaphore(_CONCURRENCY)

            async def their_packages(username: str) -> list[dict]:
                async with semaphore:
                    return await _search(client, f"maintainer:{username}", 20)

            portfolios = await asyncio.gather(*(their_packages(username) for username, _ in ranked), return_exceptions=True)

        candidates = []
        for (username, packages), portfolio in zip(ranked, portfolios):
            keyword_lists = [] if isinstance(portfolio, BaseException) else [
                canonical_list((item.get("package") or {}).get("keywords") or []) for item in portfolio
            ]
            candidates.append(_to_candidate(username, packages, keyword_lists))
        logger.info("npm adapter fetched %d candidates for keywords %s", len(candidates), keywords)
        return candidates


async def _search(client: httpx.AsyncClient, text: str, size: int) -> list[dict]:
    response = await client.get(f"{_REGISTRY}/-/v1/search", params={"text": text, "size": size})
    response.raise_for_status()
    return response.json().get("objects", [])


def _is_org_or_bot(username: str, package_name: str) -> bool:
    """Bot accounts, and accounts named after the package's scope (an org's publishing account)."""
    scope = package_name[1:].split("/", 1)[0].lower() if package_name.startswith("@") else ""
    return bool(_BOT_NAME.search(username)) or bool(scope and username.lower().startswith(scope))


def _to_candidate(username: str, packages: list[_Package], keyword_lists: list[list[str]]) -> RawCandidate:
    packages = sorted(packages, key=lambda package: -package.monthly)
    signals = [
        f"Maintains {package.name} ({compact_number(package.monthly)} downloads/month)" for package in packages[:2]
    ]
    repository = next((package.repository for package in packages if package.repository), None)
    if repository:
        signals.append(f"Repo: {repository}")
    found_by = [package.keyword for package in packages]

    return RawCandidate(
        name=username,
        profile_url=f"https://www.npmjs.com/~{username}",
        source_username=username,
        source=SourcePlatform.NPM,
        skills=by_frequency([found_by, *keyword_lists, ["javascript"]], _MAX_SKILLS),
        # Maintainer emails are registry metadata for publishing, not an
        # invitation to be contacted, so they are not stored.
        email=None,
        experience=None,
        signals=signals[:MAX_SIGNALS],
    )
