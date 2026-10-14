from __future__ import annotations

import re
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, Field, field_validator, model_validator

from app.db.models import Role, User


_ROLE_BY_INDEX = {1: Role.RECRUITER, 2: Role.HIRING_MANAGER}


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+$")
_EMAIL_MAX_CHARS = 320


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


def _well_formed_email(value: str) -> str:
    value = value.strip()
    if len(value) > _EMAIL_MAX_CHARS or not _EMAIL_PATTERN.match(value):
        raise ValueError("must be a well-formed email address")
    return value


# Shape check only. Stricter validators reject internal mail domains (.local, .test, ...).
Email = Annotated[str, AfterValidator(_well_formed_email)]


class RegisterRequest(BaseModel):
    name: str = Field(max_length=100)
    email: Email
    password: str = Field(min_length=8, max_length=100)
    role: Optional[Role] = None
    roleIndex: Optional[int] = Field(default=None, ge=1, le=2)

    _name_not_blank = field_validator("name")(_not_blank)

    @model_validator(mode="after")
    def _require_role_selection(self) -> "RegisterRequest":
        if self.role is None and self.roleIndex is None:
            raise ValueError("Either role or roleIndex must be provided")
        return self

    def resolve_role(self) -> Role:
        return self.role if self.role is not None else _ROLE_BY_INDEX[self.roleIndex]


class LoginRequest(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=100)


class RefreshTokenRequest(BaseModel):
    refreshToken: str

    _token_not_blank = field_validator("refreshToken")(_not_blank)


class GoogleCallbackRequest(BaseModel):
    code: str
    codeVerifier: str
    nonce: str

    _fields_not_blank = field_validator("code", "codeVerifier", "nonce")(_not_blank)


class GoogleCompleteSignupRequest(BaseModel):
    signupTicket: str
    role: Role

    _ticket_not_blank = field_validator("signupTicket")(_not_blank)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(id=user.id, name=user.name, email=user.email, role=user.role.value)


class AuthResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserResponse


class GoogleCallbackResponse(BaseModel):
    """Discriminated response for /api/auth/google/callback.

    A known Google user (existing googleId, or auto-linked by verified email) gets
    ``needsRoleSelection=False`` with ``auth`` populated. An unknown one gets
    ``needsRoleSelection=True`` with the signup ticket and profile fields.
    """

    needsRoleSelection: bool
    auth: Optional[AuthResponse] = None
    signupTicket: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
