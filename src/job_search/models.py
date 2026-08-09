from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class JobPlatform(StrEnum):
    BOSS = "boss"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    OFFICIAL = "official"
    GENERIC = "generic"
    MANUAL = "manual"


class JobStatus(StrEnum):
    DISCOVERED = "discovered"
    FILTERED = "filtered"
    EVALUATED = "evaluated"
    SHORTLISTED = "shortlisted"
    TAILORING = "tailoring"
    READY = "ready"
    APPLYING = "applying"
    SUBMITTED = "submitted"
    NEEDS_USER = "needs_user"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    OFFER = "offer"
    CLOSED = "closed"


class JobDecision(StrEnum):
    RECOMMENDED = "recommended"
    REVIEW = "review"
    NOT_RECOMMENDED = "not_recommended"
    NEEDS_USER = "needs_user"


class JobPosting(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    profile_task_id: str
    platform: JobPlatform = JobPlatform.MANUAL
    external_id: str = ""
    source_url: str = ""
    canonical_url: str = ""
    company: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    location: str = ""
    salary_text: str = ""
    salary_min_k: float | None = Field(default=None, ge=0)
    salary_max_k: float | None = Field(default=None, ge=0)
    employment_type: str = ""
    experience_level: str = ""
    jd_text: str = Field(min_length=1, max_length=100000)
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = ""
    status: JobStatus = JobStatus.DISCOVERED
    metadata: dict = Field(default_factory=dict)


class JobScoreDimension(BaseModel):
    score: float = Field(default=0, ge=0, le=100)
    rationale: str = ""


class JobEvaluation(BaseModel):
    job_id: str
    overall_score: float = Field(default=0, ge=0, le=100)
    decision: JobDecision = JobDecision.REVIEW
    hard_filter_passed: bool = True
    hard_filter_reasons: list[str] = Field(default_factory=list)
    dimensions: dict[str, JobScoreDimension] = Field(default_factory=dict)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    model: str = "heuristic-fallback"
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
