from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import Role, User
from app.db.postgres import get_session
from app.errors import ForbiddenError, UnauthorizedError
from app.security import tokens


_bearer = HTTPBearer(auto_error=False, description="Access token from /api/auth/login")


def fingerprint_cookie_name(settings: Settings) -> str:
    # The __Host- prefix makes browsers refuse the cookie unless it is Secure,
    # host-only and Path=/, so it cannot be planted from a sibling subdomain.
    return "__Host-tl_fgp" if settings.use_secure_cookies else "tl_fgp"


def set_fingerprint_cookie(response: Response, settings: Settings, fingerprint: str) -> None:
    response.set_cookie(
        key=fingerprint_cookie_name(settings),
        value=fingerprint,
        max_age=settings.jwt_refresh_expiry_ms // 1000,
        path="/",
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite="strict",
    )


def clear_fingerprint_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=fingerprint_cookie_name(settings),
        path="/",
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite="strict",
    )


def read_fingerprint(request: Request, settings: Settings) -> Optional[str]:
    return request.cookies.get(fingerprint_cookie_name(settings))


async def load_bound_user(
    session: AsyncSession,
    settings: Settings,
    request: Request,
    token: str,
    expected_type: str,
) -> User:
    """Resolve the user a token belongs to, enforcing the session binding."""
    claims = tokens.decode_token(settings, token, expected_type)

    subject = claims.get("sub")
    try:
        user_id = str(uuid.UUID(str(subject)))
    except ValueError as exc:
        raise UnauthorizedError("Invalid token") from exc

    user = await session.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Invalid token")
    if not tokens.fingerprint_matches(settings, user, read_fingerprint(request, settings), claims):
        raise UnauthorizedError("Invalid token")
    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        return await load_bound_user(session, settings, request, credentials.credentials, tokens.TYPE_ACCESS)
    except UnauthorizedError:
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Authentication required")
    return await load_bound_user(session, settings, request, credentials.credentials, tokens.TYPE_ACCESS)


def require_role(*roles: Role):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError("Access denied")
        return user

    return dependency


require_recruiter = require_role(Role.RECRUITER)
require_hiring_manager = require_role(Role.HIRING_MANAGER)
