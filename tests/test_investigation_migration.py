"""
Migration tests for 014_investigation_persistence.

Exercises 014's DDL in isolation on SQLite, so a failure points at this revision rather
than at the chain. The whole chain now runs on SQLite too — see
``test_migration_metadata_parity.py`` — and on Postgres in
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


def _revision_ids() -> list[str]:
    import re

    ids: list[str] = []
    for path in (Path(__file__).resolve().parents[1] / "alembic/versions").glob("*.py"):
        m = re.search(r'^revision:\s*str\s*=\s*"([^"]+)"', path.read_text(), re.M)
        if m:
            ids.append(m.group(1))
    return ids


def test_env_widens_version_table_for_long_revision_ids() -> None:
    """
    Guard: several revision ids exceed alembic's default ``version_num`` width
    (VARCHAR(32)); ``alembic/env.py`` must pre-create a wider ``alembic_version``
    so a fresh ``alembic upgrade head`` (the Compose ``migrate`` service) works.
    """
    ids = _revision_ids()
    assert ids, "no revision ids found"
    longest = max(len(r) for r in ids)
    assert longest > 32, "test premise changed: no long revision ids remain"

    env_src = (Path(__file__).resolve().parents[1] / "alembic/env.py").read_text()
    assert "_ensure_wide_version_table" in env_src
    # the ensured width must accommodate the longest revision id
    import re

    width = int(re.search(r"version_num VARCHAR\((\d+)\)", env_src).group(1))
    assert width >= longest

    # the ensured DDL actually stores the longest id (SQLite proxy for any backend)
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite:///:memory:")
    longest_id = max(ids, key=len)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            f"CREATE TABLE alembic_version (version_num VARCHAR({width}) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": longest_id})
        stored = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert stored == longest_id
