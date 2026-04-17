"""Add retention markers and selection indexes for storage and ops maintenance.

Revision ID: 010_storage_ops_retention
Revises: 009_merge_ci_heads
Create Date: 2026-04-17

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_storage_ops_retention"
down_revision: Union[str, None] = "009_merge_ci_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("compacted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "model_calls",
        sa.Column("payloads_redacted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analysis_runs_finished_at", "analysis_runs", ["finished_at"], unique=False)
    op.create_index("ix_model_calls_created_at", "model_calls", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_model_calls_created_at", table_name="model_calls")
    op.drop_index("ix_analysis_runs_finished_at", table_name="analysis_runs")
    op.drop_column("model_calls", "payloads_redacted_at")
    op.drop_column("analysis_runs", "compacted_at")
