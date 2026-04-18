"""Add child analysis-run linkage fields to evaluation case results.

Revision ID: 013_live_hybrid_evaluation_case_run_links
Revises: 012_evaluation_control_plane_case_results
Create Date: 2026-04-18

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
    op.add_column(
        "evaluation_case_results",
        sa.Column("latest_analysis_run_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("latest_analysis_run_status", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("analysis_run_history_json", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        "fk_evaluation_case_results_latest_analysis_run_id",
        "evaluation_case_results",
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
    op.drop_index(
        "ix_evaluation_case_results_latest_analysis_run_id",
        table_name="evaluation_case_results",
    )
    op.drop_constraint(
        "fk_evaluation_case_results_latest_analysis_run_id",
        "evaluation_case_results",
        type_="foreignkey",
    )
    op.drop_column("evaluation_case_results", "analysis_run_history_json")
    op.drop_column("evaluation_case_results", "latest_analysis_run_status")
    op.drop_column("evaluation_case_results", "latest_analysis_run_id")
