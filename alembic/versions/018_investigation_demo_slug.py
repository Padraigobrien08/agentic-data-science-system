"""Add investigations.demo_slug (public replay tier; additive, reversible).

Revision ID: 018_investigation_demo_slug
Revises: 017_user_access_tier
Create Date: 2026-08-11

Publishes a recorded investigation to the unauthenticated replay tier. See
``docs/decisions/2026-08-11-showcase-direction.md`` (D3, S1).

Nullable with a unique index: existing rows stay private, and nothing is published until an
operator sets a slug explicitly via ``python -m backend.maintenance.publish_demo``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "018_investigation_demo_slug"
down_revision: Union[str, None] = "017_user_access_tier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("investigations", sa.Column("demo_slug", sa.String(length=64), nullable=True))
    # Unique so two rows cannot claim the same public URL; created as a plain unique index
    # rather than a table constraint because SQLite cannot ALTER a constraint onto an
    # existing table (see 017's note on matching what ``create_all`` emits).
    op.create_index(
        "ix_investigations_demo_slug", "investigations", ["demo_slug"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_investigations_demo_slug", table_name="investigations")
    op.drop_column("investigations", "demo_slug")
