"""Run execution job queue and ``queued`` analysis run status.

Revision ID: 003_jobs
Revises: 002_core
Create Date: 2026-04-10

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_jobs"
down_revision: Union[str, None] = "002_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "run_execution_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("overrides_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_run_execution_jobs_analysis_run_id"),
        "run_execution_jobs",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_run_execution_jobs_status"),
        "run_execution_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_run_execution_jobs_status"), table_name="run_execution_jobs")
    op.drop_index(op.f("ix_run_execution_jobs_analysis_run_id"), table_name="run_execution_jobs")
    op.drop_table("run_execution_jobs")
