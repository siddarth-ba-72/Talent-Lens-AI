from __future__ import annotations

import asyncio

import pytest

from app.errors import OidcError
from app.services.google_oidc_service import GoogleIdentity, GoogleOidcService


API_ORIGIN = "http://localhost:9000/oauth/google/callback"
DEV_SERVER = "http://localhost:5173/oauth/google/callback"


@pytest.fixture
def google_settings(settings):
    return settings.model_copy(update={
        "google_client_id": "client-id",
        "google_client_secret": "client-secret",
        "google_redirect_uri": f"{API_ORIGIN}, {DEV_SERVER}",
    })


def _service(google_settings, monkeypatch) -> tuple[GoogleOidcService, list[str]]:
    service = GoogleOidcService(google_settings)
    used: list[str] = []

    async def fake_exchange(code, code_verifier, redirect_uri):
        used.append(redirect_uri)
        return "id-token"

    async def fake_verify(raw_id_token, expected_nonce):
        return GoogleIdentity(google_sub="sub", email="a@example.com", name=None, picture=None)

    monkeypatch.setattr(service, "_exchange_code_for_id_token", fake_exchange)
    monkeypatch.setattr(service, "_verify_id_token", fake_verify)
    return service, used


def test_redirect_uri_setting_takes_a_list(google_settings):
    assert google_settings.google_redirect_uris == [API_ORIGIN, DEV_SERVER]


def test_exchange_uses_the_redirect_uri_the_browser_used(google_settings, monkeypatch):
    service, used = _service(google_settings, monkeypatch)

    asyncio.run(service.exchange_code_and_verify("code", "verifier", "nonce", DEV_SERVER))

    # Google rejects the exchange unless it names the same URI as the authorize request.
    assert used == [DEV_SERVER]


def test_without_a_redirect_uri_the_first_configured_one_is_used(google_settings, monkeypatch):
    service, used = _service(google_settings, monkeypatch)

    asyncio.run(service.exchange_code_and_verify("code", "verifier", "nonce"))

    assert used == [API_ORIGIN]


def test_unlisted_redirect_uri_is_refused_before_calling_google(google_settings, monkeypatch):
    service, used = _service(google_settings, monkeypatch)

    with pytest.raises(OidcError) as raised:
        asyncio.run(service.exchange_code_and_verify("code", "verifier", "nonce", "https://evil.example/cb"))

    assert raised.value.oidc_code == "redirect_uri_not_allowed"
    assert "GOOGLE_REDIRECT_URI" in str(raised.value)
    assert used == []
