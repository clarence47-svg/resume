from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class BlockerStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class BlockerRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    application_id: str
    code: str
    message: str
    next_action: str = ""
    status: BlockerStatus = BlockerStatus.OPEN
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FollowUpEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    application_id: str
    event_type: str
    title: str
    scheduled_at: datetime
    notes: str = ""
    completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TrackingDashboard(BaseModel):
    total_jobs: int = 0
    recommended_jobs: int = 0
    awaiting_confirmation: int = 0
    submitted: int = 0
    interviews: int = 0
    offers: int = 0
    rejected: int = 0
    blocked: int = 0
    recent_jobs: list[dict] = Field(default_factory=list)
    open_blockers: list[BlockerRecord] = Field(default_factory=list)
    upcoming_follow_ups: list[FollowUpEvent] = Field(default_factory=list)
