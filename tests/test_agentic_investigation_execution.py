"""
Wire-up tests for the flag-gated agentic investigation execution path.

Covers engine selection (default EDGAR unless flag on AND run opts in), a full
end-to-end run of the adaptive loop over an in-memory dataset persisted through the
durable investigation store, terminal status mapping, the compact output summary, and
the executable-status / worker guards. All offline and deterministic (fixture policy).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401 — register ORM metadata
from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.domain import InvestigationStatus
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus
from backend.models.investigation import Investigation as InvestigationRow
from backend.models.investigation import OrchestrationCheckpoint
from backend.models.project import Project
from backend.models.user import User
from backend.services.agentic_investigation_execution_service import (
    AgenticInvestigationExecutionService,
    ENGINE_AGENTIC,
    ENGINE_EDGAR,
    select_run_engine,
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()


def _records() -> list[dict]:
    return [{"entity": "A", "period": f"2021-{i}", "revenue": 5 + 6 * i} for i in range(8)]


def _agentic_payload(**overrides) -> dict:
    payload = {
        "engine": ENGINE_AGENTIC,
        "analysis_goal": "revenue is increasing over time",
        "dataset": {
            "adapter": "in_memory",
            "name": "rev",
            "records": _records(),
            "time_field": "period",
            "entity_id_fields": ["entity"],
        },
    }
    payload.update(overrides)
    return payload


def _seed_run(
    session: Session,
    *,
    input_payload: dict | None,
    status: AnalysisRunStatus = AnalysisRunStatus.pending,
) -> AnalysisRun:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="p")
    session.add(project)
    session.flush()
    run = AnalysisRun(
        project_id=project.id,
        initiated_by_user_id=user.id,
        status=status,
        input_payload_json=input_payload,
    )
    session.add(run)
    session.commit()
    return run


def _fixture_service(session: Session) -> AgenticInvestigationExecutionService:
    return AgenticInvestigationExecutionService(session, policy_factory=lambda s: FixtureAgentPolicy())


# --- engine selection -------------------------------------------------------


def test_flag_off_always_selects_edgar(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())
    assert select_run_engine(run, Settings(agentic_engine_enabled=False)) == ENGINE_EDGAR


def test_flag_on_with_optin_selects_agentic(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())
    assert select_run_engine(run, Settings(agentic_engine_enabled=True)) == ENGINE_AGENTIC


def test_flag_on_without_optin_selects_edgar(session: Session) -> None:
    run = _seed_run(session, input_payload={"tickers": ["AAPL"]})
    assert select_run_engine(run, Settings(agentic_engine_enabled=True)) == ENGINE_EDGAR


def test_flag_on_missing_payload_selects_edgar(session: Session) -> None:
    run = _seed_run(session, input_payload=None)
    assert select_run_engine(run, Settings(agentic_engine_enabled=True)) == ENGINE_EDGAR


# --- end-to-end execution ---------------------------------------------------


def test_execute_runs_loop_and_persists_investigation(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())

    result = _fixture_service(session).execute_analysis_run(run.id)

    # terminal, non-failed outcome mapped onto an analysis-run status
    assert result.investigation_status in (InvestigationStatus.converged, InvestigationStatus.exhausted)
    assert result.db_status in (AnalysisRunStatus.success, AnalysisRunStatus.partial_success)

    session.expire_all()
    reloaded = session.get(AnalysisRun, run.id)
    assert reloaded.status == result.db_status

    # compact summary persisted for the read-API / UI
    out = reloaded.output_payload_json
    assert out["engine"] == ENGINE_AGENTIC
    assert out["investigation_id"] == str(run.id)
    assert out["dataset"]["adapter_id"] == "in_memory"
    assert out["counts"]["hypotheses"] >= 1

    # a durable investigation was created, linked to the run/project/user, with checkpoints
    inv_row = session.scalar(select(InvestigationRow).where(InvestigationRow.domain_id == str(run.id)))
    assert inv_row is not None
    assert inv_row.analysis_run_id == run.id
    assert inv_row.project_id == run.project_id
    assert inv_row.initiated_by_user_id == run.initiated_by_user_id
    checkpoints = session.scalars(
        select(OrchestrationCheckpoint).where(OrchestrationCheckpoint.investigation_id == inv_row.id)
    ).all()
    assert len(checkpoints) >= 1


def test_execute_records_experiments_over_the_frame(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())
    result = _fixture_service(session).execute_analysis_run(run.id)
    # the loop actually ran deterministic experiments over the materialized frame
    assert result.experiments_count >= 1


# --- guards -----------------------------------------------------------------


def test_running_status_is_not_executable(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload(), status=AnalysisRunStatus.running)
    with pytest.raises(ValueError, match="already executing"):
        _fixture_service(session).execute_analysis_run(run.id)


def test_worker_execution_requires_queued(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload(), status=AnalysisRunStatus.pending)
    with pytest.raises(ValueError, match="requires status 'queued'"):
        _fixture_service(session).execute_analysis_run(run.id, from_worker=True)
