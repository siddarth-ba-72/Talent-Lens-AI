from __future__ import annotations

import asyncio

from app.models.jd_models import ParsedJdModel
from app.services.sources.gitlab import GitLabSourceToolAdapter
from app.services.sources.openalex import OpenAlexSourceToolAdapter


GL = "gitlab.com/api/v4"


def test_gitlab_project_members(fake_http):
    transport = fake_http({
        f"{GL}/projects": [{
            "id": 1, "path_with_namespace": "carol/kafka-tool",
            "namespace": {"kind": "user", "path": "carol"},
        }],
        f"{GL}/projects/1/members/all": [
            {"id": 10, "username": "dave", "state": "active", "access_level": 40},
            {"id": 11, "username": "project_1_bot_ab12", "state": "active", "access_level": 40},
            {"id": 12, "username": "guest", "state": "active", "access_level": 10},
        ],
        f"{GL}/users": [{"id": 20, "username": "carol"}],
        f"{GL}/users/10": {
            "id": 10, "username": "dave", "name": "Dave", "state": "active", "job_title": "Senior Platform Engineer",
            "organization": "Acme", "public_email": "dave@example.com", "web_url": "https://gitlab.com/dave",
        },
        f"{GL}/users/20": {"id": 20, "username": "carol", "state": "active", "created_at": "2025-09-01T00:00:00Z"},
        f"{GL}/users/10/projects": [{"id": 5}],
        f"{GL}/users/20/projects": [],
        f"{GL}/projects/5/languages": {"Go": 80.0, "Shell": 20.0},
    })
    adapter = GitLabSourceToolAdapter("glpat-test", transport=transport)

    candidates = asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["Kafka"])))

    by_name = {candidate.source_username: candidate for candidate in candidates}
    # Bots and guests are skipped; the owner of a personal-namespace project is included.
    assert set(by_name) == {"dave", "carol"}
    dave = by_name["dave"]
    assert dave.experience == "Senior Platform Engineer"
    assert dave.email == "dave@example.com"
    assert dave.signals[0] == "Senior Platform Engineer at Acme"
    assert {"kafka", "go", "shell"} <= set(dave.skills)
    assert by_name["carol"].experience == "junior"
    assert all(request.headers["PRIVATE-TOKEN"] == "glpat-test" for request in transport.requests)
    assert transport.requests[0].url.params["topic"] == "kafka"


def test_gitlab_needs_a_token(fake_http):
    transport = fake_http({})

    assert asyncio.run(GitLabSourceToolAdapter(None, transport=transport).fetch_candidates([], ParsedJdModel())) == []
    assert transport.requests == []


def test_openalex_authors(fake_http):
    work = lambda title, cited, *authors: {  # noqa: E731
        "title": title, "publication_year": 2025, "cited_by_count": cited,
        "authorships": [{"author": {"id": f"https://openalex.org/{author}", "display_name": author}} for author in authors],
    }
    transport = fake_http({
        "api.openalex.org/works": {"results": [
            work("Stream processing with Kafka at scale", 30, "A1", "A2"),
            work("Exactly-once Kafka pipelines", 10, "A1"),
        ]},
        "api.openalex.org/authors": {"results": [{
            "id": "https://openalex.org/A1", "display_name": "Ada Researcher",
            "orcid": "https://orcid.org/0000-0000-0000-0001", "summary_stats": {"h_index": 12},
            "last_known_institutions": [{"display_name": "TU Delft", "country_code": "NL"}],
            "topics": [{"display_name": "Cloud Computing and Resource Management"}],
        }]},
    })
    adapter = OpenAlexSourceToolAdapter("oa-key", transport=transport)

    candidates = asyncio.run(adapter.fetch_candidates([], ParsedJdModel(technologies=["Kafka"])))

    # A1 matched two papers, A2 one.
    assert [candidate.source_username for candidate in candidates] == ["A1", "A2"]
    ada = candidates[0]
    assert ada.profile_url == "https://orcid.org/0000-0000-0000-0001"
    assert ada.location == "TU Delft, NL"
    assert ada.skills == ["kafka", "Cloud Computing and Resource Management"]
    assert "h-index 12" in ada.signals
    assert candidates[1].profile_url == "https://openalex.org/A2"
    assert all(request.url.params["api_key"] == "oa-key" for request in transport.requests)
