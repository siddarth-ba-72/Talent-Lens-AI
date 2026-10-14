from __future__ import annotations

import html
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel


USER_AGENT = "TalentLens (candidate sourcing)"
# Signals shown per candidate; the card displays the first few.
MAX_SIGNALS = 5


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
    signals: list[str] = field(default_factory=list)
    open_to_work: bool = False


class SourceToolAdapter:
    """Finds candidates on one platform.

    Adapters are shared across runs (the workflow service is cached), so keep
    per-run state in locals, never on `self`.
    """

    def __init__(self, platform: SourcePlatform, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.platform = platform
        # Tests pass an httpx.MockTransport; None means real network calls.
        self._transport = transport

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        _ = query_terms, parsed_jd
        return []

    def _client(self, **kwargs: Any) -> httpx.AsyncClient:
        kwargs.setdefault("timeout", 20.0)
        headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
        return httpx.AsyncClient(transport=self._transport, headers=headers, **kwargs)


def strip_html(value: Optional[str]) -> str:
    """Plain text from an HTML fragment, one line per paragraph or line break."""
    if not value:
        return ""
    text = re.sub(r"(?i)<\s*(p|br|li|div)\b[^>]*>", "\n", value)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = (re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def html_links(value: Optional[str]) -> list[str]:
    return [html.unescape(link) for link in re.findall(r'href="([^"]+)"', value or "")]


def truncate(value: Optional[str], limit: int) -> Optional[str]:
    if not value:
        return None
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def parse_time(value: Any) -> Optional[datetime]:
    """An ISO-8601 string or epoch seconds, as an aware datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def years_since(value: Optional[datetime], now: Optional[datetime] = None) -> Optional[float]:
    if value is None:
        return None
    return ((now or datetime.now(timezone.utc)) - value).days / 365.25


def by_frequency(groups: Iterable[Iterable[str]], limit: int) -> list[str]:
    """Items ordered by how many groups contain them (ties keep first-seen order)."""
    counts: Counter[str] = Counter()
    order: dict[str, None] = {}
    for group in groups:
        for item in dict.fromkeys(group):
            counts[item] += 1
            order.setdefault(item, None)
    return sorted(order, key=lambda item: -counts[item])[:limit]


def compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    return str(value)


def merge_terms(*groups: Iterable[str], limit: int) -> list[str]:
    seen: dict[str, None] = {}
    for group in groups:
        for term in group:
            if term:
                seen.setdefault(term, None)
    return list(seen)[:limit]
