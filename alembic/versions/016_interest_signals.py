"""Add interest_signals (landing-page lead capture; additive).

Revision ID: 016_interest_signals
Revises: 015_chat_conversations
Create Date: 2026-07-28

Standalone table for unauthenticated "signal of interest" emails left on the
landing page. Not linked to a user account. Purely additive.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "016_interest_signals"
down_revision: Union[str, None] = "015_chat_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interest_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interest_signals_email", "interest_signals", ["email"])


def downgrade() -> None:
    op.drop_index("ix_interest_signals_email", table_name="interest_signals")
    op.drop_table("interest_signals")
