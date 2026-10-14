"""dev.to, Hugging Face, npm and crates.io adapters against canned API responses."""

from __future__ import annotations

import asyncio

import httpx

from app.models.jd_models import ParsedJdModel
from app.services.sources.crates import CratesSourceToolAdapter
from app.services.sources.devto import DevToSourceToolAdapter
from app.services.sources.huggingface import HuggingFaceSourceToolAdapter, hf_filters
from app.services.sources.npm import NpmSourceToolAdapter
from app.services.sources.throttle import MinIntervalLimiter


def _article(username: str, reactions: int, tags: list[str], ai: str = "no_ai") -> dict:
    return {
        "title": f"{username} on {tags[0]}", "tag_list": tags, "public_reactions_count": reactions,
        "ai_disclosure_level": ai, "user": {"username": username, "github_username": f"{username}-gh"},
    }


def test_devto_authors(fake_http):
    transport = fake_http({
        "dev.to/api/articles": lambda request: httpx.Response(200, json=(
            [_article("writer", 40, ["node", "postgres"]), _article("tiny", 1, ["node"]),
             _article("bot", 99, ["node"], ai="fully_ai")]
            if "tag" in request.url.params
            else [_article("writer", 3, ["typescript", "node"])]
        )),
        "dev.to/api/users/by_username": {"name": "Wri Ter", "location": "Pune", "summary": "Backend dev"},
    })
    adapter = DevToSourceToolAdapter(transport=transport)

    candidates = asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["Node.js"])))

    # Too few reactions, or AI-written beyond "some help": skipped.
    assert [candidate.source_username for candidate in candidates] == ["writer"]
    writer = candidates[0]
    assert writer.skills[:2] == ["node.js", "postgresql"]
    assert "typescript" in writer.skills
    assert writer.location == "Pune"
    assert "GitHub: github.com/writer-gh" in writer.signals
    tag_call = next(request for request in transport.requests if "tag" in request.url.params)
    assert tag_call.url.params["tag"] == "node"


def test_huggingface_filters_come_from_ml_terms():
    assert hf_filters(["PyTorch", "LLM", "Kafka", "NER"]) == ["pytorch", "text-generation", "token-classification"]
    assert hf_filters(["Kafka", "Go"]) == []


def test_huggingface_skips_reuploads_and_orgs(fake_http):
    transport = fake_http({
        "huggingface.co/api/models": lambda request: httpx.Response(200, json=(
            [
                {"id": "TheBloke/big-GGUF", "likes": 999, "tags": ["gguf", "pytorch"]},
                {"id": "bigorg/flagship", "likes": 500, "tags": ["pytorch", "text-generation"]},
                {"id": "alice/ner-small", "likes": 50, "tags": ["pytorch", "token-classification"]},
            ]
            if "library" in request.url.params
            else [{"id": "alice/ner-small", "tags": ["pytorch", "token-classification", "license:mit"]}]
        )),
        "huggingface.co/api/users/alice/overview": {
            "fullname": "Alice A", "avatarUrl": "/avatars/a.svg", "numFollowers": 80, "orgs": [{"name": "acme-ai"}],
        },
        "huggingface.co/api/users/bigorg/overview": (404, {"error": "not a user"}),
    })
    adapter = HuggingFaceSourceToolAdapter(None, transport=transport)

    candidates = asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["PyTorch"])))

    assert [candidate.source_username for candidate in candidates] == ["alice"]
    alice = candidates[0]
    assert {"pytorch", "token-classification", "python"} <= set(alice.skills)
    assert "license:mit" not in alice.skills
    assert alice.avatar_url == "https://huggingface.co/avatars/a.svg"
    assert alice.signals[0] == "Author of alice/ner-small (50 likes)"
    assert "Member of acme-ai" in alice.signals


def test_npm_maintainers_without_emails(fake_http):
    def search(request):
        if request.url.params["text"].startswith("maintainer:"):
            return httpx.Response(200, json={"objects": [{"package": {"keywords": ["react", "hooks"]}}]})
        return httpx.Response(200, json={"objects": [
            {"package": {"name": "react-thing", "links": {"repository": "https://github.com/alice/react-thing"},
                         "maintainers": [{"username": "alice", "email": "alice@example.com"},
                                         {"username": "renovate-bot", "email": "bot@example.com"}]},
             "downloads": {"monthly": 50_000}},
            {"package": {"name": "@acme/ui", "maintainers": [{"username": "acme-publisher"}]},
             "downloads": {"monthly": 90_000}},
            {"package": {"name": "unused", "maintainers": [{"username": "nobody"}]}, "downloads": {"monthly": 12}},
        ]})

    adapter = NpmSourceToolAdapter(transport=fake_http({"registry.npmjs.org/-/v1/search": search}))

    candidates = asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["React"])))

    assert [candidate.source_username for candidate in candidates] == ["alice"]
    alice = candidates[0]
    assert alice.email is None
    assert alice.skills[0] == "react"
    assert alice.signals[0] == "Maintains react-thing (50k downloads/month)"
    assert "Repo: https://github.com/alice/react-thing" in alice.signals


def test_crates_owners_are_github_accounts(fake_http):
    transport = fake_http({
        "crates.io/api/v1/crates": {"crates": [{"name": "tokio-kafka", "recent_downloads": 12_000}]},
        "crates.io/api/v1/crates/tokio-kafka/owners": {"users": [
            {"login": "ferris", "kind": "user", "name": "Ferris", "url": "https://github.com/ferris"},
            {"login": "github:acme:core", "kind": "team"},
        ]},
    })
    adapter = CratesSourceToolAdapter("ops@example.com", transport=transport, limiter=MinIntervalLimiter(0))

    candidates = asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["Rust", "Kafka"])))

    assert [candidate.source_username for candidate in candidates] == ["ferris"]
    ferris = candidates[0]
    assert ferris.profile_url == "https://github.com/ferris"
    assert ferris.skills == ["rust", "kafka"]
    assert "ops@example.com" in transport.requests[0].headers["User-Agent"]
    # "rust" itself is not searched: every crate is Rust.
    assert transport.requests[0].url.params["q"] == "kafka"


def test_crates_needs_a_contact(fake_http):
    transport = fake_http({})

    assert asyncio.run(CratesSourceToolAdapter(None, transport=transport).fetch_candidates([], ParsedJdModel())) == []
    assert transport.requests == []


def test_huggingface_retries_a_busy_hub(fake_http, monkeypatch):
    from app.services.sources import huggingface

    async def no_wait(seconds):
        return None

    monkeypatch.setattr(huggingface.asyncio, "sleep", no_wait)
    answers = iter([httpx.Response(504, json={"error": "busy"}), httpx.Response(200, json=[])])
    transport = fake_http({"huggingface.co/api/models": lambda request: next(answers)})

    adapter = HuggingFaceSourceToolAdapter(None, transport=transport)

    assert asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["PyTorch"]))) == []
    assert len(transport.requests) == 2
    assert transport.requests[0].url.params["library"] == "pytorch"
