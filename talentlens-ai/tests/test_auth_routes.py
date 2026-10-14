from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import auth as auth_api
from app.config import get_settings
from app.db.models import Role
from app.db.postgres import get_session
from app.security import tokens
from app.security.auth import fingerprint_cookie_name
from app.security.rate_limit import auth_limiter
from app.services import auth_service


@pytest.fixture
def auth_client(settings):
    app = FastAPI()
    app.include_router(auth_api.router)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = lambda: None
    auth_limiter.reset()
    return TestClient(app)


def test_registering_signs_the_new_account_in(auth_client, settings, make_user, monkeypatch):
    user = make_user(Role.HIRING_MANAGER)

    async def fake_register(session, request):
        return user

    monkeypatch.setattr(auth_service, "register", fake_register)

    response = auth_client.post(
        "/api/auth/register",
        json={"name": user.name, "email": user.email, "password": "long-enough-password", "role": "HIRING_MANAGER"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"] == {"id": user.id, "name": user.name, "email": user.email, "role": "HIRING_MANAGER"}
    assert set(body) == {"accessToken", "refreshToken", "user"}

    # The tokens are usable as issued: they are bound to the session cookie set alongside them.
    fingerprint = response.cookies[fingerprint_cookie_name(settings)]
    assert "httponly" in response.headers["set-cookie"].lower()
    for token, token_type in ((body["accessToken"], tokens.TYPE_ACCESS), (body["refreshToken"], tokens.TYPE_REFRESH)):
        claims = tokens.decode_token(settings, token, token_type)
        assert claims["sub"] == user.id
        assert tokens.fingerprint_matches(settings, user, fingerprint, claims)
