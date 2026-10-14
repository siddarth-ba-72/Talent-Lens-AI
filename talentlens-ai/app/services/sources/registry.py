"""The sourcing platforms: what each needs configured, and when to suggest it for a JD."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.config import Settings
from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import DEVOPS_TERMS, JS_TERMS, ML_TERMS, canonical_list, jd_text
from app.services.sources.base import SourceToolAdapter
from app.services.sources.crates import CratesSourceToolAdapter
from app.services.sources.devto import DevToSourceToolAdapter
from app.services.sources.github import GitHubSourceToolAdapter
from app.services.sources.gitlab import GitLabSourceToolAdapter
from app.services.sources.hackernews import HackerNewsSourceToolAdapter
from app.services.sources.huggingface import HuggingFaceSourceToolAdapter
from app.services.sources.npm import NpmSourceToolAdapter
from app.services.sources.openalex import OpenAlexSourceToolAdapter
from app.services.sources.stackoverflow import StackOverflowSourceToolAdapter


@dataclass(frozen=True)
class _JdView:
    """What the suggestion rules look at."""

    terms: frozenset[str]
    text: str

    def mentions(self, *words: str) -> bool:
        return any(word in self.text for word in words)


def _view(parsed_jd: ParsedJdModel) -> _JdView:
    # Every term, not just the matchable ones: "machine learning" in skills counts here.
    terms = frozenset(canonical_list([*parsed_jd.technologies, *parsed_jd.skills]))
    return _JdView(terms=terms, text=jd_text(parsed_jd))


@dataclass(frozen=True)
class PlatformSpec:
    build: Callable[[Settings], SourceToolAdapter]
    # Settings attributes that must be set for the platform to be offered.
    required_settings: tuple[str, ...]
    suggest_when: Callable[[_JdView], bool]


def _always(_: _JdView) -> bool:
    return True


PLATFORMS: dict[SourcePlatform, PlatformSpec] = {
    SourcePlatform.GITHUB: PlatformSpec(
        build=lambda settings: GitHubSourceToolAdapter(settings.github_token),
        required_settings=("github_token",),
        suggest_when=_always,
    ),
    SourcePlatform.STACKOVERFLOW: PlatformSpec(
        build=lambda settings: StackOverflowSourceToolAdapter(settings.stackexchange_key),
        required_settings=(),
        suggest_when=_always,
    ),
    SourcePlatform.HACKERNEWS: PlatformSpec(
        build=lambda settings: HackerNewsSourceToolAdapter(),
        required_settings=(),
        suggest_when=_always,
    ),
    SourcePlatform.DEVTO: PlatformSpec(
        build=lambda settings: DevToSourceToolAdapter(),
        required_settings=(),
        suggest_when=lambda jd: bool(jd.terms & JS_TERMS)
        or jd.mentions("frontend", "front-end", "devrel", "developer relations", "developer advocate", "technical writ"),
    ),
    SourcePlatform.HUGGINGFACE: PlatformSpec(
        build=lambda settings: HuggingFaceSourceToolAdapter(settings.hf_token),
        required_settings=(),
        suggest_when=lambda jd: bool(jd.terms & ML_TERMS) or jd.mentions("machine learning", "deep learning"),
    ),
    SourcePlatform.NPM: PlatformSpec(
        build=lambda settings: NpmSourceToolAdapter(),
        required_settings=(),
        suggest_when=lambda jd: bool(jd.terms & JS_TERMS),
    ),
    SourcePlatform.CRATES: PlatformSpec(
        build=lambda settings: CratesSourceToolAdapter(settings.sourcing_contact),
        required_settings=("sourcing_contact",),
        suggest_when=lambda jd: "rust" in jd.terms,
    ),
    SourcePlatform.GITLAB: PlatformSpec(
        build=lambda settings: GitLabSourceToolAdapter(settings.gitlab_token),
        required_settings=("gitlab_token",),
        suggest_when=lambda jd: bool(jd.terms & DEVOPS_TERMS) or jd.mentions("gitlab", "devops"),
    ),
    SourcePlatform.OPENALEX: PlatformSpec(
        build=lambda settings: OpenAlexSourceToolAdapter(settings.openalex_api_key),
        required_settings=(),
        suggest_when=lambda jd: jd.mentions(
            "phd", "publication", "research scientist", "applied scientist", "research engineer", "peer-reviewed"
        ),
    ),
}


def is_available(platform: SourcePlatform, settings: Settings) -> bool:
    spec = PLATFORMS.get(platform)
    return spec is not None and all(getattr(settings, name, None) for name in spec.required_settings)


def available_platforms(settings: Settings) -> list[SourcePlatform]:
    return [platform for platform in PLATFORMS if is_available(platform, settings)]


def suggest_platforms(parsed_jd: ParsedJdModel, settings: Settings) -> list[SourcePlatform]:
    """The available platforms that suit this JD, in registry order."""
    view = _view(parsed_jd)
    return [
        platform for platform, spec in PLATFORMS.items()
        if is_available(platform, settings) and spec.suggest_when(view)
    ]


def build_adapters(settings: Settings) -> dict[SourcePlatform, SourceToolAdapter]:
    return {platform: spec.build(settings) for platform, spec in PLATFORMS.items()}
