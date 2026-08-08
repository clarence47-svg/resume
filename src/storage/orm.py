from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
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
