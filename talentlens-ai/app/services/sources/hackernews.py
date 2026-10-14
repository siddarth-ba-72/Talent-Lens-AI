"""People who posted in Hacker News' monthly "Ask HN: Who wants to be hired?" thread.

Posts follow the thread's template (Location / Remote / Willing to relocate /
Technologies / Résumé/CV / Email), so they parse without an LLM.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.scoring_service import YEARS_PATTERN
from app.services.skill_vocabulary import canonical, canonical_list, jd_terms, single_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    html_links,
    merge_terms,
    strip_html,
    truncate,
)


logger = logging.getLogger(__name__)

_API = "https://hn.algolia.com/api/v1"
_THREAD_PREFIX = "Ask HN: Who wants to be hired?"
_LOOKBACK_THREADS = 2
_MAX_KEYWORDS = 5
_HITS_PER_SEARCH = 100
_MAX_POSTS = 30
_MAX_SKILLS = 25

_FIELD_LINE = re.compile(r"^\s*([^:\n]{2,30}?)\s*:\s*(.+)$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_KEY_FIELDS = {
    "location": "location",
    "remote": "remote",
    "willing to relocate": "relocate",
    "relocate": "relocate",
    "relocation": "relocate",
    "technologies": "skills",
    "technology": "skills",
    "tech": "skills",
    "tech stack": "skills",
    "stack": "skills",
    "skills": "skills",
    "languages": "skills",
    "email": "email",
    "e-mail": "email",
    "contact": "email",
    "experience": "experience",
    "years of experience": "experience",
    "yoe": "experience",
    "résumé/cv": "resume",
    "resume/cv": "resume",
    "résumé": "resume",
    "resume": "resume",
    "cv": "resume",
    "github": "github",
    "website": "website",
    "portfolio": "website",
}


@dataclass
class HnPost:
    """The fields of one post, as written."""

    text: str
    fields: dict[str, str] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)


class HackerNewsSourceToolAdapter(SourceToolAdapter):
    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.HACKERNEWS, transport)

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        keywords = merge_terms(
            (canonical(term) for term in single_terms(query_terms)), jd_terms(parsed_jd), limit=_MAX_KEYWORDS
        )
        if not keywords:
            return []

        async with self._client() as client:
            threads = await _latest_threads(client)
            # objectID -> (hit, keywords it matched)
            matches: dict[str, tuple[dict, set[str]]] = {}
            for thread_id, _ in threads:
                for keyword in keywords:
                    try:
                        response = await client.get(
                            f"{_API}/search",
                            params={"tags": f"comment,story_{thread_id}", "query": keyword, "hitsPerPage": _HITS_PER_SEARCH},
                        )
                        response.raise_for_status()
                    except Exception as exc:
                        logger.warning("HN search for %r in %s failed: %s", keyword, thread_id, exc)
                        continue
                    for hit in response.json().get("hits", []):
                        # Only top-level posts; replies are other people talking to the poster.
                        if str(hit.get("parent_id")) != thread_id or not hit.get("author"):
                            continue
                        entry = matches.setdefault(hit["objectID"], (hit, set()))
                        entry[1].add(keyword)

        titles = dict(threads)
        # One post per person (the newest), most keywords matched first.
        newest: dict[str, tuple[dict, set[str]]] = {}
        for hit, matched in sorted(matches.values(), key=lambda entry: -(entry[0].get("created_at_i") or 0)):
            newest.setdefault(hit["author"], (hit, matched))
        ranked = sorted(newest.values(), key=lambda entry: (-len(entry[1]), -(entry[0].get("created_at_i") or 0)))

        candidates = [
            _to_candidate(hit, matched, titles.get(str(hit.get("story_id")), ""))
            for hit, matched in ranked[:_MAX_POSTS]
        ]
        logger.info("HN adapter fetched %d candidates from %d threads", len(candidates), len(threads))
        return candidates


async def _latest_threads(client: httpx.AsyncClient) -> list[tuple[str, str]]:
    """(story id, title) of the latest "Who wants to be hired?" threads, newest first."""
    response = await client.get(
        f"{_API}/search_by_date",
        params={"tags": "story,author_whoishiring", "query": "who wants to be hired", "hitsPerPage": 6},
    )
    response.raise_for_status()
    threads = [
        (str(hit["objectID"]), hit.get("title") or "")
        for hit in response.json().get("hits", [])
        if (hit.get("title") or "").startswith(_THREAD_PREFIX)
    ]
    return threads[:_LOOKBACK_THREADS]


def parse_post(comment_html: str) -> HnPost:
    text = strip_html(comment_html)
    post = HnPost(text=text, links=html_links(comment_html))
    for line in text.split("\n"):
        match = _FIELD_LINE.match(line)
        if not match:
            continue
        key = " ".join(match.group(1).lower().split())
        name = _KEY_FIELDS.get(key)
        if name and name not in post.fields:
            post.fields[name] = match.group(2).strip()
    return post


def deobfuscate_email(value: str) -> Optional[str]:
    text = re.sub(r"\s*[\[\(\{<]\s*at\s*[\]\)\}>]\s*|\s+at\s+", "@", value, flags=re.IGNORECASE)
    text = re.sub(r"\s*[\[\(\{<]\s*dot\s*[\]\)\}>]\s*|\s+dot\s+", ".", text, flags=re.IGNORECASE)
    match = _EMAIL.search(text)
    return match.group(0) if match else None


def _split_skills(value: str) -> list[str]:
    return canonical_list(re.split(r"[,;/|]|\band\b", value), limit=_MAX_SKILLS)


def _to_candidate(hit: dict, matched: set[str], thread_title: str) -> RawCandidate:
    post = parse_post(hit.get("comment_text") or "")
    fields = post.fields

    skills = _split_skills(fields["skills"]) if "skills" in fields else []
    # Posts outside the template: at least the JD keywords they were found by.
    skills = merge_terms(skills, sorted(matched), limit=_MAX_SKILLS)

    email = deobfuscate_email(fields["email"]) if "email" in fields else None
    if email is None:
        mailto = next((link for link in post.links if link.lower().startswith("mailto:")), None)
        email = deobfuscate_email(mailto[len("mailto:"):]) if mailto else None

    experience = fields.get("experience")
    if not experience:
        years = YEARS_PATTERN.search(post.text)
        experience = f"{years.group(1)} years" if years else None

    month = re.search(r"\(([^)]+)\)\s*$", thread_title)
    signals = [f'Posted in "Who wants to be hired?"' + (f" ({month.group(1)})" if month else "")]
    for name, label in (("remote", "Remote"), ("relocate", "Willing to relocate")):
        if fields.get(name):
            signals.append(f"{label}: {truncate(fields[name], 60)}")
    for name, label in (("resume", "Résumé"), ("github", "GitHub"), ("website", "Website")):
        if fields.get(name):
            signals.append(f"{label}: {truncate(fields[name], 100)}")

    author = hit["author"]
    return RawCandidate(
        name=author,
        # The post, not the user page: the post has the CV, links and contact details.
        profile_url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
        source_username=author,
        source=SourcePlatform.HACKERNEWS,
        skills=skills,
        email=email,
        bio=truncate(post.text, 300),
        location=truncate(fields.get("location"), 100),
        experience=truncate(experience, 60),
        signals=signals[:MAX_SIGNALS],
        open_to_work=True,
    )
