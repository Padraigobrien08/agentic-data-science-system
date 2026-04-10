"""Core domain: users, projects, analysis_runs, steps, tools, artifacts, evaluations, model_calls.

Replaces legacy ``runs`` and ``evaluation_runs`` from 001 (data in those tables is dropped).

Revision ID: 002_core
Revises: 001_initial
Create Date: 2026-04-10

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_core"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("runs")
    op.drop_table("evaluation_runs")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("preferences_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_owner_user_id"), "projects", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_projects_slug"), "projects", ["slug"], unique=False)

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("initiated_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("orchestration_goal_text", sa.Text(), nullable=True),
        sa.Column("input_payload_json", sa.JSON(), nullable=True),
        sa.Column("output_payload_json", sa.JSON(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_runs_correlation_id"), "analysis_runs", ["correlation_id"], unique=True)
    op.create_index(op.f("ix_analysis_runs_initiated_by_user_id"), "analysis_runs", ["initiated_by_user_id"], unique=False)
    op.create_index(op.f("ix_analysis_runs_project_id"), "analysis_runs", ["project_id"], unique=False)
    op.create_index(op.f("ix_analysis_runs_status"), "analysis_runs", ["status"], unique=False)

    op.create_table(
        "run_steps",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("label", sa.String(length=512), nullable=True),
        sa.Column("planned_tool_name", sa.String(length=128), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("planner_tool_input_json", sa.JSON(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "step_index", name="uq_run_steps_analysis_run_id_step_index"),
    )
    op.create_index(op.f("ix_run_steps_analysis_run_id"), "run_steps", ["analysis_run_id"], unique=False)
    op.create_index(op.f("ix_run_steps_planned_tool_name"), "run_steps", ["planned_tool_name"], unique=False)
    op.create_index(op.f("ix_run_steps_status"), "run_steps", ["status"], unique=False)
    op.create_index(op.f("ix_run_steps_step_index"), "run_steps", ["step_index"], unique=False)

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("initiated_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("suite_id", sa.String(length=256), nullable=False),
        sa.Column("suite_manifest_path", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("results_json", sa.JSON(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluation_runs_initiated_by_user_id"), "evaluation_runs", ["initiated_by_user_id"], unique=False)
    op.create_index(op.f("ix_evaluation_runs_project_id"), "evaluation_runs", ["project_id"], unique=False)
    op.create_index(op.f("ix_evaluation_runs_status"), "evaluation_runs", ["status"], unique=False)
    op.create_index(op.f("ix_evaluation_runs_suite_id"), "evaluation_runs", ["suite_id"], unique=False)

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_step_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("mcp_status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("request_params_json", sa.JSON(), nullable=True),
        sa.Column("response_envelope_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("panel_row_count", sa.Integer(), nullable=True),
        sa.Column("feature_row_count", sa.Integer(), nullable=True),
        sa.Column("anomaly_count", sa.Integer(), nullable=True),
        sa.Column("report_character_count", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_step_id"], ["run_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tool_calls_analysis_run_id"), "tool_calls", ["analysis_run_id"], unique=False)
    op.create_index(op.f("ix_tool_calls_mcp_status"), "tool_calls", ["mcp_status"], unique=False)
    op.create_index(op.f("ix_tool_calls_run_step_id"), "tool_calls", ["run_step_id"], unique=True)
    op.create_index(op.f("ix_tool_calls_tool_name"), "tool_calls", ["tool_name"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("evaluation_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("run_step_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("role_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("storage_uri", sa.String(length=2048), nullable=False),
        sa.Column("mime_type", sa.String(length=256), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_step_id"], ["run_steps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifacts_analysis_run_id"), "artifacts", ["analysis_run_id"], unique=False)
    op.create_index(op.f("ix_artifacts_content_sha256"), "artifacts", ["content_sha256"], unique=False)
    op.create_index(op.f("ix_artifacts_evaluation_run_id"), "artifacts", ["evaluation_run_id"], unique=False)
    op.create_index(op.f("ix_artifacts_kind"), "artifacts", ["kind"], unique=False)
    op.create_index(op.f("ix_artifacts_role_key"), "artifacts", ["role_key"], unique=False)
    op.create_index(op.f("ix_artifacts_run_step_id"), "artifacts", ["run_step_id"], unique=False)

    op.create_table(
        "model_calls",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("evaluation_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("tool_call_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_payload_json", sa.JSON(), nullable=True),
        sa.Column("response_payload_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_call_id"], ["tool_calls.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_calls_analysis_run_id"), "model_calls", ["analysis_run_id"], unique=False)
    op.create_index(op.f("ix_model_calls_evaluation_run_id"), "model_calls", ["evaluation_run_id"], unique=False)
    op.create_index(op.f("ix_model_calls_model_name"), "model_calls", ["model_name"], unique=False)
    op.create_index(op.f("ix_model_calls_provider"), "model_calls", ["provider"], unique=False)
    op.create_index(op.f("ix_model_calls_status"), "model_calls", ["status"], unique=False)
    op.create_index(op.f("ix_model_calls_tool_call_id"), "model_calls", ["tool_call_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_model_calls_tool_call_id"), table_name="model_calls")
    op.drop_index(op.f("ix_model_calls_status"), table_name="model_calls")
    op.drop_index(op.f("ix_model_calls_provider"), table_name="model_calls")
    op.drop_index(op.f("ix_model_calls_model_name"), table_name="model_calls")
    op.drop_index(op.f("ix_model_calls_evaluation_run_id"), table_name="model_calls")
    op.drop_index(op.f("ix_model_calls_analysis_run_id"), table_name="model_calls")
    op.drop_table("model_calls")

    op.drop_index(op.f("ix_artifacts_run_step_id"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_role_key"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_kind"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_evaluation_run_id"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_content_sha256"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_analysis_run_id"), table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index(op.f("ix_tool_calls_tool_name"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_run_step_id"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_mcp_status"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_analysis_run_id"), table_name="tool_calls")
    op.drop_table("tool_calls")

    op.drop_index(op.f("ix_evaluation_runs_suite_id"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_status"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_project_id"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_initiated_by_user_id"), table_name="evaluation_runs")
    op.drop_table("evaluation_runs")

    op.drop_index(op.f("ix_run_steps_step_index"), table_name="run_steps")
    op.drop_index(op.f("ix_run_steps_status"), table_name="run_steps")
    op.drop_index(op.f("ix_run_steps_planned_tool_name"), table_name="run_steps")
    op.drop_index(op.f("ix_run_steps_analysis_run_id"), table_name="run_steps")
    op.drop_table("run_steps")

    op.drop_index(op.f("ix_analysis_runs_status"), table_name="analysis_runs")
    op.drop_index(op.f("ix_analysis_runs_project_id"), table_name="analysis_runs")
    op.drop_index(op.f("ix_analysis_runs_initiated_by_user_id"), table_name="analysis_runs")
    op.drop_index(op.f("ix_analysis_runs_correlation_id"), table_name="analysis_runs")
    op.drop_table("analysis_runs")

    op.drop_index(op.f("ix_projects_slug"), table_name="projects")
    op.drop_index(op.f("ix_projects_owner_user_id"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("suite_id", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluation_runs_suite_id"), "evaluation_runs", ["suite_id"], unique=False)
    op.create_index(op.f("ix_evaluation_runs_status"), "evaluation_runs", ["status"], unique=False)

    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("external_run_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runs_external_run_id"), "runs", ["external_run_id"], unique=False)
    op.create_index(op.f("ix_runs_status"), "runs", ["status"], unique=False)
