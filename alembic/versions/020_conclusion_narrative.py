"""Add conclusions.narrative (the finding as prose; additive, reversible).

Revision ID: 020_conclusion_narrative
Revises: 019_schema_metadata_alignment
Create Date: 2026-08-23

The loop may ask its policy to write the finding as prose, because a list of joined
hypothesis statements is the truth but not an answer. What lands here is only ever prose
whose every figure was checked against the run's own recorded values
(``agentic.agent.narrative.verify_narrative``) — a narrative citing a number the run never
produced is discarded rather than stored.

Nullable, and staying nullable: a policy that cannot write is not a broken policy, and
``statement`` remains the deterministic answer of record whether or not this is set. Every
existing row keeps a null and loses nothing.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "020_conclusion_narrative"
down_revision: Union[str, None] = "019_schema_metadata_alignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A plain nullable add: no constraint or type change, so this needs no batch block and
    # applies as-is on SQLite as well as Postgres.
    op.add_column("conclusions", sa.Column("narrative", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conclusions") as batch:
        batch.drop_column("narrative")
