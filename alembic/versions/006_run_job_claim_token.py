"""Add claim token fencing to run execution jobs.

Revision ID: 006_job_claim_token
Revises: 005_job_lease
Create Date: 2026-04-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_job_claim_token"
down_revision: Union[str, None] = "005_job_lease"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "run_execution_jobs",
        sa.Column("claim_token", sa.String(length=36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("run_execution_jobs", "claim_token")
