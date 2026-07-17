"""Add generalized investigation persistence (additive; existing runs untouched).

Revision ID: 014_investigation_persistence
Revises: 013_live_hybrid_evaluation_case_run_links
Create Date: 2026-07-18

Creates the investigation root, reasoning entities, append-only state-event log,
durable orchestration checkpoints, reproducibility manifests, and artifact-linkage
tables. Purely additive: no existing table, column, or row is modified. The two
forward convenience pointers on ``investigations`` (current_conclusion_id,
reproducibility_manifest_id) are plain columns here to avoid a circular
CREATE-time foreign key; the ORM adds them as FKs for metadata-created schemas.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_investigation_persistence"
down_revision: Union[str, None] = "013_live_hybrid_evaluation_case_run_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    # 1. investigations root (forward pointers as plain columns to avoid FK cycle)
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("initiated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("goal_json", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("budget_json", sa.JSON(), nullable=True),
        sa.Column("termination_json", sa.JSON(), nullable=True),
        sa.Column("current_conclusion_id", sa.Uuid(), nullable=True),
        sa.Column("reproducibility_manifest_id", sa.Uuid(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("domain_id", name="uq_investigations_domain_id"),
        sa.UniqueConstraint("analysis_run_id", name="uq_investigations_analysis_run_id"),
    )
    op.create_index("ix_investigations_project_id", "investigations", ["project_id"])
    op.create_index("ix_investigations_status", "investigations", ["status"])
    op.create_index("ix_investigations_origin", "investigations", ["origin"])

    # 2. reproducibility_manifests
    op.create_table(
        "reproducibility_manifests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=True),
        sa.Column("domain_id", sa.String(length=128), nullable=True),
        sa.Column("code_version", sa.String(length=128), nullable=True),
        sa.Column("tool_versions_json", sa.JSON(), nullable=True),
        sa.Column("prompt_versions_json", sa.JSON(), nullable=True),
        sa.Column("model_config_json", sa.JSON(), nullable=True),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("dataset_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("parameters_hash", sa.String(length=128), nullable=True),
        sa.Column("environment_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_reproducibility_manifests_investigation_id", "reproducibility_manifests", ["investigation_id"])

    # 3. investigation_datasets
    op.create_table(
        "investigation_datasets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("data_source_json", sa.JSON(), nullable=True),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_investigation_datasets_investigation_id", "investigation_datasets", ["investigation_id"])

    # 4. hypotheses (self FK for parent)
    op.create_table(
        "hypotheses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("prior_confidence", sa.Float(), nullable=False),
        sa.Column("parent_hypothesis_id", sa.Uuid(), nullable=True),
        sa.Column("metric_refs_json", sa.JSON(), nullable=True),
        sa.Column("entity_refs_json", sa.JSON(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_hypothesis_id"], ["hypotheses.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_hypotheses_investigation_id", "hypotheses", ["investigation_id"])
    op.create_index("ix_hypotheses_domain_id", "hypotheses", ["domain_id"])
    op.create_index("ix_hypotheses_status", "hypotheses", ["status"])

    # 5. experiment_requests
    op.create_table(
        "experiment_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("definition_id", sa.String(length=128), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("target_hypothesis_ids_json", sa.JSON(), nullable=True),
        sa.Column("cost_estimate_json", sa.JSON(), nullable=True),
        sa.Column("expected_information_gain", sa.Float(), nullable=True),
        sa.Column("preconditions_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("reproducibility_manifest_id", sa.Uuid(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reproducibility_manifest_id"], ["reproducibility_manifests.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("investigation_id", "domain_id", name="uq_experiment_request_domain_id"),
    )
    op.create_index("ix_experiment_requests_investigation_id", "experiment_requests", ["investigation_id"])
    op.create_index("ix_experiment_requests_tool_name", "experiment_requests", ["tool_name"])

    # 6. experiment_results (idempotency unique key)
    op.create_table(
        "experiment_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("request_domain_id", sa.String(length=128), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tool_version", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("output_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("statistics_json", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("reproducibility_manifest_id", sa.Uuid(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["experiment_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reproducibility_manifest_id"], ["reproducibility_manifests.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("investigation_id", "idempotency_key", name="uq_experiment_result_idempotency"),
    )
    op.create_index("ix_experiment_results_investigation_id", "experiment_results", ["investigation_id"])
    op.create_index("ix_experiment_results_idempotency_key", "experiment_results", ["idempotency_key"])
    op.create_index("ix_experiment_results_tool_name", "experiment_results", ["tool_name"])

    # 7. observations
    op.create_table(
        "observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("experiment_result_id", sa.Uuid(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("observation_type", sa.String(length=64), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=True),
        sa.Column("entity_ref", sa.String(length=256), nullable=True),
        sa.Column("metric_ref", sa.String(length=256), nullable=True),
        sa.Column("data_reference_json", sa.JSON(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experiment_result_id"], ["experiment_results.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_observations_investigation_id", "observations", ["investigation_id"])

    # 8. evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("experiment_result_id", sa.Uuid(), nullable=True),
        sa.Column("source_reference_json", sa.JSON(), nullable=True),
        sa.Column("payload_reference_json", sa.JSON(), nullable=True),
        sa.Column("statistics_json", sa.JSON(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experiment_result_id"], ["experiment_results.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_evidence_investigation_id", "evidence", ["investigation_id"])
    op.create_index("ix_evidence_type", "evidence", ["evidence_type"])

    # 9. conclusions
    op.create_table(
        "conclusions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("disposition", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("supporting_hypothesis_ids_json", sa.JSON(), nullable=True),
        sa.Column("key_evidence_ids_json", sa.JSON(), nullable=True),
        sa.Column("caveats_json", sa.JSON(), nullable=True),
        sa.Column("open_question_ids_json", sa.JSON(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conclusions_investigation_id", "conclusions", ["investigation_id"])

    # 10. agent_decisions / critiques / open_questions
    op.create_table(
        "agent_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("targets_json", sa.JSON(), nullable=True),
        sa.Column("chosen_option", sa.Text(), nullable=True),
        sa.Column("alternatives_json", sa.JSON(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_decisions_investigation_id", "agent_decisions", ["investigation_id"])

    op.create_table(
        "critiques",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("critique_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("target_kind", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_critiques_investigation_id", "critiques", ["investigation_id"])

    op.create_table(
        "open_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("related_hypothesis_ids_json", sa.JSON(), nullable=True),
        sa.Column("answered_by_evidence_ids_json", sa.JSON(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_open_questions_investigation_id", "open_questions", ["investigation_id"])

    # 11. append-only state events
    op.create_table(
        "investigation_state_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_kind", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("investigation_id", "sequence", name="uq_state_event_seq"),
    )
    op.create_index("ix_investigation_state_events_investigation_id", "investigation_state_events", ["investigation_id"])

    # 12. durable orchestration checkpoints
    op.create_table(
        "orchestration_checkpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("investigation_id", "sequence", name="uq_checkpoint_seq"),
    )
    op.create_index("ix_orchestration_checkpoints_investigation_id", "orchestration_checkpoints", ["investigation_id"])

    # 13. association / artifact-linkage tables
    op.create_table(
        "evidence_hypothesis_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("hypothesis_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["hypotheses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("evidence_id", "hypothesis_id", name="uq_evidence_hypothesis"),
    )
    op.create_index("ix_evidence_hypothesis_links_evidence_id", "evidence_hypothesis_links", ["evidence_id"])
    op.create_index("ix_evidence_hypothesis_links_hypothesis_id", "evidence_hypothesis_links", ["hypothesis_id"])

    op.create_table(
        "evidence_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("evidence_id", "artifact_id", name="uq_evidence_artifact"),
    )
    op.create_index("ix_evidence_artifacts_evidence_id", "evidence_artifacts", ["evidence_id"])
    op.create_index("ix_evidence_artifacts_artifact_id", "evidence_artifacts", ["artifact_id"])

    op.create_table(
        "experiment_result_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_result_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["experiment_result_id"], ["experiment_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("experiment_result_id", "artifact_id", name="uq_experiment_result_artifact"),
    )
    op.create_index(
        "ix_experiment_result_artifacts_result_id", "experiment_result_artifacts", ["experiment_result_id"]
    )
    op.create_index("ix_experiment_result_artifacts_artifact_id", "experiment_result_artifacts", ["artifact_id"])


def downgrade() -> None:
    for table in (
        "experiment_result_artifacts",
        "evidence_artifacts",
        "evidence_hypothesis_links",
        "orchestration_checkpoints",
        "investigation_state_events",
        "open_questions",
        "critiques",
        "agent_decisions",
        "conclusions",
        "evidence",
        "observations",
        "experiment_results",
        "experiment_requests",
        "hypotheses",
        "investigation_datasets",
        "reproducibility_manifests",
        "investigations",
    ):
        op.drop_table(table)
