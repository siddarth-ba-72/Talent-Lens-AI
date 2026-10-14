from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import ShareRequest, User


def _is_id(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


class CreateShareRequestRequest(BaseModel):
    searchId: str
    recruiterUserId: str
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("searchId", "recruiterUserId")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        if not _is_id(value):
            raise ValueError("must be a valid id")
        return value

    @model_validator(mode="after")
    def _distinct_ids(self) -> "CreateShareRequestRequest":
        if self.searchId == self.recruiterUserId:
            raise ValueError("searchId and recruiterUserId cannot be the same value")
        return self


class ShareRequestResponse(BaseModel):
    id: str
    searchId: str
    requesterUserId: str
    ownerUserId: str
    status: str
    requestedAt: datetime
    resolvedAt: Optional[datetime]
    resolvedBy: Optional[str]
    note: Optional[str]
    # Display names, so clients do not have to resolve the ids themselves.
    searchTitle: Optional[str] = None
    requesterName: Optional[str] = None
    ownerName: Optional[str] = None

    @classmethod
    def from_request(
        cls,
        request: ShareRequest,
        *,
        search_title: Optional[str] = None,
        requester_name: Optional[str] = None,
        owner_name: Optional[str] = None,
    ) -> "ShareRequestResponse":
        return cls(
            id=request.id,
            searchId=request.search_id,
            requesterUserId=request.requester_user_id,
            ownerUserId=request.owner_user_id,
            status=request.status.value,
            requestedAt=request.requested_at,
            resolvedAt=request.resolved_at,
            resolvedBy=request.resolved_by,
            note=request.note,
            searchTitle=search_title,
            requesterName=requester_name,
            ownerName=owner_name,
        )


class RecruiterResponse(BaseModel):
    id: str
    name: str
    email: str

    @classmethod
    def from_user(cls, user: User) -> "RecruiterResponse":
        return cls(id=user.id, name=user.name, email=user.email)
