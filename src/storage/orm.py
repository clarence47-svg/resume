from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProfileTaskORM(Base):
    __tablename__ = "profile_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(64), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    review_mode: Mapped[str] = mapped_column(String(16), default="auto")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    graph_thread_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    documents: Mapped[list["DocumentORM"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    facts: Mapped[list["FactORM"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    result: Mapped["ProfileResultORM | None"] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )
    matches: Mapped[list["MatchTaskORM"]] = relationship(
        back_populates="profile_task", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["JobCampaignORM"]] = relationship(
        back_populates="profile_task", cascade="all, delete-orphan"
    )


class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("profile_tasks.id", ondelete="CASCADE"))
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extension: Mapped[str] = mapped_column(String(16))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="stored")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    task: Mapped[ProfileTaskORM] = relationship(back_populates="documents")


class FactORM(Base):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("profile_tasks.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(64), index=True)
    statement: Mapped[str] = mapped_column(Text)
    basis_type: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16))
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    task: Mapped[ProfileTaskORM] = relationship(back_populates="facts")


class ProfileResultORM(Base):
    __tablename__ = "profile_results"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("profile_tasks.id", ondelete="CASCADE"), primary_key=True
    )
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    markdown_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    docx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    task: Mapped[ProfileTaskORM] = relationship(back_populates="result")


class MatchTaskORM(Base):
    __tablename__ = "match_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_task_id: Mapped[str] = mapped_column(
        ForeignKey("profile_tasks.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("tailoring_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    jd_text: Mapped[str] = mapped_column(Text)
    profile_result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    facts_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    conflicts_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    jd_analysis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(64), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    graph_thread_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    profile_task: Mapped[ProfileTaskORM] = relationship(back_populates="matches")
    result: Mapped["MatchResultORM | None"] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )
    versions: Mapped[list["MatchResultVersionORM"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class MatchResultORM(Base):
    __tablename__ = "match_results"

    match_id: Mapped[str] = mapped_column(
        ForeignKey("match_tasks.id", ondelete="CASCADE"), primary_key=True
    )
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    current_version: Mapped[int] = mapped_column(Integer)
    markdown_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    docx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    task: Mapped[MatchTaskORM] = relationship(back_populates="result")


class MatchResultVersionORM(Base):
    __tablename__ = "match_result_versions"

    match_id: Mapped[str] = mapped_column(
        ForeignKey("match_tasks.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    markdown_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    docx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    task: Mapped[MatchTaskORM] = relationship(back_populates="versions")


class CareerSettingsORM(Base):
    __tablename__ = "career_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    encrypted_payload: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AnswerBankORM(Base):
    __tablename__ = "answer_bank"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_key: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    encrypted_payload: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class JobCampaignORM(Base):
    __tablename__ = "job_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_task_id: Mapped[str] = mapped_column(
        ForeignKey("profile_tasks.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    strategy: Mapped[str] = mapped_column(String(24))
    search_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_cities: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_platforms: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    profile_task: Mapped[ProfileTaskORM] = relationship(back_populates="campaigns")
    jobs: Mapped[list["JobPostingORM"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    batches: Mapped[list["TailoringBatchORM"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class JobPostingORM(Base):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("job_campaigns.id", ondelete="CASCADE"), index=True
    )
    profile_task_id: Mapped[str] = mapped_column(
        ForeignKey("profile_tasks.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[str] = mapped_column(String(255), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    canonical_url: Mapped[str] = mapped_column(Text, default="")
    company: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    salary_text: Mapped[str] = mapped_column(String(255), default="")
    salary_min_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(120), default="")
    experience_level: Mapped[str] = mapped_column(String(120), default="")
    jd_text: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    campaign: Mapped[JobCampaignORM] = relationship(back_populates="jobs")
    evaluation: Mapped["JobEvaluationORM | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    resumes: Mapped[list["ResumeVersionORM"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list["ApplicationAttemptORM"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    interview_kits: Mapped[list["InterviewKitORM"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobEvaluationORM(Base):
    __tablename__ = "job_evaluations"

    job_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True
    )
    evaluation_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    overall_score: Mapped[float] = mapped_column(Float, default=0, index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    job: Mapped[JobPostingORM] = relationship(back_populates="evaluation")


class TailoringBatchORM(Base):
    __tablename__ = "tailoring_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("job_campaigns.id", ondelete="CASCADE"), index=True
    )
    profile_task_id: Mapped[str] = mapped_column(
        ForeignKey("profile_tasks.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    job_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    match_ids: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    aggregate_gaps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    campaign: Mapped[JobCampaignORM] = relationship(back_populates="batches")


class ResumeVersionORM(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (UniqueConstraint("job_id", "version", name="uq_resume_job_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    profile_task_id: Mapped[str] = mapped_column(
        ForeignKey("profile_tasks.id", ondelete="CASCADE"), index=True
    )
    match_id: Mapped[str] = mapped_column(
        ForeignKey("match_tasks.id", ondelete="CASCADE"), index=True
    )
    match_version: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    template: Mapped[str] = mapped_column(String(32))
    document_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    markdown_path: Mapped[str] = mapped_column(Text, default="")
    html_path: Mapped[str] = mapped_column(Text, default="")
    docx_path: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    job: Mapped[JobPostingORM] = relationship(back_populates="resumes")
    applications: Mapped[list["ApplicationAttemptORM"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )


class ApplicationAttemptORM(Base):
    __tablename__ = "application_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    resume_version_id: Mapped[str] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    encrypted_preview: Mapped[str] = mapped_column(Text, default="")
    preview_hash: Mapped[str] = mapped_column(String(64), default="")
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    blocker_code: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_thread_id: Mapped[str] = mapped_column(String(100))
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    job: Mapped[JobPostingORM] = relationship(back_populates="applications")
    resume: Mapped[ResumeVersionORM] = relationship(back_populates="applications")
    events: Mapped[list["ApplicationEventORM"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    blockers: Mapped[list["BlockerORM"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    follow_ups: Mapped[list["FollowUpORM"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationEventORM(Base):
    __tablename__ = "application_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("application_attempts.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped[ApplicationAttemptORM] = relationship(back_populates="events")


class BlockerORM(Base):
    __tablename__ = "application_blockers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("application_attempts.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    next_action: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped[ApplicationAttemptORM] = relationship(back_populates="blockers")


class FollowUpORM(Base):
    __tablename__ = "follow_up_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("application_attempts.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped[ApplicationAttemptORM] = relationship(back_populates="follow_ups")


class InterviewKitORM(Base):
    __tablename__ = "interview_kits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    resume_version_id: Mapped[str] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True
    )
    kit_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    markdown_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    job: Mapped[JobPostingORM] = relationship(back_populates="interview_kits")
