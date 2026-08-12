"""Bring the migrated schema in line with ``Base.metadata``.

Revision ID: 019_schema_metadata_alignment
Revises: 018_investigation_demo_slug
Create Date: 2026-08-12

A database built from migrations did not match one built from ``Base.metadata.create_all``
— the schema the tests run against. ``alembic.autogenerate.compare_metadata`` reported 51
differences at ``018``, all of them cases where a migration under-delivered what the ORM
already declares:

* 35 indexes for columns declared ``index=True`` (mostly the ``014`` investigation tables),
  never created by the migration that made those tables.
* 2 forward-pointer foreign keys on ``investigations``. ``014`` left them as plain columns
  to avoid a circular ``CREATE TABLE`` dependency and noted the ORM adds them anyway; both
  tables exist by now, so they can be added here.
* 2 unique constraints on ``investigations`` replaced by the unique *indexes* the model
  declares via ``unique=True, index=True``. Same invariant, different object.
* 2 indexes renamed to the names the models generate.
* 10 enum-backed columns written as ``VARCHAR(32)`` but computed by SQLAlchemy as the
  width of the longest member. Same alignment rule as ``017_user_access_tier``'s note on
  ``str_enum_column``: a database built from migrations must match one built from metadata.

The reverse direction — DB objects the models did not know about — was fixed on the model
side instead (``artifacts`` retention index, ``evaluation_case_results`` unique constraint
and its three composite indexes, and ten server defaults), so nothing here drops an object
that carries intent.

Two operational notes for Postgres. The ``VARCHAR`` narrowings rewrite their tables under
an ACCESS EXCLUSIVE lock; every stored value is an enum member well inside the new width,
so no row can fail, but on a large table this is not instant. Index creation is plain
(not ``CONCURRENTLY``) because Alembic runs migrations inside a transaction.

On SQLite the constraint and type work goes through ``op.batch_alter_table``, which copies
and moves each table; index creation is dialect-agnostic.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019_schema_metadata_alignment"
down_revision: Union[str, None] = "018_investigation_demo_slug"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: ``(table, column, aligned_width)`` for enum-backed columns. The aligned width is what
#: ``str_enum_column`` compiles to — the longest member — on both dialects.
#: ``native_enum=False`` means no CHECK constraint is involved on either side.
_ENUM_WIDTHS: tuple[tuple[str, str, int], ...] = (
    ("analysis_runs", "status", 15),
    ("artifacts", "kind", 8),
    ("chat_messages", "role", 9),
    ("chat_messages", "status", 8),
    ("evaluation_runs", "status", 7),
    ("investigations", "origin", 13),
    ("model_calls", "status", 9),
    ("run_execution_jobs", "status", 9),
    ("run_steps", "status", 7),
    ("tool_calls", "mcp_status", 7),
)

_PREVIOUS_ENUM_WIDTH = 32

#: Server defaults must be restated on every ``alter_column`` that changes a type, or
#: Postgres keeps the old default while SQLite's table rebuild silently drops it.
_SERVER_DEFAULTS: dict[tuple[str, str], str] = {
    ("analysis_runs", "status"): "pending",
    ("artifacts", "kind"): "other",
    ("evaluation_runs", "status"): "pending",
    ("model_calls", "status"): "pending",
    ("run_execution_jobs", "status"): "pending",
    ("run_steps", "status"): "pending",
    ("tool_calls", "mcp_status"): "success",
}

#: Indexes the ORM declares but no migration ever created.
_MISSING_INDEXES: tuple[tuple[str, str, list[str], bool], ...] = (
    ("agent_decisions", "ix_agent_decisions_decision_type", ["decision_type"], False),
    ("agent_decisions", "ix_agent_decisions_domain_id", ["domain_id"], False),
    ("conclusions", "ix_conclusions_disposition", ["disposition"], False),
    ("conclusions", "ix_conclusions_domain_id", ["domain_id"], False),
    ("critiques", "ix_critiques_critique_type", ["critique_type"], False),
    ("critiques", "ix_critiques_domain_id", ["domain_id"], False),
    ("critiques", "ix_critiques_target_id", ["target_id"], False),
    ("evidence", "ix_evidence_direction", ["direction"], False),
    ("evidence", "ix_evidence_domain_id", ["domain_id"], False),
    ("evidence", "ix_evidence_evidence_type", ["evidence_type"], False),
    ("evidence", "ix_evidence_experiment_result_id", ["experiment_result_id"], False),
    ("experiment_requests", "ix_experiment_requests_domain_id", ["domain_id"], False),
    ("experiment_requests", "ix_experiment_requests_status", ["status"], False),
    (
        "experiment_result_artifacts",
        "ix_experiment_result_artifacts_experiment_result_id",
        ["experiment_result_id"],
        False,
    ),
    ("experiment_results", "ix_experiment_results_domain_id", ["domain_id"], False),
    ("experiment_results", "ix_experiment_results_input_fingerprint", ["input_fingerprint"], False),
    ("experiment_results", "ix_experiment_results_output_fingerprint", ["output_fingerprint"], False),
    ("experiment_results", "ix_experiment_results_request_domain_id", ["request_domain_id"], False),
    ("experiment_results", "ix_experiment_results_request_id", ["request_id"], False),
    ("experiment_results", "ix_experiment_results_status", ["status"], False),
    ("investigation_datasets", "ix_investigation_datasets_content_hash", ["content_hash"], False),
    ("investigation_datasets", "ix_investigation_datasets_domain_id", ["domain_id"], False),
    ("investigation_state_events", "ix_investigation_state_events_entity_id", ["entity_id"], False),
    ("investigation_state_events", "ix_investigation_state_events_event_type", ["event_type"], False),
    ("investigations", "ix_investigations_analysis_run_id", ["analysis_run_id"], True),
    ("investigations", "ix_investigations_domain_id", ["domain_id"], True),
    ("investigations", "ix_investigations_initiated_by_user_id", ["initiated_by_user_id"], False),
    ("observations", "ix_observations_domain_id", ["domain_id"], False),
    ("observations", "ix_observations_entity_ref", ["entity_ref"], False),
    ("observations", "ix_observations_experiment_result_id", ["experiment_result_id"], False),
    ("observations", "ix_observations_metric_ref", ["metric_ref"], False),
    ("open_questions", "ix_open_questions_domain_id", ["domain_id"], False),
    ("open_questions", "ix_open_questions_status", ["status"], False),
    ("reproducibility_manifests", "ix_reproducibility_manifests_domain_id", ["domain_id"], False),
    ("reproducibility_manifests", "ix_reproducibility_manifests_parameters_hash", ["parameters_hash"], False),
)

#: ``(table, old_name)`` — the model declares an index on the same columns under a
#: different name, which ``_MISSING_INDEXES`` creates.
_RENAMED_INDEXES: tuple[tuple[str, str], ...] = (
    ("evidence", "ix_evidence_type"),
    ("experiment_result_artifacts", "ix_experiment_result_artifacts_result_id"),
)

#: Forward pointers ``014`` deferred to break a CREATE-time cycle.
_INVESTIGATION_FKS: tuple[tuple[str, str, str], ...] = (
    ("fk_investigations_current_conclusion_id", "current_conclusion_id", "conclusions"),
    ("fk_investigations_reproducibility_manifest_id", "reproducibility_manifest_id", "reproducibility_manifests"),
)

_INVESTIGATION_UNIQUE_CONSTRAINTS: tuple[tuple[str, list[str]], ...] = (
    ("uq_investigations_domain_id", ["domain_id"]),
    ("uq_investigations_analysis_run_id", ["analysis_run_id"]),
)


def _retype(table: str, column: str, *, to_width: int) -> None:
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            column,
            type_=sa.String(length=to_width),
            existing_type=sa.String(length=_PREVIOUS_ENUM_WIDTH),
            existing_nullable=False,
            existing_server_default=_SERVER_DEFAULTS.get((table, column)),
        )


def upgrade() -> None:
    # 1. Retire the two migration-era index names the models spell differently. Done before
    #    any rebuild so a batch copy cannot reflect and recreate a name we are dropping.
    for table, old_name in _RENAMED_INDEXES:
        op.drop_index(old_name, table_name=table)

    # 2. investigations: swap unique constraints for unique indexes, add the deferred
    #    forward-pointer FKs, and narrow ``origin`` — one batch, so SQLite rebuilds once.
    #    The unique indexes themselves are created in step 4 with the rest.
    with op.batch_alter_table("investigations") as batch_op:
        for name, _columns in _INVESTIGATION_UNIQUE_CONSTRAINTS:
            batch_op.drop_constraint(name, type_="unique")
        for name, column, target in _INVESTIGATION_FKS:
            batch_op.create_foreign_key(name, target, [column], ["id"], ondelete="SET NULL")
        batch_op.alter_column(
            "origin",
            type_=sa.String(length=13),
            existing_type=sa.String(length=_PREVIOUS_ENUM_WIDTH),
            existing_nullable=False,
        )

    # 3. Remaining enum-backed columns down to their model-computed width.
    for table, column, width in _ENUM_WIDTHS:
        if table == "investigations":
            continue  # handled in the batch above
        _retype(table, column, to_width=width)

    # 4. Indexes the ORM declares but no migration created.
    for table, name, columns, unique in _MISSING_INDEXES:
        op.create_index(name, table, columns, unique=unique)


def downgrade() -> None:
    for table, name, _columns, _unique in reversed(_MISSING_INDEXES):
        op.drop_index(name, table_name=table)

    for table, column, _width in _ENUM_WIDTHS:
        if table == "investigations":
            continue
        _retype(table, column, to_width=_PREVIOUS_ENUM_WIDTH)

    with op.batch_alter_table("investigations") as batch_op:
        batch_op.alter_column(
            "origin",
            type_=sa.String(length=_PREVIOUS_ENUM_WIDTH),
            existing_type=sa.String(length=13),
            existing_nullable=False,
        )
        for name, _column, _target in _INVESTIGATION_FKS:
            batch_op.drop_constraint(name, type_="foreignkey")
        for name, columns in _INVESTIGATION_UNIQUE_CONSTRAINTS:
            batch_op.create_unique_constraint(name, columns)

    op.create_index("ix_evidence_type", "evidence", ["evidence_type"], unique=False)
    op.create_index(
        "ix_experiment_result_artifacts_result_id",
        "experiment_result_artifacts",
        ["experiment_result_id"],
        unique=False,
    )
