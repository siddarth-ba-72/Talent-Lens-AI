"""Owners of Rust crates in the JD's area. crates.io owners are GitHub accounts."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import canonical, jd_terms, single_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    compact_number,
    merge_terms,
)
from app.services.sources.throttle import MinIntervalLimiter


logger = logging.getLogger(__name__)

_API = "https://crates.io/api/v1"
_MAX_KEYWORDS = 2
_CRATES_PER_KEYWORD = 5
# crates.io's data-access policy: at most one request per second, with a
# User-Agent that names the app and a way to contact its operator.
_LIMITER = MinIntervalLimiter(1.0)


@dataclass(frozen=True)
class _Crate:
    name: str
    recent_downloads: int
    keyword: str


class CratesSourceToolAdapter(SourceToolAdapter):
    def __init__(
        self,
        contact: Optional[str],
        transport: Optional[httpx.AsyncBaseTransport] = None,
        limiter: Optional[MinIntervalLimiter] = None,
    ):
        super().__init__(SourcePlatform.CRATES, transport)
        self._contact = contact
        self._limiter = limiter or _LIMITER

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        if not self._contact:
            logger.warning("SOURCING_CONTACT not configured — skipping crates.io sourcing")
            return []
        keywords = merge_terms(
            (canonical(term) for term in [*single_terms(query_terms), *jd_terms(parsed_jd)] if canonical(term) != "rust"),
            limit=_MAX_KEYWORDS,
        )
        if not keywords:
            return []

        headers = {"User-Agent": f"TalentLens candidate sourcing ({self._contact})"}
        async with self._client(headers=headers) as client:
            crates: list[_Crate] = []
            for keyword in keywords:
                try:
                    body = await self._get(client, "/crates", {
                        "q": keyword, "sort": "recent-downloads", "per_page": _CRATES_PER_KEYWORD,
                    })
                except Exception as exc:
                    logger.warning("crates.io search for %r failed: %s", keyword, exc)
                    continue
                for item in body.get("crates", []):
                    if item.get("name") and all(crate.name != item["name"] for crate in crates):
                        crates.append(_Crate(item["name"], int(item.get("recent_downloads") or 0), keyword))

            # login -> (owner record, crates they own)
            owners: dict[str, tuple[dict, list[_Crate]]] = {}
            for crate in crates:
                try:
                    body = await self._get(client, f"/crates/{quote(crate.name, safe='')}/owners")
                except Exception as exc:
                    logger.debug("crates.io owners for %s failed: %s", crate.name, exc)
                    continue
                for user in body.get("users", []):
                    login = user.get("login") or ""
                    # Teams are GitHub teams ("github:org:team"), not people.
                    if login and user.get("kind", "user") == "user":
                        owners.setdefault(login, (user, []))[1].append(crate)

        candidates = [_to_candidate(user, owned) for user, owned in owners.values()]
        candidates.sort(key=lambda candidate: candidate.source_username)
        logger.info("crates.io adapter fetched %d candidates from %d crates", len(candidates), len(crates))
        return candidates

    async def _get(self, client: httpx.AsyncClient, path: str, params: Optional[dict] = None) -> dict:
        await self._limiter.wait()
        response = await client.get(f"{_API}{path}", params=params)
        response.raise_for_status()
        return response.json()


def _to_candidate(user: dict, owned: list[_Crate]) -> RawCandidate:
    login = user["login"]
    owned = sorted(owned, key=lambda crate: -crate.recent_downloads)
    signals = [
        f"Owns crate {crate.name} ({compact_number(crate.recent_downloads)} recent downloads)" for crate in owned[:3]
    ]
    return RawCandidate(
        name=user.get("name") or login,
        # The owner record links the GitHub profile the login belongs to.
        profile_url=user.get("url") or f"https://github.com/{login}",
        source_username=login,
        source=SourcePlatform.CRATES,
        skills=merge_terms(["rust"], (crate.keyword for crate in owned), limit=10),
        avatar_url=user.get("avatar") or None,
        experience=None,
        signals=signals[:MAX_SIGNALS],
    )
