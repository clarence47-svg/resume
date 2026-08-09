from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from job_search.models import JobPlatform


class ApplicationStatus(StrEnum):
    QUEUED = "queued"
    CONNECTING = "connecting"
    OPENING = "opening"
    FILLING = "filling"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    NEEDS_USER = "needs_user"
    BLOCKED = "blocked"
    FAILED_RETRYABLE = "failed_retryable"
    CANCELLED = "cancelled"


class ApplicationField(BaseModel):
    key: str
    label: str
    value: str
    source: str
    sensitive: bool = False
    confirmed: bool = False


class ApplicationPreview(BaseModel):
    job_id: str
    company: str
    title: str
    platform: JobPlatform
    job_url: str
    resume_version_id: str
    resume_filename: str
    selected_experiences: list[str] = Field(default_factory=list)
    fields: list[ApplicationField] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    submit_label: str = "提交申请"
    action_kind: str = "application_submit"
    message_preview: str = ""
    delivery_note: str = ""
    preview_hash: str = ""


class BrowserConnectionStatus(BaseModel):
    enabled: bool = False
    connected: bool = False
    cdp_url: str = ""
    browser_version: str = ""
    boss_page_open: bool = False
    boss_logged_in: bool = False
    boss_page_url: str = ""
    blockers: list[str] = Field(default_factory=list)
    message: str = ""


class ApplicationEvidence(BaseModel):
    confirmation_text: str = ""
    confirmation_url: str = ""
    application_reference: str = ""
    screenshot_path: str = ""
    submitted_at: datetime | None = None


class ApplicationAttempt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    resume_version_id: str
    status: ApplicationStatus = ApplicationStatus.QUEUED
    stage: str = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    platform: JobPlatform = JobPlatform.GENERIC
    preview: ApplicationPreview | None = None
    evidence: ApplicationEvidence | None = None
    blocker_code: str = ""
    error: str | None = None
    graph_thread_id: str = ""
    attempt: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
