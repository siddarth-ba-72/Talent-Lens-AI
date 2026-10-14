"""Platform registry, ranking across platforms, the throttle, and the sourcing request/route."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import platforms as platforms_api
from app.config import get_settings
from app.models.candidate_models import SourcePlatform, SourcingRequestPayloadModel, SourcingStatus
from app.models.jd_models import ParsedJdModel
from app.models.search_models import SourcingRequest
from app.security.auth import require_recruiter
from app.services.sources.base import RawCandidate, SourceToolAdapter
from app.services.sources.registry import available_platforms, is_available, suggest_platforms
from app.services.sources.throttle import MinIntervalLimiter
from app.services.sourcing_workflow_service import SourcingWorkflowService


def _with(settings, **values):
    return settings.model_copy(update=values)


def test_platforms_needing_credentials_are_unavailable_without_them(settings):
    assert not is_available(SourcePlatform.GITHUB, settings)
    assert not is_available(SourcePlatform.GITLAB, settings)
    assert not is_available(SourcePlatform.CRATES, settings)
    assert is_available(SourcePlatform.STACKOVERFLOW, settings)
    assert is_available(SourcePlatform.HACKERNEWS, settings)

    configured = _with(settings, github_token="t", gitlab_token="t", sourcing_contact="ops@example.com")
    assert set(available_platforms(configured)) >= {SourcePlatform.GITHUB, SourcePlatform.GITLAB, SourcePlatform.CRATES}


@pytest.mark.parametrize(
    ("parsed", "expected", "unexpected"),
    [
        (ParsedJdModel(technologies=["PyTorch", "Python"]), {SourcePlatform.HUGGINGFACE}, {SourcePlatform.NPM}),
        (ParsedJdModel(technologies=["React", "TypeScript"]), {SourcePlatform.NPM, SourcePlatform.DEVTO},
         {SourcePlatform.HUGGINGFACE}),
        (ParsedJdModel(technologies=["Rust", "Tokio"]), {SourcePlatform.CRATES}, {SourcePlatform.NPM}),
        (ParsedJdModel(technologies=["Terraform"], summary="DevOps engineer"), {SourcePlatform.GITLAB}, set()),
        (ParsedJdModel(technologies=["Python"], qualifications=["PhD in computer science"]),
         {SourcePlatform.OPENALEX}, {SourcePlatform.CRATES}),
    ],
)
def test_suggestions_follow_the_jd(settings, parsed, expected, unexpected):
    configured = _with(settings, github_token="t", gitlab_token="t", sourcing_contact="ops@example.com")

    suggested = set(suggest_platforms(parsed, configured))

    general = {SourcePlatform.GITHUB, SourcePlatform.STACKOVERFLOW, SourcePlatform.HACKERNEWS}
    assert general <= suggested
    assert expected <= suggested
    assert not unexpected & suggested


def test_suggestions_skip_unconfigured_platforms(settings):
    suggested = suggest_platforms(ParsedJdModel(technologies=["Rust"]), settings)

    assert SourcePlatform.CRATES not in suggested
    assert SourcePlatform.GITHUB not in suggested


class _Provider:
    def generate_queries(self, parsed_jd, platforms):
        return {platform: [] for platform in platforms}


class _Adapter(SourceToolAdapter):
    def __init__(self, platform, candidates=None, error=None):
        super().__init__(platform)
        self._candidates = candidates or []
        self._error = error
        self.seen_jd = None

    async def fetch_candidates(self, query_terms, parsed_jd):
        self.seen_jd = parsed_jd
        if self._error:
            raise self._error
        return self._candidates


def _raw(platform, username, skills, open_to_work=False):
    return RawCandidate(
        name=username, profile_url=f"https://example.com/{username}", source_username=username,
        source=platform, skills=skills, open_to_work=open_to_work,
    )


def _payload(platforms, parsed):
    return SourcingRequestPayloadModel(
        taskId="t", searchId="s", runId="r", parsedJd=parsed, platforms=platforms,
        timestamp=datetime.now(timezone.utc),
    )


def test_each_platform_keeps_its_best_three_places(settings):
    parsed = ParsedJdModel(technologies=["Go", "Kafka"])
    strong = [_raw(SourcePlatform.GITHUB, f"gh{index:02d}", ["go", "kafka"]) for index in range(25)]
    weak = [_raw(SourcePlatform.OPENALEX, f"A{index}", ["Distributed computing"]) for index in range(5)]
    github = _Adapter(SourcePlatform.GITHUB, strong)
    workflow = SourcingWorkflowService(_Provider(), settings, adapters={
        SourcePlatform.GITHUB: github,
        SourcePlatform.OPENALEX: _Adapter(SourcePlatform.OPENALEX, weak),
    })

    result = asyncio.run(workflow.run(_payload([SourcePlatform.GITHUB, SourcePlatform.OPENALEX], parsed)))

    sources = [candidate.source for candidate in result.candidates]
    assert len(sources) == 20
    assert sources.count(SourcePlatform.OPENALEX) == 3
    assert sources[-3:] == [SourcePlatform.OPENALEX] * 3  # still listed by score
    assert github.seen_jd == parsed


def test_open_to_work_wins_ties_and_failures_are_reported(settings):
    parsed = ParsedJdModel(technologies=["Go"])
    workflow = SourcingWorkflowService(_Provider(), settings, adapters={
        SourcePlatform.GITHUB: _Adapter(SourcePlatform.GITHUB, [_raw(SourcePlatform.GITHUB, "aaa", ["go"])]),
        SourcePlatform.HACKERNEWS: _Adapter(
            SourcePlatform.HACKERNEWS, [_raw(SourcePlatform.HACKERNEWS, "zzz", ["go"], open_to_work=True)]
        ),
        SourcePlatform.STACKOVERFLOW: _Adapter(SourcePlatform.STACKOVERFLOW, error=RuntimeError("quota")),
    })

    result = asyncio.run(workflow.run(_payload(
        [SourcePlatform.GITHUB, SourcePlatform.HACKERNEWS, SourcePlatform.STACKOVERFLOW], parsed
    )))

    assert result.status == SourcingStatus.COMPLETED
    assert [candidate.sourceUsername for candidate in result.candidates] == ["zzz", "aaa"]
    assert result.error == "STACKOVERFLOW: quota"


def test_limiter_spaces_calls():
    limiter = MinIntervalLimiter(0.05)

    async def three_calls():
        await asyncio.gather(limiter.wait(), limiter.wait(), limiter.wait())

    started = time.monotonic()
    asyncio.run(three_calls())
    assert time.monotonic() - started >= 0.09


def test_sourcing_request_needs_platforms_unless_auto():
    assert SourcingRequest(auto=True).platforms == []
    assert SourcingRequest(platforms=["GITHUB"]).auto is False
    with pytest.raises(ValidationError):
        SourcingRequest(platforms=[])


def test_platforms_route_reports_availability(settings, make_user):
    app = FastAPI()
    app.include_router(platforms_api.router)
    app.dependency_overrides[get_settings] = lambda: _with(settings, github_token="t")
    app.dependency_overrides[require_recruiter] = lambda: make_user()

    body = TestClient(app).get("/api/sourcing/platforms").json()

    availability = {item["platform"]: item["available"] for item in body}
    assert availability["GITHUB"] is True
    assert availability["GITLAB"] is False
    assert "LEETCODE" not in availability
