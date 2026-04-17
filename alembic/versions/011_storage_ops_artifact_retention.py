"""Add artifact blob tombstones for retention-aware delivery.

Revision ID: 011_storage_ops_artifact_retention
Revises: 010_storage_ops_retention
Create Date: 2026-04-17

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_storage_ops_artifact_retention"
down_revision: Union[str, None] = "010_storage_ops_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "artifacts",
        sa.Column("blob_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_artifacts_created_at_blob_deleted_at",
        "artifacts",
        ["created_at", "blob_deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_artifacts_created_at_blob_deleted_at", table_name="artifacts")
    op.drop_column("artifacts", "blob_deleted_at")
