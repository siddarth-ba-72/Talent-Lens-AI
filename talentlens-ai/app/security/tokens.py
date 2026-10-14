"""JWT issuing/verification and the session binding that protects it.

A bearer token on its own is not enough to call the API. Every access and
refresh token is bound to the browser session it was issued to:

* at sign-in the server generates a random session fingerprint and hands it to
  the browser only as an HttpOnly cookie, so page scripts can never read it;
* the token carries ``fgp``: an HMAC of that fingerprint keyed with a salt
  derived from the user's id and their private ``token_salt``;
* a request is authorised only if the token is valid *and* the cookie hashes to
  the token's ``fgp`` under that user's salt.

A token lifted out of localStorage is therefore useless without the cookie, and
rotating a user's ``token_salt`` revokes every token they hold.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import Settings
from app.db.models import User
from app.errors import UnauthorizedError


ALGORITHM = "HS256"

TYPE_ACCESS = "ACCESS"
TYPE_REFRESH = "REFRESH"
TYPE_SIGNUP_TICKET = "SIGNUP_TICKET"

CLAIM_TYPE = "type"
CLAIM_ROLE = "role"
CLAIM_EMAIL = "email"
CLAIM_FINGERPRINT = "fgp"


def new_fingerprint() -> str:
    return secrets.token_urlsafe(32)


def _user_salt(settings: Settings, user: User) -> bytes:
    material = f"tl-session-v1:{user.id}:{user.token_salt}".encode("utf-8")
    return hmac.new(settings.jwt_secret.encode("utf-8"), material, hashlib.sha256).digest()


def fingerprint_hash(settings: Settings, user: User, fingerprint: str) -> str:
    return hmac.new(_user_salt(settings, user), fingerprint.encode("utf-8"), hashlib.sha256).hexdigest()


def fingerprint_matches(settings: Settings, user: User, fingerprint: str | None, claims: dict[str, Any]) -> bool:
    expected = claims.get(CLAIM_FINGERPRINT)
    if not fingerprint or not isinstance(expected, str):
        return False
    return hmac.compare_digest(fingerprint_hash(settings, user, fingerprint), expected)


def _encode(settings: Settings, claims: dict[str, Any], lifetime_ms: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {**claims, "iat": now, "exp": now + timedelta(milliseconds=lifetime_ms)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(settings: Settings, user: User, fingerprint: str) -> str:
    claims = {
        "sub": user.id,
        CLAIM_EMAIL: user.email,
        CLAIM_ROLE: user.role.value,
        CLAIM_TYPE: TYPE_ACCESS,
        CLAIM_FINGERPRINT: fingerprint_hash(settings, user, fingerprint),
    }
    return _encode(settings, claims, settings.jwt_access_expiry_ms)


def create_refresh_token(settings: Settings, user: User, fingerprint: str) -> str:
    claims = {
        "sub": user.id,
        CLAIM_TYPE: TYPE_REFRESH,
        CLAIM_FINGERPRINT: fingerprint_hash(settings, user, fingerprint),
    }
    return _encode(settings, claims, settings.jwt_refresh_expiry_ms)


def create_signup_ticket(settings: Settings, claims: dict[str, Any]) -> str:
    return _encode(settings, {**claims, CLAIM_TYPE: TYPE_SIGNUP_TICKET}, settings.jwt_signup_ticket_expiry_ms)


def decode_token(settings: Settings, token: str, expected_type: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid token") from exc

    if claims.get(CLAIM_TYPE) != expected_type:
        raise UnauthorizedError("Invalid token")
    return claims
