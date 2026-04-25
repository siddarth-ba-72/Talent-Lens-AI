from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.jd_models import ParsedJdModel


class SourcePlatform(str, Enum):
    GITHUB = "GITHUB"
    STACKOVERFLOW = "STACKOVERFLOW"
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
    matchScore: int = Field(ge=0, le=100)
    scoreBreakdown: ScoreBreakdownModel
    sourcedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
