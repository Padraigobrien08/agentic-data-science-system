"""Model calls: prompt registry columns (id + version).

Revision ID: 006_prompt_registry
Revises: 005_job_lease
Create Date: 2026-04-10

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_prompt_registry"
down_revision: Union[str, None] = "005_job_lease"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_calls",
        sa.Column("prompt_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "model_calls",
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
    )
    op.create_index(op.f("ix_model_calls_prompt_id"), "model_calls", ["prompt_id"], unique=False)
    op.create_index(op.f("ix_model_calls_prompt_version"), "model_calls", ["prompt_version"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_model_calls_prompt_version"), table_name="model_calls")
    op.drop_index(op.f("ix_model_calls_prompt_id"), table_name="model_calls")
    op.drop_column("model_calls", "prompt_version")
    op.drop_column("model_calls", "prompt_id")
