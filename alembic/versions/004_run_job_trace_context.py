"""Store W3C trace context on run execution jobs for worker propagation.

Revision ID: 004_trace_ctx
Revises: 003_jobs
Create Date: 2026-04-10

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_trace_ctx"
down_revision: Union[str, None] = "003_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "run_execution_jobs",
        sa.Column("trace_context_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("run_execution_jobs", "trace_context_json")
