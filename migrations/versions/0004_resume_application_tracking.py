from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_resume_application_tracking"
down_revision: str | None = "0003_career_campaign_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("profile_task_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("match_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.String(length=32), nullable=False),
        sa.Column("document_json", sa.JSON(), nullable=False),
        sa.Column("markdown_path", sa.Text(), nullable=False),
        sa.Column("html_path", sa.Text(), nullable=False),
        sa.Column("docx_path", sa.Text(), nullable=False),
        sa.Column("pdf_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["match_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_task_id"], ["profile_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "version", name="uq_resume_job_version"),
    )
    op.create_index("ix_resume_versions_job_id", "resume_versions", ["job_id"])
    op.create_index("ix_resume_versions_profile_task_id", "resume_versions", ["profile_task_id"])
    op.create_index("ix_resume_versions_match_id", "resume_versions", ["match_id"])
    op.create_table(
        "application_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("resume_version_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("encrypted_preview", sa.Text(), nullable=False),
        sa.Column("preview_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("blocker_code", sa.String(length=64), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("graph_thread_id", sa.String(length=100), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_application_attempts_job_id", ["job_id"]),
        ("ix_application_attempts_resume_version_id", ["resume_version_id"]),
        ("ix_application_attempts_status", ["status"]),
        ("ix_application_attempts_platform", ["platform"]),
    ):
        op.create_index(name, "application_attempts", columns)
    op.create_table(
        "application_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["application_attempts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_events_application_id", "application_events", ["application_id"]
    )
    op.create_index("ix_application_events_event_type", "application_events", ["event_type"])
    op.create_table(
        "application_blockers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["application_attempts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_blockers_application_id",
        "application_blockers",
        ["application_id"],
    )
    op.create_index("ix_application_blockers_code", "application_blockers", ["code"])
    op.create_index("ix_application_blockers_status", "application_blockers", ["status"])
    op.create_table(
        "follow_up_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["application_attempts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_follow_up_events_application_id", "follow_up_events", ["application_id"])
    op.create_index("ix_follow_up_events_scheduled_at", "follow_up_events", ["scheduled_at"])
    op.create_table(
        "interview_kits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("resume_version_id", sa.String(length=36), nullable=False),
        sa.Column("kit_json", sa.JSON(), nullable=False),
        sa.Column("markdown_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interview_kits_job_id", "interview_kits", ["job_id"])
    op.create_index("ix_interview_kits_resume_version_id", "interview_kits", ["resume_version_id"])


def downgrade() -> None:
    op.drop_table("interview_kits")
    op.drop_table("follow_up_events")
    op.drop_table("application_blockers")
    op.drop_table("application_events")
    op.drop_table("application_attempts")
    op.drop_table("resume_versions")
