from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import AuthProvider, Role, User, new_token_salt
from app.errors import DuplicateResourceError, OidcError, UnauthorizedError
from app.models.auth_models import LoginRequest, RegisterRequest
from app.security import tokens
from app.security.passwords import hash_password, verify_password
from app.services.google_oidc_service import GoogleIdentity, GoogleOidcService


@dataclass(frozen=True)
class GoogleCallbackResult:
    """Either a signed-in user, or a signup ticket awaiting role selection."""

    user: Optional[User] = None
    signup_ticket: Optional[str] = None
    identity: Optional[GoogleIdentity] = None


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _find_by_email(session: AsyncSession, email: str) -> Optional[User]:
    return await session.scalar(select(User).where(User.email == email))


async def _insert_user(session: AsyncSession, user: User) -> User:
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DuplicateResourceError(f"Email already registered: {user.email}") from exc
    return user


async def register(session: AsyncSession, request: RegisterRequest) -> User:
    email = _normalize_email(request.email)
    if await _find_by_email(session, email) is not None:
        raise DuplicateResourceError(f"Email already registered: {email}")

    user = User(
        email=email,
        password_hash=hash_password(request.password),
        name=request.name,
        role=request.resolve_role(),
        auth_providers=[AuthProvider.LOCAL.value],
        email_verified=False,
    )
    return await _insert_user(session, user)


async def login(session: AsyncSession, request: LoginRequest) -> User:
    user = await _find_by_email(session, _normalize_email(request.email))
    # Google-only users have no password; reject with the same generic error.
    if user is None or not user.password_hash or not verify_password(request.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")
    return user


async def revoke_sessions(session: AsyncSession, user: User) -> None:
    """Invalidate every token issued to the user by rotating their salt."""
    user.token_salt = new_token_salt()
    await session.commit()


async def google_callback(
    session: AsyncSession,
    settings: Settings,
    oidc: GoogleOidcService,
    code: str,
    code_verifier: str,
    nonce: str,
    redirect_uri: Optional[str] = None,
) -> GoogleCallbackResult:
    identity = await oidc.exchange_code_and_verify(code, code_verifier, nonce, redirect_uri)

    # 1. Existing Google-linked user
    by_google_id = await session.scalar(select(User).where(User.google_id == identity.google_sub))
    if by_google_id is not None:
        return GoogleCallbackResult(user=by_google_id)

    # 2. Auto-link by verified email
    existing = await _find_by_email(session, identity.email)
    if existing is not None:
        existing.google_id = identity.google_sub
        existing.auth_providers = sorted({*(existing.auth_providers or []), AuthProvider.GOOGLE.value})
        existing.email_verified = True
        if existing.avatar_url is None and identity.picture:
            existing.avatar_url = identity.picture
        await session.commit()
        return GoogleCallbackResult(user=existing)

    # 3. Brand-new user: issue signup ticket, await role selection
    ticket = tokens.create_signup_ticket(
        settings,
        {
            "googleSub": identity.google_sub,
            "email": identity.email,
            "name": identity.name or "",
            "picture": identity.picture or "",
        },
    )
    return GoogleCallbackResult(signup_ticket=ticket, identity=identity)


async def google_complete_signup(session: AsyncSession, settings: Settings, signup_ticket: str, role: Role) -> User:
    try:
        claims = tokens.decode_token(settings, signup_ticket, tokens.TYPE_SIGNUP_TICKET)
    except UnauthorizedError as exc:
        raise OidcError("signup_expired", "Signup ticket invalid or expired") from exc

    google_sub = claims.get("googleSub")
    email = claims.get("email")
    name = claims.get("name")
    picture = claims.get("picture")
    if not google_sub or not email:
        raise OidcError("signup_invalid", "Signup ticket missing required claims")

    # Race-guard: did someone register this email between callback and complete-signup?
    if await _find_by_email(session, email) is not None:
        raise DuplicateResourceError(f"Email already registered: {email}")

    user = User(
        email=email,
        password_hash=None,
        name=name if name and name.strip() else email,
        role=role,
        google_id=google_sub,
        auth_providers=[AuthProvider.GOOGLE.value],
        email_verified=True,
        avatar_url=picture if picture and picture.strip() else None,
    )
    return await _insert_user(session, user)
