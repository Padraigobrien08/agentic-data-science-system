"""Add child analysis-run linkage fields to evaluation case results.

Revision ID: 013_live_hybrid_evaluation_case_run_links
Revises: 012_evaluation_control_plane_case_results
Create Date: 2026-04-18

The foreign key lands through ``op.batch_alter_table`` because SQLite has no
``ALTER TABLE ... ADD CONSTRAINT``; batch mode copies the table and moves it into place.
On Postgres batch mode is a pass-through that emits the same plain ``ALTER`` statements,
so the production schema is unchanged either way.

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_live_hybrid_evaluation_case_run_links"
down_revision: Union[str, None] = "012_evaluation_control_plane_case_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columns and constraint go in one batch so SQLite rebuilds the table once.
    with op.batch_alter_table("evaluation_case_results") as batch_op:
        batch_op.add_column(sa.Column("latest_analysis_run_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("latest_analysis_run_status", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("analysis_run_history_json", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_evaluation_case_results_latest_analysis_run_id",
            "analysis_runs",
            ["latest_analysis_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_evaluation_case_results_latest_analysis_run_id",
        "evaluation_case_results",
        ["latest_analysis_run_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop the index first: a batch rebuild reflects surviving indexes and would try to
    # recreate this one against the column it is about to remove.
    op.drop_index(
        "ix_evaluation_case_results_latest_analysis_run_id",
        table_name="evaluation_case_results",
    )
    with op.batch_alter_table("evaluation_case_results") as batch_op:
        batch_op.drop_constraint(
            "fk_evaluation_case_results_latest_analysis_run_id",
            type_="foreignkey",
        )
        batch_op.drop_column("analysis_run_history_json")
        batch_op.drop_column("latest_analysis_run_status")
        batch_op.drop_column("latest_analysis_run_id")
