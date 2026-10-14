"""Authors of recent research papers on the JD's topics (research / applied-science roles)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import canonical_list, jd_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    merge_terms,
    truncate,
)


logger = logging.getLogger(__name__)

_API = "https://api.openalex.org"
_MAX_PHRASES = 2
_WORKS_PER_PHRASE = 50
_LOOKBACK_YEARS = 3
_MAX_AUTHORS = 20
_MAX_SKILLS = 15


class OpenAlexSourceToolAdapter(SourceToolAdapter):
    def __init__(self, api_key: Optional[str], transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.OPENALEX, transport)
        self._api_key = api_key

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        terms = jd_terms(parsed_jd)
        # Research phrases from the LLM; otherwise the JD's leading terms one at a time.
        phrases = merge_terms(
            (query.strip() for query in query_terms), (term.replace("-", " ") for term in terms), limit=_MAX_PHRASES
        )
        if not phrases:
            return []

        since = f"{datetime.now(timezone.utc).year - _LOOKBACK_YEARS}-01-01"
        async with self._client() as client:
            # author id -> (name, works of theirs that matched)
            authors: dict[str, tuple[str, list[dict]]] = {}
            for phrase in phrases:
                try:
                    body = await self._get(client, "/works", {
                        "search": phrase,
                        "filter": f"from_publication_date:{since}",
                        "per-page": _WORKS_PER_PHRASE,
                        "select": "id,title,publication_year,authorships,cited_by_count",
                    })
                except Exception as exc:
                    logger.warning("OpenAlex works search for %r failed: %s", phrase, exc)
                    continue
                for work in body.get("results", []):
                    for authorship in work.get("authorships") or []:
                        author = authorship.get("author") or {}
                        author_id = _short_id(author.get("id"))
                        if author_id:
                            entry = authors.setdefault(author_id, (author.get("display_name") or author_id, []))
                            if work not in entry[1]:
                                entry[1].append(work)

            ranked = sorted(
                authors.items(),
                key=lambda entry: (-len(entry[1][1]), -sum(int(work.get("cited_by_count") or 0) for work in entry[1][1])),
            )[:_MAX_AUTHORS]
            if not ranked:
                return []

            try:
                body = await self._get(client, "/authors", {
                    "filter": "ids.openalex:" + "|".join(author_id for author_id, _ in ranked),
                    "per-page": _MAX_AUTHORS,
                    "select": "id,display_name,orcid,last_known_institutions,topics,works_count,summary_stats",
                })
                profiles = {_short_id(item.get("id")): item for item in body.get("results", [])}
            except Exception as exc:
                logger.warning("OpenAlex author lookup failed: %s", exc)
                profiles = {}

        candidates = [
            _to_candidate(author_id, name, works, profiles.get(author_id, {}), terms)
            for author_id, (name, works) in ranked
        ]
        logger.info("OpenAlex adapter fetched %d candidates for %s", len(candidates), phrases)
        return candidates

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> dict:
        if self._api_key:
            params = {**params, "api_key": self._api_key}
        response = await client.get(f"{_API}{path}", params=params)
        response.raise_for_status()
        return response.json()


def _short_id(value: Optional[str]) -> Optional[str]:
    """"https://openalex.org/A5095693000" -> "A5095693000"."""
    if not value:
        return None
    short = value.rstrip("/").rsplit("/", 1)[-1]
    return short if re.fullmatch(r"A\d+", short) else None


def _to_candidate(author_id: str, name: str, works: list[dict], profile: dict, jd_terms_: list[str]) -> RawCandidate:
    titles = " ".join((work.get("title") or "").lower() for work in works)
    # The JD terms their matching papers are actually about, then their research topics.
    title_terms = [term for term in jd_terms_ if term.replace("-", " ") in titles]
    # Research topics ("Cloud Computing and Resource Management") keep their own names.
    topics = [topic["display_name"] for topic in (profile.get("topics") or [])[:8] if topic.get("display_name")]
    skills = merge_terms(canonical_list(title_terms), topics, limit=_MAX_SKILLS)

    institution = next(iter(profile.get("last_known_institutions") or []), {}) or {}
    location = ", ".join(part for part in (institution.get("display_name"), institution.get("country_code")) if part)

    best = max(works, key=lambda work: int(work.get("cited_by_count") or 0))
    signals = [f'Paper "{truncate(best.get("title"), 90)}" ({best.get("publication_year")})']
    h_index = (profile.get("summary_stats") or {}).get("h_index")
    if h_index:
        signals.append(f"h-index {h_index}")
    if institution.get("display_name"):
        signals.append(f"Institution: {institution['display_name']}")

    return RawCandidate(
        name=profile.get("display_name") or name,
        profile_url=profile.get("orcid") or f"https://openalex.org/{author_id}",
        source_username=author_id,
        source=SourcePlatform.OPENALEX,
        skills=skills,
        location=location or None,
        experience=None,
        signals=signals[:MAX_SIGNALS],
    )
