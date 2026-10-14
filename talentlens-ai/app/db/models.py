from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


class Role(str, Enum):
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"


class AuthProvider(str, Enum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"


class SourcingStatus(str, Enum):
    IDLE = "IDLE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ShareRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


def new_token_salt() -> str:
    return secrets.token_hex(32)


def _enum(enum_cls: type[Enum]) -> SqlEnum:
    return SqlEnum(enum_cls, native_enum=False, length=32)


_ID = Uuid(as_uuid=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(_ID, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    # Null for Google-only accounts.
    password_hash: Mapped[Optional[str]] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(_enum(Role), index=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    auth_providers: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    # Per-user secret that keys the session binding of every token issued to this
    # user. Never leaves the server; rotating it revokes all of the user's tokens.
    token_salt: Mapped[str] = mapped_column(String(64), default=new_token_salt)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Search(Base):
    __tablename__ = "searches"
    __table_args__ = (Index("ix_searches_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(_ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(_ID, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300))
    raw_jd_text: Mapped[Optional[str]] = mapped_column(Text)
    jd_file_name: Mapped[Optional[str]] = mapped_column(String(255))
    parsed_jd: Mapped[dict[str, Any]] = mapped_column(JSONB)
    sourcing_status: Mapped[SourcingStatus] = mapped_column(_enum(SourcingStatus), default=SourcingStatus.IDLE)
    sourcing_platforms: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    shares: Mapped[list[SearchShare]] = relationship(
        back_populates="search", cascade="all, delete-orphan", passive_deletes=True, lazy="selectin"
    )

    @property
    def shared_with(self) -> list[str]:
        return [share.user_id for share in self.shares]


class SearchShare(Base):
    """A hiring manager who has been granted read access to a search."""

    __tablename__ = "search_shares"

    search_id: Mapped[str] = mapped_column(_ID, ForeignKey("searches.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(_ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    search: Mapped[Search] = relationship(back_populates="shares")


class SourcingTask(Base):
    __tablename__ = "sourcing_tasks"

    id: Mapped[str] = mapped_column(_ID, primary_key=True, default=new_id)
    search_id: Mapped[str] = mapped_column(_ID, ForeignKey("searches.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str] = mapped_column(String(64))
    platforms: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    status: Mapped[TaskStatus] = mapped_column(_enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    candidates_found: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ShareRequest(Base):
    __tablename__ = "share_requests"
    __table_args__ = (
        Index("ix_share_requests_owner_status_requested", "owner_user_id", "status", "requested_at"),
        Index("ix_share_requests_requester_requested", "requester_user_id", "requested_at"),
        Index("ix_share_requests_search_requester_status", "search_id", "requester_user_id", "status"),
    )

    id: Mapped[str] = mapped_column(_ID, primary_key=True, default=new_id)
    search_id: Mapped[str] = mapped_column(_ID, ForeignKey("searches.id", ondelete="CASCADE"))
    requester_user_id: Mapped[str] = mapped_column(_ID, ForeignKey("users.id", ondelete="CASCADE"))
    owner_user_id: Mapped[str] = mapped_column(_ID, ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[ShareRequestStatus] = mapped_column(_enum(ShareRequestStatus), default=ShareRequestStatus.PENDING)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(_ID, ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[Optional[str]] = mapped_column(String(500))
