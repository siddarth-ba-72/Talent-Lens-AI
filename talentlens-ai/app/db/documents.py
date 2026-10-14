from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.models.candidate_models import ScoreBreakdownModel, SourcePlatform


class CandidateDocument(Document):
    """A profile sourced from an external platform, scored against one search run."""

    searchId: str
    runId: str
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
    matchScore: int
    scoreBreakdown: ScoreBreakdownModel
    isActive: bool = True
    sourcedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "candidates"
        indexes = [
            # A profile appears at most once per run; re-runs are separate snapshots.
            IndexModel(
                [("searchId", ASCENDING), ("runId", ASCENDING), ("source", ASCENDING), ("sourceUsername", ASCENDING)],
                unique=True,
            ),
            IndexModel([("searchId", ASCENDING), ("isActive", ASCENDING), ("matchScore", DESCENDING)]),
        ]
