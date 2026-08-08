from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_jd_match_agent"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_task_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("profile_result_snapshot", sa.JSON(), nullable=False),
        sa.Column("facts_snapshot", sa.JSON(), nullable=False),
        sa.Column("conflicts_snapshot", sa.JSON(), nullable=False),
        sa.Column("jd_analysis", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("graph_thread_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_task_id"], ["profile_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_tasks_profile_task_id", "match_tasks", ["profile_task_id"])
    op.create_index("ix_match_tasks_status", "match_tasks", ["status"])
    op.create_table(
        "match_results",
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("markdown_path", sa.Text(), nullable=True),
        sa.Column("docx_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["match_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("match_id"),
    )
    op.create_table(
        "match_result_versions",
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("markdown_path", sa.Text(), nullable=True),
        sa.Column("docx_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["match_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("match_id", "version"),
    )


def downgrade() -> None:
    op.drop_table("match_result_versions")
    op.drop_table("match_results")
    op.drop_index("ix_match_tasks_status", table_name="match_tasks")
    op.drop_index("ix_match_tasks_profile_task_id", table_name="match_tasks")
    op.drop_table("match_tasks")
