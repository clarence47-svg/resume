from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_career_campaign_jobs"
down_revision: str | None = "0002_jd_match_agent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "answer_bank",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("question_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_answer_bank_question_key", "answer_bank", ["question_key"])
    op.create_index("ix_answer_bank_status", "answer_bank", ["status"])
    op.create_table(
        "job_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_task_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("strategy", sa.String(length=24), nullable=False),
        sa.Column("search_keywords", sa.JSON(), nullable=False),
        sa.Column("target_cities", sa.JSON(), nullable=False),
        sa.Column("source_platforms", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_task_id"], ["profile_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_campaigns_profile_task_id", "job_campaigns", ["profile_task_id"])
    op.create_index("ix_job_campaigns_status", "job_campaigns", ["status"])
    op.create_table(
        "job_postings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("profile_task_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("salary_text", sa.String(length=255), nullable=False),
        sa.Column("salary_min_k", sa.Float(), nullable=True),
        sa.Column("salary_max_k", sa.Float(), nullable=True),
        sa.Column("employment_type", sa.String(length=120), nullable=False),
        sa.Column("experience_level", sa.String(length=120), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["job_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_task_id"], ["profile_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_job_postings_campaign_id", ["campaign_id"]),
        ("ix_job_postings_profile_task_id", ["profile_task_id"]),
        ("ix_job_postings_platform", ["platform"]),
        ("ix_job_postings_company", ["company"]),
        ("ix_job_postings_title", ["title"]),
        ("ix_job_postings_content_hash", ["content_hash"]),
        ("ix_job_postings_status", ["status"]),
    ):
        op.create_index(name, "job_postings", columns)
    op.create_table(
        "job_evaluations",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_json", sa.JSON(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_job_evaluations_overall_score", "job_evaluations", ["overall_score"])
    op.create_index("ix_job_evaluations_decision", "job_evaluations", ["decision"])
    op.create_table(
        "tailoring_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("profile_task_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("job_ids", sa.JSON(), nullable=False),
        sa.Column("match_ids", sa.JSON(), nullable=False),
        sa.Column("aggregate_gaps", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["job_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_task_id"], ["profile_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tailoring_batches_campaign_id", "tailoring_batches", ["campaign_id"])
    op.create_index(
        "ix_tailoring_batches_profile_task_id", "tailoring_batches", ["profile_task_id"]
    )
    op.create_index("ix_tailoring_batches_status", "tailoring_batches", ["status"])
    with op.batch_alter_table("match_tasks") as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("batch_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_match_tasks_job_id", "job_postings", ["job_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            "fk_match_tasks_batch_id",
            "tailoring_batches",
            ["batch_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_match_tasks_job_id", ["job_id"])
        batch_op.create_index("ix_match_tasks_batch_id", ["batch_id"])


def downgrade() -> None:
    with op.batch_alter_table("match_tasks") as batch_op:
        batch_op.drop_index("ix_match_tasks_batch_id")
        batch_op.drop_index("ix_match_tasks_job_id")
        batch_op.drop_constraint("fk_match_tasks_batch_id", type_="foreignkey")
        batch_op.drop_constraint("fk_match_tasks_job_id", type_="foreignkey")
        batch_op.drop_column("batch_id")
        batch_op.drop_column("job_id")
    op.drop_table("tailoring_batches")
    op.drop_table("job_evaluations")
    op.drop_table("job_postings")
    op.drop_table("job_campaigns")
    op.drop_table("answer_bank")
    op.drop_table("career_settings")
