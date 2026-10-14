from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.models.jd_models import ParsedJdModel
from app.services.sources.github import GitHubSourceToolAdapter, infer_experience


API = "api.github.com"
JD = ParsedJdModel(technologies=["Kafka"], skills=["Go"], experienceLevel="Senior")
RECENT = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
STALE = (datetime.now(timezone.utc) - timedelta(days=800)).isoformat()


def _routes():
    return {
        f"{API}/search/repositories": {
            "items": [{"full_name": "acme/stream", "language": "Go", "topics": ["kafka", "event-driven"]}]
        },
        f"{API}/repos/acme/stream/contributors": [
            {"login": "alice", "type": "User", "contributions": 40},
            {"login": "dependabot[bot]", "type": "Bot", "contributions": 300},
            {"login": "drive-by", "type": "User", "contributions": 2},
        ],
        f"{API}/search/users": {
            "items": [{"login": "bob", "type": "User"}, {"login": "acme-org", "type": "Organization"}]
        },
        f"{API}/users/alice": {
            "login": "alice", "type": "User", "name": "Alice", "hireable": True, "followers": 150,
            "created_at": "2012-03-01T00:00:00Z", "html_url": "https://github.com/alice", "blog": "alice.dev",
        },
        f"{API}/users/alice/repos": [
            {"language": "Java", "fork": True, "topics": ["spring"], "pushed_at": RECENT, "stargazers_count": 900},
            {"language": "Go", "fork": False, "topics": ["grpc"], "pushed_at": RECENT, "stargazers_count": 120},
        ],
        f"{API}/users/bob": {"login": "bob", "type": "User", "created_at": "2015-01-01T00:00:00Z"},
        f"{API}/users/bob/repos": [{"language": "Go", "fork": False, "topics": [], "pushed_at": STALE}],
    }


def test_contributors_are_found_and_described(fake_http):
    transport = fake_http(_routes())
    adapter = GitHubSourceToolAdapter("token", transport=transport)

    candidates = asyncio.run(adapter.fetch_candidates(["language:go"], JD))

    # Bots and drive-by contributors are skipped; bob has no recent activity of his own.
    assert [candidate.source_username for candidate in candidates] == ["alice"]
    alice = candidates[0]
    assert {"go", "kafka", "grpc"} <= set(alice.skills)
    assert "java" not in alice.skills  # forks don't count
    assert alice.open_to_work is True
    assert alice.signals[0] == "Marked hireable on GitHub"
    assert "Contributor to acme/stream (40 commits)" in alice.signals
    assert alice.experience == "senior"

    user_search = next(request for request in transport.requests if request.url.path == "/search/users")
    assert "sort" not in user_search.url.params
    repos_call = next(request for request in transport.requests if request.url.path == "/users/alice/repos")
    assert repos_call.url.params["sort"] == "pushed"
    assert transport.requests[0].headers["Authorization"] == "Bearer token"


def test_stops_calling_when_rate_limited(fake_http):
    limited = (lambda request: httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, json={}))
    transport = fake_http({f"{API}/search/repositories": limited, f"{API}/search/users": limited})
    adapter = GitHubSourceToolAdapter("token", transport=transport)

    assert asyncio.run(adapter.fetch_candidates(["language:go"], JD)) == []
    assert len(transport.requests) == 1


def test_without_token_nothing_is_called(fake_http):
    transport = fake_http({})

    assert asyncio.run(GitHubSourceToolAdapter(None, transport=transport).fetch_candidates([], JD)) == []
    assert transport.requests == []


def test_experience_heuristic():
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    recent = now - timedelta(days=30)

    assert infer_experience(datetime(2012, 1, 1, tzinfo=timezone.utc), 500, 0, recent, now) == "senior"
    assert infer_experience(datetime(2020, 1, 1, tzinfo=timezone.utc), 0, 0, recent, now) == "mid"
    assert infer_experience(datetime(2025, 6, 1, tzinfo=timezone.utc), 0, 0, recent, now) == "junior"
    # Unclear cases score as neutral rather than being labelled junior.
    assert infer_experience(datetime(2020, 1, 1, tzinfo=timezone.utc), 0, 0, None, now) is None
