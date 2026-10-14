from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.db.models import Search, SourcingTask
from app.models.jd_models import ParsedJdModel


MAX_JD_TEXT_CHARS = 50_000


class CreateSearchRequest(BaseModel):
    jdText: Optional[str] = Field(default=None, max_length=MAX_JD_TEXT_CHARS)


class SourcingRequest(BaseModel):
    platforms: list[str] = Field(default_factory=list)
    # Let the server pick the platforms that suit the JD (ignores `platforms`).
    auto: bool = False

    @model_validator(mode="after")
    def _require_platforms(self) -> "SourcingRequest":
        if not self.auto and not self.platforms:
            raise ValueError("Select at least one platform, or set auto")
        return self


class PlatformAvailabilityResponse(BaseModel):
    platform: str
    # False when a credential the platform needs is not configured on the server.
    available: bool


class SearchResponse(BaseModel):
    id: str
    title: str
    rawJdText: Optional[str]
    jdFileName: Optional[str]
    parsedJd: ParsedJdModel
    sourcingStatus: str
    sourcingPlatforms: list[str]
    candidateCount: int
    sharedWith: list[str]
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def from_search(cls, search: Search) -> "SearchResponse":
        return cls(
            id=search.id,
            title=search.title,
            rawJdText=search.raw_jd_text,
            jdFileName=search.jd_file_name,
            parsedJd=ParsedJdModel.model_validate(search.parsed_jd),
            sourcingStatus=search.sourcing_status.value,
            sourcingPlatforms=list(search.sourcing_platforms or []),
            candidateCount=search.candidate_count,
            sharedWith=search.shared_with,
            createdAt=search.created_at,
            updatedAt=search.updated_at,
        )


class SearchSummaryResponse(BaseModel):
    id: str
    title: str
    sourcingStatus: str
    sourcingPlatforms: list[str]
    candidateCount: int
    createdAt: datetime
    # Only filled in for searches the caller can already open; the picker a hiring
    # manager uses to request access must not leak JD contents.
    parsedJd: Optional[ParsedJdModel] = None

    @classmethod
    def from_search(cls, search: Search, *, include_parsed_jd: bool = False) -> "SearchSummaryResponse":
        return cls(
            id=search.id,
            title=search.title,
            sourcingStatus=search.sourcing_status.value,
            sourcingPlatforms=list(search.sourcing_platforms or []),
            candidateCount=search.candidate_count,
            createdAt=search.created_at,
            parsedJd=ParsedJdModel.model_validate(search.parsed_jd) if include_parsed_jd else None,
        )


class SourcingStatusResponse(BaseModel):
    taskId: str
    searchId: str
    runId: str
    status: str
    candidatesFound: int
    error: Optional[str]
    startedAt: datetime
    completedAt: Optional[datetime]

    @classmethod
    def from_task(cls, task: SourcingTask) -> "SourcingStatusResponse":
        return cls(
            taskId=task.id,
            searchId=task.search_id,
            runId=task.run_id,
            status=task.status.value,
            candidatesFound=task.candidates_found,
            error=task.error,
            startedAt=task.started_at,
            completedAt=task.completed_at,
        )
