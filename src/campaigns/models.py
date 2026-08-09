from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from career.models import ApplicationStrategy


class CampaignStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class BatchStatus(StrEnum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    AWAITING_REVIEW = "awaiting_review"
    GENERATING = "generating"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED_RETRYABLE = "failed_retryable"
    CANCELLED = "cancelled"


class JobCampaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    profile_task_id: str
    title: str = Field(min_length=1, max_length=255)
    strategy: ApplicationStrategy = ApplicationStrategy.VOLUME
    search_keywords: list[str] = Field(default_factory=list)
    target_cities: list[str] = Field(default_factory=list)
    source_platforms: list[str] = Field(default_factory=lambda: ["manual"])
    status: CampaignStatus = CampaignStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AggregateGap(BaseModel):
    key: str
    text: str
    job_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    priority: int = Field(default=1, ge=1, le=3)
    current_coverage: float = Field(default=0, ge=0, le=1)


class TailoringBatch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    profile_task_id: str
    title: str
    job_ids: list[str] = Field(min_length=1, max_length=20)
    match_ids: dict[str, str] = Field(default_factory=dict)
    aggregate_gaps: list[AggregateGap] = Field(default_factory=list)
    status: BatchStatus = BatchStatus.QUEUED
    stage: str = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
