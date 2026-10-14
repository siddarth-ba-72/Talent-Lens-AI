from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.documents import CandidateDocument
from app.db.postgres import normalize_database_url
from app.models.candidate_models import ScoreBreakdownModel, SourcePlatform
from app.security.passwords import hash_password, verify_password
from app.security.rate_limit import AttemptLimiter
from app.services import export_service
from app.services.candidate_service import CandidateFilterParams, build_filter
from app.services.search_service import like_pattern, normalize_id
from app.web import mount_ui


def test_password_hash_round_trip():
    hashed = hash_password("correct horse battery")

    assert hashed.startswith("$2b$12$")
    assert verify_password("correct horse battery", hashed)
    assert not verify_password("wrong", hashed)


def test_verifies_hashes_written_by_the_previous_spring_backend():
    # Spring's BCryptPasswordEncoder emits the $2a$ variant of the same algorithm.
    spring_style = hash_password("legacy-password").replace("$2b$", "$2a$", 1)

    assert verify_password("legacy-password", spring_style)


def test_malformed_hash_is_a_failed_login_not_a_crash():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_rate_limiter_blocks_after_the_allowed_attempts():
    limiter = AttemptLimiter()

    assert [limiter.is_limited("1.2.3.4", 3, 60) for _ in range(5)] == [False, False, False, True, True]
    assert not limiter.is_limited("5.6.7.8", 3, 60)


def test_rate_limiter_window_expires():
    limiter = AttemptLimiter()
    assert limiter.is_limited("1.2.3.4", 0, 60)

    assert not limiter.is_limited("1.2.3.4", 1, window_seconds=-1)


@pytest.mark.parametrize(
    "url, expected",
    [
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ],
)
def test_database_url_forms_are_normalised(url, expected):
    assert normalize_database_url(url) == expected


def test_non_postgres_database_url_is_refused():
    with pytest.raises(ValueError):
        normalize_database_url("mysql://u:p@host/db")


def test_ids_are_canonicalised_and_garbage_is_not_an_id():
    assert normalize_id("C4CD82E2-6324-4BC0-9DF8-FCB8B50B8E87") == "c4cd82e2-6324-4bc0-9df8-fcb8b50b8e87"
    assert normalize_id("'; DROP TABLE users; --") is None


def test_like_wildcards_in_keywords_are_literal():
    assert like_pattern("50%_off\\") == "%50\\%\\_off\\\\%"


def test_candidate_keyword_is_matched_literally():
    query = build_filter("search-1", CandidateFilterParams(keyword=".*"))

    assert {"$regex": "\\.\\*", "$options": "i"} in [c.get("name") for c in query["$and"][-1]["$or"]]


def test_candidates_are_limited_to_the_chosen_run():
    assert {"runId": "run_2"} in build_filter("search-1", CandidateFilterParams(run_id="run_2"))["$and"]
    assert not any("runId" in c for c in build_filter("search-1", CandidateFilterParams())["$and"])


def _candidate(**overrides) -> CandidateDocument:
    fields = dict(
        id=ObjectId("65f000000000000000000001"),
        searchId="search-1",
        runId="run_1",
        name="Ada Lovelace",
        email=None,
        profileUrl="https://github.com/ada",
        source=SourcePlatform.GITHUB,
        sourceUsername="ada",
        skills=["Python", "C"],
        location='London, "UK"',
        matchScore=88,
        scoreBreakdown=ScoreBreakdownModel(skillMatch=90, experienceMatch=85, overallFit=88),
        sourcedAt=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    # model_construct: build the document without a database connection.
    return CandidateDocument.model_construct(**fields)


def test_csv_export_layout():
    header, row = export_service.render("csv", [_candidate()]).decode().strip().split("\n")

    assert header == export_service.CSV_HEADER
    assert row == (
        '"65f000000000000000000001","Ada Lovelace",,"GITHUB","ada","https://github.com/ada",'
        '"Python|C","London, ""UK""",88,90,85,88,"run_1",2026-01-02T03:04:05Z'
    )


@pytest.mark.parametrize("payload", ["=HYPERLINK(\"http://evil\")", "+1+1", "-2+3", "@SUM(A1)"])
def test_csv_export_neutralises_spreadsheet_formulas(payload):
    row = export_service.render("csv", [_candidate(name=payload)]).decode().split("\n")[1]

    assert row.split(",")[1].startswith("\"'")


def test_export_format_validation():
    assert export_service.resolve_format("CSV") == "csv"
    for bad in (None, " ", "xml"):
        with pytest.raises(Exception):
            export_service.resolve_format(bad)


@pytest.fixture
def ui_client(tmp_path):
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html>shell</html>")
    (static / "favicon.svg").write_text("<svg/>")
    (static / "assets" / "app-abc123.js").write_text("console.log(1)")
    (tmp_path / "secret.env").write_text("JWT_SECRET=do-not-serve")

    # Docs off, as in production: /docs must then be a 404, not the UI shell.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    assert mount_ui(app, static)
    return TestClient(app)


def test_client_side_routes_get_the_shell_with_a_csp(ui_client):
    response = ui_client.get("/searches/123")

    assert response.text == "<html>shell</html>"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-cache"


def test_hashed_assets_are_cached_and_missing_ones_are_not_the_shell(ui_client):
    assert "immutable" in ui_client.get("/assets/app-abc123.js").headers["cache-control"]
    assert ui_client.get("/assets/missing.js").status_code == 404


@pytest.mark.parametrize("path", ["/api/unknown", "/ai/unknown", "/docs"])
def test_api_paths_are_never_answered_with_the_shell(ui_client, path):
    assert ui_client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/../secret.env", "/%2e%2e/secret.env", "/..%2fsecret.env", "/assets/../../secret.env"])
def test_files_outside_the_build_are_not_served(ui_client, path):
    assert "do-not-serve" not in ui_client.get(path).text


def test_ui_is_skipped_when_no_build_exists(tmp_path):
    assert mount_ui(FastAPI(), tmp_path / "nope") is False
