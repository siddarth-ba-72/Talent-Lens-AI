from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import User
from app.db.postgres import get_session
from app.models.auth_models import (
    AuthResponse,
    GoogleCallbackRequest,
    GoogleCallbackResponse,
    GoogleCompleteSignupRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserResponse,
)
from app.security import tokens
from app.security.auth import (
    clear_fingerprint_cookie,
    get_current_user,
    get_optional_user,
    load_bound_user,
    read_fingerprint,
    set_fingerprint_cookie,
)
from app.security.rate_limit import limit_auth_attempts
from app.services import auth_service
from app.services.google_oidc_service import GoogleOidcService


router = APIRouter(prefix="/api/auth", tags=["auth"])


@lru_cache
def get_google_oidc_service() -> GoogleOidcService:
    return GoogleOidcService(get_settings())


def _start_session(response: Response, settings: Settings, user: User, fingerprint: Optional[str] = None) -> AuthResponse:
    """Issue a token pair bound to a session fingerprint held in an HttpOnly cookie."""
    fingerprint = fingerprint or tokens.new_fingerprint()
    set_fingerprint_cookie(response, settings, fingerprint)
    return AuthResponse(
        accessToken=tokens.create_access_token(settings, user, fingerprint),
        refreshToken=tokens.create_refresh_token(settings, user, fingerprint),
        user=UserResponse.from_user(user),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_auth_attempts)],
)
async def register(
    request: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    # A new account is signed in straight away, so the UI need not ask for the password again.
    user = await auth_service.register(session, request)
    return _start_session(response, settings, user)


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(limit_auth_attempts)])
async def login(
    request: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    user = await auth_service.login(session, request)
    return _start_session(response, settings, user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    body: RefreshTokenRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    user = await load_bound_user(session, settings, request, body.refreshToken, tokens.TYPE_REFRESH)
    # Same browser session, so the fingerprint carries over; only the tokens rotate.
    return _start_session(response, settings, user, read_fingerprint(request, settings))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    response: Response,
    user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    # Signing out revokes every token the user holds, not just this browser's.
    if user is not None:
        await auth_service.revoke_sessions(session, user)
    clear_fingerprint_cookie(response, settings)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_user(user)


@router.post("/google/callback", response_model=GoogleCallbackResponse, dependencies=[Depends(limit_auth_attempts)])
async def google_callback(
    body: GoogleCallbackRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    oidc: GoogleOidcService = Depends(get_google_oidc_service),
) -> GoogleCallbackResponse:
    result = await auth_service.google_callback(
        session, settings, oidc, body.code, body.codeVerifier, body.nonce, body.redirectUri
    )
    if result.user is not None:
        return GoogleCallbackResponse(needsRoleSelection=False, auth=_start_session(response, settings, result.user))

    identity = result.identity
    return GoogleCallbackResponse(
        needsRoleSelection=True,
        signupTicket=result.signup_ticket,
        email=identity.email,
        name=identity.name,
        picture=identity.picture,
    )


@router.post(
    "/google/complete-signup", response_model=AuthResponse, dependencies=[Depends(limit_auth_attempts)]
)
async def google_complete_signup(
    body: GoogleCompleteSignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    user = await auth_service.google_complete_signup(session, settings, body.signupTicket, body.role)
    return _start_session(response, settings, user)
