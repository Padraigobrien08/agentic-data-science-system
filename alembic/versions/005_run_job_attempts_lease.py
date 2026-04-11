"""Run execution jobs: attempt counter and lease expiry for worker hardening.

Revision ID: 005_job_lease
Revises: 004_trace_ctx
Create Date: 2026-04-11

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_job_lease"
down_revision: Union[str, None] = "004_trace_ctx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "run_execution_jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "run_execution_jobs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("run_execution_jobs", "lease_expires_at")
    op.drop_column("run_execution_jobs", "attempt_count")
