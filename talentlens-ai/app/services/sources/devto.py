from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import as_devto_tag, canonical_list, jd_terms, single_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    by_frequency,
    merge_terms,
    truncate,
)


logger = logging.getLogger(__name__)

_API = "https://dev.to/api"
_MAX_TAGS = 3
_ARTICLES_PER_TAG = 30
_MAX_AUTHORS = 20
_MIN_REACTIONS = 5
_MAX_SKILLS = 20
_CONCURRENCY = 5
# Articles whose author discloses at most some AI help. Anything beyond that
# says little about the author's own expertise.
_HUMAN_WRITTEN = {None, "", "no_ai", "not_disclosed", "some_ai"}


class DevToSourceToolAdapter(SourceToolAdapter):
    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.DEVTO, transport)

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        tags = merge_terms(
            (as_devto_tag(term) for term in [*single_terms(query_terms), *jd_terms(parsed_jd)]), limit=_MAX_TAGS
        )
        if not tags:
            return []

        async with self._client() as client:
            # username -> articles found for the JD's tags
            authors: dict[str, list[dict]] = {}
            for tag in tags:
                try:
                    response = await client.get(
                        f"{_API}/articles", params={"tag": tag, "top": 365, "per_page": _ARTICLES_PER_TAG}
                    )
                    response.raise_for_status()
                except Exception as exc:
                    logger.warning("dev.to articles for #%s failed: %s", tag, exc)
                    continue
                for article in response.json():
                    username = (article.get("user") or {}).get("username")
                    if username and article.get("ai_disclosure_level") in _HUMAN_WRITTEN:
                        authors.setdefault(username, []).append(article)

            ranked = sorted(
                (
                    (username, articles) for username, articles in authors.items()
                    if max(_reactions(article) for article in articles) >= _MIN_REACTIONS
                ),
                key=lambda entry: (-len(entry[1]), -sum(_reactions(article) for article in entry[1])),
            )[:_MAX_AUTHORS]

            semaphore = asyncio.Semaphore(_CONCURRENCY)

            async def load(username: str) -> tuple[dict, list[dict]]:
                async with semaphore:
                    profile = await client.get(f"{_API}/users/by_username", params={"url": username})
                    profile.raise_for_status()
                    articles = await client.get(f"{_API}/articles", params={"username": username, "per_page": 30})
                    articles.raise_for_status()
                    return profile.json(), articles.json()

            results = await asyncio.gather(*(load(username) for username, _ in ranked), return_exceptions=True)

        candidates = []
        for (username, found), result in zip(ranked, results):
            if isinstance(result, BaseException):
                logger.debug("dev.to profile fetch failed for %s: %s", username, result)
                continue
            candidates.append(_to_candidate(username, found, *result))
        logger.info("dev.to adapter fetched %d candidates for tags %s", len(candidates), tags)
        return candidates


def _reactions(article: dict) -> int:
    return int(article.get("public_reactions_count") or article.get("positive_reactions_count") or 0)


def _to_candidate(username: str, found: list[dict], profile: dict, articles: list[dict]) -> RawCandidate:
    # The articles that matched the JD first, so their tags win ties.
    tag_lists = [canonical_list(article.get("tag_list") or []) for article in [*found, *articles]]
    best = max(found, key=_reactions)
    signals = [f'Wrote "{truncate(best.get("title"), 80)}" ({_reactions(best)} reactions)']
    github = profile.get("github_username") or (best.get("user") or {}).get("github_username")
    if github:
        signals.append(f"GitHub: github.com/{github}")
    if profile.get("website_url"):
        signals.append(f"Website: {profile['website_url']}")

    return RawCandidate(
        name=profile.get("name") or username,
        profile_url=f"https://dev.to/{username}",
        source_username=username,
        source=SourcePlatform.DEVTO,
        skills=by_frequency(tag_lists, _MAX_SKILLS),
        avatar_url=profile.get("profile_image") or None,
        bio=truncate(profile.get("summary"), 300),
        location=truncate(profile.get("location"), 100),
        experience=None,
        signals=signals[:MAX_SIGNALS],
    )
