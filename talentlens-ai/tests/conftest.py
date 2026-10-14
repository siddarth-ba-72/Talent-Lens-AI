from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.db.models import Role, User, new_id, new_token_salt


@pytest.fixture
def settings() -> Settings:
    # Explicit values so the suite never depends on, or reads, a developer's .env.
    return Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="postgresql://user:pass@localhost:5432/test",
        MONGODB_URI="mongodb://localhost:27017",
        JWT_SECRET="unit-test-secret-that-is-long-enough-0123456789",
    )


@pytest.fixture
def make_user():
    def _make(role: Role = Role.RECRUITER) -> User:
        user_id = new_id()
        return User(
            id=user_id,
            email=f"{user_id}@example.com",
            name="Test User",
            role=role,
            token_salt=new_token_salt(),
        )

    return _make


@pytest.fixture
def fake_http():
    """An httpx transport answering from a route table, recording each request.

    `routes` maps "host/path" to a JSON body, a (status, body) pair, or a
    function taking the request and returning an httpx.Response.
    """

    def _make(routes: dict):
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            answer = routes.get(f"{request.url.host}{request.url.path}")
            if answer is None:
                return httpx.Response(404, json={"message": "no route"})
            if callable(answer):
                return answer(request)
            status, body = answer if isinstance(answer, tuple) else (200, answer)
            return httpx.Response(status, json=body)

        transport = httpx.MockTransport(handler)
        transport.requests = requests
        return transport

    return _make
