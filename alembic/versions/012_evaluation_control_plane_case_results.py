"""Add case-level persisted results for the evaluation control plane.

Revision ID: 012_evaluation_control_plane_case_results
Revises: 011_storage_ops_artifact_retention
Create Date: 2026-04-18

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_evaluation_control_plane_case_results"
down_revision: Union[str, None] = "011_storage_ops_artifact_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluation_case_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.String(length=256), nullable=False),
        sa.Column("input_mode", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("degradation_class", sa.String(length=64), nullable=False),
        sa.Column("run_goal", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=True),
        sa.Column("observation_json", sa.JSON(), nullable=True),
        sa.Column("checks_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("artifacts_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_run_id", "case_id", name="uq_evaluation_case_results_run_case"),
    )
    op.create_index(
        "ix_evaluation_case_results_evaluation_run_id",
        "evaluation_case_results",
        ["evaluation_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_case_results_run_status",
        "evaluation_case_results",
        ["evaluation_run_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_case_results_run_input_mode",
        "evaluation_case_results",
        ["evaluation_run_id", "input_mode"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_case_results_run_degradation",
        "evaluation_case_results",
        ["evaluation_run_id", "degradation_class"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_evaluation_case_results_run_degradation", table_name="evaluation_case_results")
    op.drop_index("ix_evaluation_case_results_run_input_mode", table_name="evaluation_case_results")
    op.drop_index("ix_evaluation_case_results_run_status", table_name="evaluation_case_results")
    op.drop_index("ix_evaluation_case_results_evaluation_run_id", table_name="evaluation_case_results")
    op.drop_table("evaluation_case_results")
