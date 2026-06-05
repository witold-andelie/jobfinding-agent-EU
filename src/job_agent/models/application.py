"""Application model + lifecycle status (the Tracker's domain)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    new = "new"            # created, not yet sent
    applied = "applied"    # submitted by the user
    interview = "interview"
    offer = "offer"
    accepted = "accepted"  # terminal
    rejected = "rejected"  # terminal
    withdrawn = "withdrawn"  # terminal


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Application(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_source: str
    job_external_id: str
    job_title: str
    company: str
    candidate_ref: str  # opaque candidate identifier
    status: ApplicationStatus = ApplicationStatus.new
    cover_letter: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None
    history: list[dict[str, str]] = Field(default_factory=list)  # [{"status","at"}]
