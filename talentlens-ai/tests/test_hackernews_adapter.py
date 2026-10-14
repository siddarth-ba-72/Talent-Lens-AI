from __future__ import annotations

import asyncio

import httpx

from app.models.jd_models import ParsedJdModel
from app.services.sources.hackernews import HackerNewsSourceToolAdapter, deobfuscate_email, parse_post


# Made up; follows the thread's template as posts usually do.
TEMPLATE_POST = (
    "Location: Lisbon, Portugal<p>Remote: Yes<p>Willing to relocate: No<p>"
    "Technologies: Go, Kafka, Postgres, k8s<p>"
    "Résumé/CV: <a href=\"https:&#x2F;&#x2F;example.dev&#x2F;cv\">https:&#x2F;&#x2F;example.dev&#x2F;cv</a><p>"
    "Email: dev [at] example [dot] dev"
)


def test_template_post_is_parsed():
    post = parse_post(TEMPLATE_POST)

    assert post.fields["location"] == "Lisbon, Portugal"
    assert post.fields["remote"] == "Yes"
    assert post.fields["skills"] == "Go, Kafka, Postgres, k8s"
    assert post.fields["resume"] == "https://example.dev/cv"
    assert post.links == ["https://example.dev/cv"]


def test_email_deobfuscation():
    assert deobfuscate_email("dev [at] example [dot] dev") == "dev@example.dev"
    assert deobfuscate_email("dev at example dot dev") == "dev@example.dev"
    assert deobfuscate_email("plain@example.com (preferred)") == "plain@example.com"
    assert deobfuscate_email("ask me on the forum") is None


def _search(request: httpx.Request) -> httpx.Response:
    tags = request.url.params["tags"]
    if tags == "comment,story_100":
        return httpx.Response(200, json={"hits": [
            {"objectID": "101", "author": "lisbon-dev", "parent_id": 100, "story_id": 100,
             "created_at_i": 2000, "comment_text": TEMPLATE_POST},
            # A reply to someone's post, not a post of its own.
            {"objectID": "102", "author": "replier", "parent_id": 101, "story_id": 100,
             "created_at_i": 2001, "comment_text": "Great profile!"},
        ]})
    if tags == "comment,story_90":
        return httpx.Response(200, json={"hits": [
            {"objectID": "91", "author": "lisbon-dev", "parent_id": 90, "story_id": 90,
             "created_at_i": 1000, "comment_text": "Location: Porto<p>Technologies: Go"},
            {"objectID": "92", "author": "freeform", "parent_id": 90, "story_id": 90,
             "created_at_i": 1001, "comment_text": "I build Go and Kafka services, 7 years in fintech."},
        ]})
    return httpx.Response(200, json={"hits": []})


def test_adapter_returns_one_post_per_person(fake_http):
    transport = fake_http({
        "hn.algolia.com/api/v1/search_by_date": {"hits": [
            {"objectID": "100", "title": "Ask HN: Who wants to be hired? (October 2026)"},
            {"objectID": "99", "title": "Ask HN: Who is hiring? (October 2026)"},
            {"objectID": "90", "title": "Ask HN: Who wants to be hired? (September 2026)"},
        ]},
        "hn.algolia.com/api/v1/search": _search,
    })
    adapter = HackerNewsSourceToolAdapter(transport=transport)

    candidates = asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["Go"])))

    by_author = {candidate.source_username: candidate for candidate in candidates}
    assert set(by_author) == {"lisbon-dev", "freeform"}

    lisbon = by_author["lisbon-dev"]
    assert lisbon.profile_url == "https://news.ycombinator.com/item?id=101"  # the newest post
    assert lisbon.location == "Lisbon, Portugal"
    assert lisbon.email == "dev@example.dev"
    assert lisbon.skills[:4] == ["go", "kafka", "postgresql", "kubernetes"]
    assert lisbon.open_to_work is True
    assert lisbon.signals[0] == 'Posted in "Who wants to be hired?" (October 2026)'
    assert "Remote: Yes" in lisbon.signals

    freeform = by_author["freeform"]
    assert freeform.skills == ["go"]  # outside the template: the keywords it was found by
    assert freeform.experience == "7 years"
