from __future__ import annotations

import asyncio
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import Settings
from app.errors import OidcError


logger = logging.getLogger(__name__)

MAX_TOKEN_AGE_SECONDS = 600
_CLOCK_SKEW_SECONDS = 60


@dataclass(frozen=True)
class GoogleIdentity:
    google_sub: str
    email: str
    name: Optional[str]
    picture: Optional[str]


class GoogleOidcService:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def exchange_code_and_verify(
        self, code: str, code_verifier: str, expected_nonce: str, redirect_uri: Optional[str] = None
    ) -> GoogleIdentity:
        """`redirect_uri` is the one the browser sent Google to; Google only accepts the
        exchange with that same URI. It must be one of GOOGLE_REDIRECT_URI."""
        settings = self._settings
        allowed = settings.google_redirect_uris
        if not (settings.google_client_id and settings.google_client_secret and allowed):
            raise OidcError("google_not_configured", "Google sign-in is not configured on this server")
        if redirect_uri is None:
            redirect_uri = allowed[0]
        elif redirect_uri not in allowed:
            logger.warning("Google sign-in from unlisted redirect URI %s (allowed: %s)", redirect_uri, allowed)
            raise OidcError(
                "redirect_uri_not_allowed",
                f"Sign-in came back to {redirect_uri}, which is not in GOOGLE_REDIRECT_URI on this server",
            )

        raw_id_token = await self._exchange_code_for_id_token(code, code_verifier, redirect_uri)
        return await self._verify_id_token(raw_id_token, expected_nonce)

    async def _exchange_code_for_id_token(self, code: str, code_verifier: str, redirect_uri: str) -> str:
        settings = self._settings
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(settings.google_token_endpoint, data=form)
        except httpx.HTTPError as exc:
            logger.warning("Unexpected error during Google code exchange: %s", exc)
            raise OidcError("google_exchange_failed", "Failed to exchange code with Google") from exc

        if response.status_code >= 400:
            reason = _describe_token_error(response)
            logger.warning("Google token endpoint returned %s: %s", response.status_code, reason)
            raise OidcError(
                "google_exchange_failed",
                f"Google rejected the code exchange ({response.status_code}): {reason}",
            )

        raw_id_token = _json_object(response).get("id_token")
        if not isinstance(raw_id_token, str) or not raw_id_token:
            raise OidcError("google_exchange_failed", "No id_token in Google response")
        return raw_id_token

    async def _verify_id_token(self, raw_id_token: str, expected_nonce: str) -> GoogleIdentity:
        settings = self._settings
        try:
            # Checks the signature against Google's rotating keys, plus audience,
            # issuer and expiry.
            payload = await asyncio.to_thread(
                google_id_token.verify_oauth2_token,
                raw_id_token,
                google_requests.Request(),
                settings.google_client_id,
                clock_skew_in_seconds=_CLOCK_SKEW_SECONDS,
            )
        except Exception as exc:
            logger.warning("Google ID token verification failed: %s", exc)
            raise OidcError(
                "id_token_invalid", "ID token signature, issuer, audience, or expiry invalid"
            ) from exc

        authorized_party = payload.get("azp")
        if authorized_party is not None and authorized_party != settings.google_client_id:
            raise OidcError("id_token_invalid", "Authorized party (azp) does not match client id")

        issued_at = payload.get("iat")
        now = int(time.time())
        if (
            not isinstance(issued_at, (int, float))
            or issued_at < now - MAX_TOKEN_AGE_SECONDS
            or issued_at > now + _CLOCK_SKEW_SECONDS
        ):
            raise OidcError("id_token_invalid", "ID token iat outside acceptable window")

        token_nonce = payload.get("nonce")
        if not isinstance(token_nonce, str) or not hmac.compare_digest(token_nonce, expected_nonce):
            raise OidcError("nonce_mismatch", "ID token nonce does not match")

        if payload.get("email_verified") is not True:
            raise OidcError("email_not_verified", "Google email is not verified")

        email = payload.get("email")
        subject = payload.get("sub")
        if not email or not subject:
            raise OidcError("id_token_invalid", "ID token missing email or subject")

        return GoogleIdentity(
            google_sub=str(subject),
            email=str(email).lower(),
            name=payload.get("name"),
            picture=payload.get("picture"),
        )


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _describe_token_error(response: httpx.Response) -> str:
    body = _json_object(response)
    parts = [str(body[key]) for key in ("error", "error_description") if body.get(key)]
    return ": ".join(parts) or "no details"
