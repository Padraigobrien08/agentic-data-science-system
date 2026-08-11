"""Add users.access_tier (spend entitlement; additive, reversible).

Revision ID: 017_user_access_tier
Revises: 016_interest_signals
Create Date: 2026-08-11

Decides which execution engine a user's runs may use and which spend ceiling applies
(``guest`` < ``standard`` < ``adaptive``). See ``docs/decisions/2026-08-11-showcase-direction.md``.

Existing rows backfill to ``standard`` — the deterministic engine — so turning on
``EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED`` cannot retroactively grant the paid loop to
accounts that predate this column.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "017_user_access_tier"
down_revision: Union[str, None] = "016_interest_signals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Deliberately ``String``, not ``sa.Enum``. ``backend.models.types.str_enum_column`` uses
#: ``native_enum=False``, which under SQLAlchemy 2.0 defaults to ``create_constraint=False``
#: — so ``create_all`` emits a bare ``VARCHAR(8)`` with no CHECK on both SQLite and Postgres.
#: An ``sa.Enum`` here would add a CHECK the ORM never creates, so a database built from
#: migrations would differ from one built from metadata (which is what the tests use), and
#: SQLite cannot ALTER a constraint onto an existing table anyway. Length 8 matches the
#: longest member ("standard"/"adaptive"), which is what SQLAlchemy computes for the model.
_TIER = sa.String(length=8)


def upgrade() -> None:
    # server_default backfills existing rows in the same statement, so the column can be
    # NOT NULL immediately without a separate UPDATE pass.
    op.add_column(
        "users",
        sa.Column("access_tier", _TIER, nullable=False, server_default="standard"),
    )
    op.create_index("ix_users_access_tier", "users", ["access_tier"])


def downgrade() -> None:
    op.drop_index("ix_users_access_tier", table_name="users")
    op.drop_column("users", "access_tier")
