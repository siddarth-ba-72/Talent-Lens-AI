from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.jd_models import ParsedJdModel


class SourcePlatform(str, Enum):
    GITHUB = "GITHUB"
    STACKOVERFLOW = "STACKOVERFLOW"
    HACKERNEWS = "HACKERNEWS"
    DEVTO = "DEVTO"
    HUGGINGFACE = "HUGGINGFACE"
    NPM = "NPM"
    CRATES = "CRATES"
    GITLAB = "GITLAB"
    OPENALEX = "OPENALEX"
    # No longer offered (they never sourced anyone); kept so stored data still loads.
    LEETCODE = "LEETCODE"
    PEOPLES_DATA = "PEOPLES_DATA"
    OTHER = "OTHER"


class ScoreBreakdownModel(BaseModel):
    skillMatch: int = Field(ge=0, le=100)
    experienceMatch: int = Field(ge=0, le=100)
    overallFit: int = Field(ge=0, le=100)


class RankedCandidateModel(BaseModel):
    name: str
    email: Optional[str] = None
    avatarUrl: Optional[str] = None
    profileUrl: str
    source: SourcePlatform
    sourceUsername: str
    skills: list[str] = Field(default_factory=list)
    bio: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    # Short reasons the candidate was picked, e.g. "Top answerer in [go]".
    signals: list[str] = Field(default_factory=list)
    # The candidate says they are looking (GitHub "hireable", an HN "Who wants to be hired?" post).
    openToWork: bool = False
    matchScore: int = Field(ge=0, le=100)
    scoreBreakdown: ScoreBreakdownModel
    sourcedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidateResponse(BaseModel):
    id: str
    searchId: str
    runId: str
    name: str
    email: Optional[str]
    avatarUrl: Optional[str]
    profileUrl: str
    source: str
    sourceUsername: str
    skills: list[str]
    bio: Optional[str]
    location: Optional[str]
    signals: list[str]
    openToWork: bool
    matchScore: int
    scoreBreakdown: ScoreBreakdownModel
    sourcedAt: datetime


class SourcingRequestPayloadModel(BaseModel):
    taskId: str
    searchId: str
    runId: str
    parsedJd: ParsedJdModel
    platforms: list[SourcePlatform]
    timestamp: datetime


class SourcingStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SourcingResultPayloadModel(BaseModel):
    taskId: str
    searchId: str
    runId: str
    status: SourcingStatus
    candidatesFound: int = 0
    candidates: list[RankedCandidateModel] = Field(default_factory=list)
    error: Optional[str] = None
    completedAt: datetime

    @model_validator(mode="after")
    def _enforce_count_and_top_cap(self) -> "SourcingResultPayloadModel":
        limited = self.candidates[:20]
        self.candidates = limited
        self.candidatesFound = len(limited)
        return self
