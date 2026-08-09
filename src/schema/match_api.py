from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from matching.models import CopyUnitUpdate, JDMatchResult, MatchVersionSource


class MatchTaskStatus(StrEnum):
    QUEUED = "queued"
    ANALYZING_JD = "analyzing_jd"
    MATCHING = "matching"
    GENERATING = "generating"
    AUDITING = "auditing"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    FAILED_RETRYABLE = "failed_retryable"


class MatchCreateRequest(BaseModel):
    profile_task_id: str
    jd_text: str
    title: str = ""


class MatchTaskCreated(BaseModel):
    match_id: str
    status: MatchTaskStatus


class MatchTaskSummary(BaseModel):
    id: str
    profile_task_id: str
    job_id: str | None = None
    batch_id: str | None = None
    title: str
    status: MatchTaskStatus
    stage: str
    progress: int = Field(ge=0, le=100)
    current_version: int | None = None
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class MatchTaskDetail(MatchTaskSummary):
    jd_text: str
    role_title: str | None = None


class MatchResultResponse(BaseModel):
    result: JDMatchResult


class MatchVersionSummary(BaseModel):
    version: int
    source: MatchVersionSource
    created_at: datetime


class DraftUpdateRequest(BaseModel):
    expected_version: int = Field(ge=1)
    updates: list[CopyUnitUpdate] = Field(min_length=1)


class MatchDeleteResponse(BaseModel):
    status: str = "deleted"
