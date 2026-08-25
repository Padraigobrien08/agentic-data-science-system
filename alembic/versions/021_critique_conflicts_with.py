"""Add critiques.conflicts_with_id (the other side of a contradiction; additive, reversible).

Revision ID: 021_critique_conflicts_with
Revises: 020_conclusion_narrative
Create Date: 2026-08-25

A contradiction is a statement about *two* claims — "these cannot both hold" — but the row
recorded only the one being critiqued. Nothing downstream could therefore ask the question
that matters later in a run: has evidence since separated the pair? ``resolved`` was left to
carry that alone, and because it was a flag someone had to remember to set, it was never once
set to ``True`` anywhere in the codebase. Any run that recorded a conflict could not reach
``sufficient_evidence`` again, even after the discriminating experiment settled it.

With both sides stored, resolution is derived from the claims rather than asserted: exactly
one of the pair still standing means the run answered the question.

Nullable, because only ``contradiction`` critiques have a second side; an ordinary challenge
to a single claim keeps a null and loses nothing. Existing rows are unaffected — they are
historical records of conflicts whose pairing is recoverable from their message text.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "021_critique_conflicts_with"
down_revision: Union[str, None] = "020_conclusion_narrative"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A plain nullable add, so this needs no batch block and applies as-is on SQLite as well
    # as Postgres. The index is created separately for the same reason.
    op.add_column(
        "critiques", sa.Column("conflicts_with_id", sa.String(length=128), nullable=True)
    )
    op.create_index(
        "ix_critiques_conflicts_with_id", "critiques", ["conflicts_with_id"], unique=False
    )


def downgrade() -> None:
    # Index first: SQLite rebuilds the table inside a batch block, and an index over a column
    # that block is about to remove cannot survive the rebuild.
    op.drop_index("ix_critiques_conflicts_with_id", table_name="critiques")
    with op.batch_alter_table("critiques") as batch:
        batch.drop_column("conflicts_with_id")
