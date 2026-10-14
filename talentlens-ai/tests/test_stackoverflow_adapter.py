from __future__ import annotations

import asyncio
import time

import httpx

from app.models.jd_models import ParsedJdModel
from app.services.sources import stackoverflow
from app.services.sources.stackoverflow import StackOverflowSourceToolAdapter


JD = ParsedJdModel(technologies=["Golang", "Kafka", "NotARealTag"])
NOW = int(time.time())


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/info"):
        # Synonyms come back as their master tag; unknown tags are dropped.
        return httpx.Response(200, json={"items": [{"name": "apache-kafka"}, {"name": "go"}], "quota_remaining": 280})
    if path == "/2.3/tags/go/top-answerers/all_time":
        return httpx.Response(200, json={"items": [
            {"user": {"user_id": 1, "user_type": "registered"}, "score": 100},
            {"user": {"user_id": 2, "user_type": "unregistered"}, "score": 90},
        ]})
    if path == "/2.3/tags/apache-kafka/top-answerers/all_time":
        return httpx.Response(200, json={"items": [
            {"user": {"user_id": 1, "user_type": "registered"}, "score": 40},
            {"user": {"user_id": 3, "user_type": "registered"}, "score": 70},
        ]})
    if path == "/2.3/users/1;3":
        return httpx.Response(200, json={"items": [
            {
                "user_id": 1, "display_name": "Ren&eacute; O&#39;Neil", "location": "Z&uuml;rich",
                "reputation": 12400, "last_access_date": NOW, "link": "https://stackoverflow.com/users/1/rene",
                "about_me": "<p>Distributed systems.</p>",
            },
            {"user_id": 3, "display_name": "Gone", "last_access_date": NOW - 3 * 365 * 86400},
        ]})
    if path == "/2.3/users/1/top-tags":
        return httpx.Response(200, json={"items": [{"tag_name": "go"}, {"tag_name": "postgresql"}]})
    return httpx.Response(404, json={"error_id": 404, "error_message": "no route"})


def test_top_answerers_become_candidates():
    transport = httpx.MockTransport(_handler)
    adapter = StackOverflowSourceToolAdapter("app-key", transport=transport)

    candidates = asyncio.run(adapter.fetch_candidates([], JD))

    # Unregistered and long-inactive users are dropped.
    assert [candidate.source_username for candidate in candidates] == ["1"]
    rene = candidates[0]
    assert rene.name == "René O'Neil"
    assert rene.location == "Zürich"
    assert rene.bio == "Distributed systems."
    assert {"go", "kafka", "postgresql"} <= set(rene.skills)
    assert rene.signals[0] == "Top answerer in [go], [apache-kafka]"
    assert rene.experience is None


def test_sends_key_and_waits_on_backoff(monkeypatch):
    seen: list[httpx.Request] = []
    slept: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/info"):
            return httpx.Response(200, json={"items": [{"name": "go"}], "backoff": 5})
        return httpx.Response(200, json={"items": []})

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(stackoverflow.asyncio, "sleep", fake_sleep)
    adapter = StackOverflowSourceToolAdapter("app-key", transport=httpx.MockTransport(handler))

    asyncio.run(adapter.fetch_candidates(["go"], ParsedJdModel()))

    assert all(request.url.params["key"] == "app-key" for request in seen)
    assert all(request.url.params["site"] == "stackoverflow" for request in seen)
    assert slept and slept[0] > 4
