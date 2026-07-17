"""
Migration tests for 014_investigation_persistence.

The full Alembic chain is not SQLite-compatible (an earlier migration uses
constraint ALTER), so 014's DDL is tested in isolation on SQLite here (offline).
The full upgrade/downgrade chain is exercised on Postgres in
``test_investigation_persistence_postgres.py`` (skipped without a Postgres URL).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic/versions/014_investigation_persistence.py"

_INVESTIGATION_TABLES = {
    "investigations", "investigation_datasets", "hypotheses", "evidence",
    "experiment_requests", "experiment_results", "observations", "agent_decisions",
    "critiques", "open_questions", "conclusions", "reproducibility_manifests",
    "orchestration_checkpoints", "investigation_state_events",
    "evidence_hypothesis_links", "evidence_artifacts", "experiment_result_artifacts",
}


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_014", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_014_upgrade_creates_and_downgrade_drops() -> None:
    # SQLite has foreign-key enforcement off by default, so 014's FK references to
    # pre-existing tables (analysis_runs, artifacts, ...) are accepted at CREATE time.
    engine = create_engine("sqlite:///:memory:")
    mod = _load_migration()
    with engine.begin() as conn:
        ops = Operations(MigrationContext.configure(conn))
        mod.op = ops  # rebind the module-level alembic proxy to our Operations
        mod.upgrade()
        present = set(inspect(conn).get_table_names())
        assert _INVESTIGATION_TABLES.issubset(present), _INVESTIGATION_TABLES - present

        # idempotency constraint is created
        uqs = {uc["name"] for uc in inspect(conn).get_unique_constraints("experiment_results")}
        assert "uq_experiment_result_idempotency" in uqs

        mod.downgrade()
        after = set(inspect(conn).get_table_names())
        assert not (_INVESTIGATION_TABLES & after), _INVESTIGATION_TABLES & after


def test_migration_014_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "014_investigation_persistence"
    assert mod.down_revision == "013_live_hybrid_evaluation_case_run_links"
