"""
Postgres integration tests for investigation persistence.

Skipped unless ``EDGAR_TEST_POSTGRES_URL`` is set (runs in the dedicated Postgres
CI job). Covers repository behavior on real Postgres plus the full Alembic
upgrade→downgrade→upgrade chain, asserting existing run tables are preserved.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.pool import NullPool

# Reuse the module-scoped Postgres database fixture (creates + create_all + drops).
from tests.postgres_queue_test_utils import postgres_session_factory, postgres_test_url  # noqa: F401

import backend.models  # noqa: F401
from backend.models.investigation import Investigation
from backend.repositories.investigation_repository import (
    InvestigationConcurrencyError,
    SqlAlchemyInvestigationRepository,
)
from agentic.domain import ExperimentResult, ExperimentStatus, Provenance, ProvenanceSource
from agentic.domain.examples import example_investigation

REPO_ROOT = Path(__file__).resolve().parents[1]
_INVESTIGATION_TABLES = {
    "investigations", "experiment_results", "orchestration_checkpoints", "investigation_state_events",
}


@pytest.fixture
def pg_session(postgres_session_factory: sessionmaker[Session]) -> Iterator[Session]:
    s = postgres_session_factory()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _tool_prov() -> Provenance:
    return Provenance(source=ProvenanceSource.deterministic_tool, tool_name="t", tool_version="1")


def test_pg_create_and_resume_exact(pg_session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(pg_session)
    inv = example_investigation()
    row = repo.create(inv)
    pg_session.commit()
    restored = repo.load_domain(row.id)
    assert restored.model_dump(mode="json") == inv.model_dump(mode="json")


def test_pg_experiment_recording_idempotent(pg_session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(pg_session)
    row = repo.create(example_investigation())
    pg_session.commit()
    result = ExperimentResult(request_id="r", tool_name="t", status=ExperimentStatus.succeeded, provenance=_tool_prov())
    r1, c1 = repo.record_experiment_result(row.id, result=result, idempotency_key="k1")
    pg_session.commit()
    r2, c2 = repo.record_experiment_result(row.id, result=result, idempotency_key="k1")
    pg_session.commit()
    assert c1 is True and c2 is False and r1.id == r2.id


def test_pg_optimistic_concurrency(postgres_session_factory: sessionmaker[Session]) -> None:
    s0 = postgres_session_factory()
    repo = SqlAlchemyInvestigationRepository(s0)
    row = repo.create(example_investigation())
    s0.commit()
    inv_id = row.id
    s0.close()

    sa, sb = postgres_session_factory(), postgres_session_factory()
    a = sa.get(Investigation, inv_id)
    b = sb.get(Investigation, inv_id)
    a.status = "running"
    sa.commit()
    b.status = "failed"
    with pytest.raises(StaleDataError):
        sb.commit()
    sa.close()
    sb.close()


def test_pg_explicit_stale_version(pg_session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(pg_session)
    row = repo.create(example_investigation())
    pg_session.commit()
    inv = repo.load_domain(row.id)
    with pytest.raises(InvestigationConcurrencyError):
        repo.save_state(row.id, inv, expected_state_version=row.state_version - 1)


# --- full-chain migration upgrade / downgrade -------------------------------


def _run_alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        EDGAR_BACKEND_DATABASE_URL=url,
        EDGAR_BACKEND_ALLOW_SQLITE="false",
        EDGAR_BACKEND_JWT_SECRET="pytest-jwt-secret-minimum-32-characters-long-x",
        EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION="true",
        EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN="t",
        EDGAR_BACKEND_OPS_API_TOKEN="t",
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, check=True,
    )


def test_pg_full_migration_upgrade_downgrade() -> None:
    admin_url = make_url(postgres_test_url())
    db_name = f"edgar_mig_{uuid.uuid4().hex[:12]}"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    target_url = admin_url.set(database=db_name).render_as_string(hide_password=False)
    engine = create_engine(target_url, poolclass=NullPool)
    try:
        _run_alembic(target_url, "upgrade", "head")
        tables = set(inspect(engine).get_table_names())
        assert _INVESTIGATION_TABLES.issubset(tables)
        assert "analysis_runs" in tables  # existing runs table preserved

        _run_alembic(target_url, "downgrade", "013_live_hybrid_evaluation_case_run_links")
        after = set(inspect(engine).get_table_names())
        assert not (_INVESTIGATION_TABLES & after)   # investigation tables dropped
        assert "analysis_runs" in after              # existing runs table NOT removed

        _run_alembic(target_url, "upgrade", "head")  # re-upgrade is clean
        assert _INVESTIGATION_TABLES.issubset(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :n"
            ), {"n": db_name})
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin.dispose()
