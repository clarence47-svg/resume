from datetime import datetime
from enum import StrEnum
from profile.models import ConflictRecord, ProfileFact, ProfileResult

from pydantic import BaseModel, Field


class ReviewMode(StrEnum):
    AUTO = "auto"
    PAUSE = "pause"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    AWAITING_REVIEW = "awaiting_review"
    GENERATING = "generating"
    AUDITING = "auditing"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    FAILED_RETRYABLE = "failed_retryable"


class DocumentStatus(StrEnum):
    STORED = "stored"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class TaskCreated(BaseModel):
    task_id: str
    status: TaskStatus


class DocumentSummary(BaseModel):
    id: str
    original_name: str
    extension: str
    size_bytes: int
    status: DocumentStatus
    error: str | None = None


class TaskSummary(BaseModel):
    id: str
    title: str
    status: TaskStatus
    stage: str
    progress: int = Field(ge=0, le=100)
    review_mode: ReviewMode
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class TaskDetail(TaskSummary):
    documents: list[DocumentSummary] = Field(default_factory=list)
    conflicts: list[ConflictRecord] = Field(default_factory=list)


class FactsResponse(BaseModel):
    task_id: str
    facts: list[ProfileFact]
    conflicts: list[ConflictRecord]


class FactsUpdateRequest(BaseModel):
    facts: list[ProfileFact]


class ResultResponse(BaseModel):
    result: ProfileResult


class DeleteResponse(BaseModel):
    status: str = "deleted"
