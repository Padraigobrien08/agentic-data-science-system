"""Repository/service layers for analysis runs, steps, tool calls, and artifact attachment."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus, RunStepStatus, ToolCallMcpStatus
from backend.models.project import Project
from backend.models.run_execution_job import RunExecutionJob
from backend.models.user import User
from backend.repositories.analysis_run_repository import AnalysisRunRepository
from backend.repositories.artifact_repository import ArtifactRepository
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from backend.services.exceptions import InvalidStatusTransition
from backend.services.run_lifecycle_service import RunLifecycleService
from backend.services.run_queue_service import RunQueueService
from backend.services.run_step_service import RunStepService
from backend.services.tool_call_service import ToolCallService


@pytest.fixture
def session_and_settings(tmp_path) -> tuple[Session, Settings]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    root = tmp_path / "blobs"
    root.mkdir()
    settings = Settings(artifact_storage_root=root)
    return factory(), settings


@pytest.fixture
def run_bundle(
    session_and_settings: tuple[Session, Settings],
) -> tuple[Session, Settings, AnalysisRun, User, Project]:
    session, settings = session_and_settings
    u = User(email=f"x-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u)
    session.flush()
    p = Project(owner_user_id=u.id, name="P")
    session.add(p)
    session.flush()
    run_svc = AnalysisRunService(session)
    run = run_svc.create(p.id, correlation_id="corr-1", input_payload_json={"tickers": ["AAPL"]})
    session.commit()
    return session, settings, run, u, p


def test_transition_error_to_queued_clears_finished_at(run_bundle) -> None:
    session, _settings, run, _u, _p = run_bundle
    svc = AnalysisRunService(session)
    svc.transition_status(run.id, AnalysisRunStatus.running)
    svc.transition_status(run.id, AnalysisRunStatus.error)
    session.commit()
    assert session.get(AnalysisRun, run.id).finished_at is not None
    svc.transition_status(run.id, AnalysisRunStatus.queued)
    session.commit()
    row = session.get(AnalysisRun, run.id)
    assert row is not None
    assert row.status == AnalysisRunStatus.queued
    assert row.finished_at is None
    assert row.started_at is None


def test_lifecycle_cancel_running_marks_cancelled(run_bundle) -> None:
    session, _settings, run, _u, _p = run_bundle
    svc = AnalysisRunService(session)
    svc.transition_status(run.id, AnalysisRunStatus.running)
    session.commit()
    row = RunLifecycleService(session).cancel_analysis_run(run.id)
    session.commit()
    assert row.status == AnalysisRunStatus.cancelled


def test_enqueue_after_create_sets_queued_and_job(run_bundle) -> None:
    session, _settings, run, _u, _p = run_bundle
    RunQueueService(session).enqueue_after_create(run.id, {"refresh": False})
    session.commit()
    row = session.get(AnalysisRun, run.id)
    assert row is not None and row.status == AnalysisRunStatus.queued
    jobs = list(session.scalars(select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run.id)).all())
    assert len(jobs) == 1
    assert jobs[0].status == RunExecutionJobStatus.pending


def test_analysis_run_repository_list(run_bundle) -> None:
    session, _settings, run, _u, p = run_bundle
    repo = AnalysisRunRepository(session)
    assert repo.get(run.id) is not None
    assert repo.get_by_correlation_id("corr-1") is not None
    assert len(repo.list_for_project(p.id)) == 1


def test_analysis_run_error_can_restart_to_running(run_bundle) -> None:
    session, _settings, run, _u, _p = run_bundle
    svc = AnalysisRunService(session)
    svc.transition_status(run.id, AnalysisRunStatus.running)
    svc.transition_status(run.id, AnalysisRunStatus.error)
    session.commit()
    svc.transition_status(run.id, AnalysisRunStatus.running)
    row = session.get(AnalysisRun, run.id)
    assert row is not None and row.status == AnalysisRunStatus.running


def test_analysis_run_status_and_payloads(run_bundle) -> None:
    session, _settings, run, _u, _p = run_bundle
    svc = AnalysisRunService(session)
    svc.transition_status(run.id, AnalysisRunStatus.running)
    svc.merge_input_payload(run.id, {"refresh": False})
    row = session.get(AnalysisRun, run.id)
    assert row.status == AnalysisRunStatus.running
    assert row.input_payload_json == {"tickers": ["AAPL"], "refresh": False}
    svc.set_output_payload(run.id, {"ok": True})
    svc.transition_status(run.id, AnalysisRunStatus.success)
    row = session.get(AnalysisRun, run.id)
    assert row.status == AnalysisRunStatus.success
    assert row.finished_at is not None
    with pytest.raises(InvalidStatusTransition):
        svc.transition_status(run.id, AnalysisRunStatus.running)


def test_run_step_service(run_bundle) -> None:
    session, _settings, run, _u, _p = run_bundle
    steps = RunStepService(session)
    s0 = steps.create(run.id, 0, label="resolve", planned_tool_name="resolve_company")
    steps.merge_planner_tool_input(s0.id, {"ticker": "AAPL"})
    steps.transition_status(s0.id, RunStepStatus.running)
    steps.transition_status(s0.id, RunStepStatus.success)
    assert len(steps.list_for_analysis_run(run.id)) == 1
    with pytest.raises(ValueError):
        steps.create(run.id, 0, label="dup")


def test_tool_call_service(run_bundle) -> None:
    session, _settings, run, _u, _p = run_bundle
    steps = RunStepService(session)
    st = steps.create(run.id, 0, label="t")
    tc_svc = ToolCallService(session)
    tc = tc_svc.create(run.id, st.id, "resolve_company", request_params_json={"ticker": "AAPL"})
    tc_svc.start_execution(tc.id)
    tc_svc.record_response(
        tc.id,
        ToolCallMcpStatus.success,
        response_envelope_json={"status": "success", "data": {}},
    )
    row = tc_svc.require(tc.id)
    assert row.response_envelope_json is not None
    with pytest.raises(ValueError):
        tc_svc.record_response(
            tc.id,
            ToolCallMcpStatus.error,
            response_envelope_json={"x": 1},
        )
    tc_svc.record_response(
        tc.id,
        ToolCallMcpStatus.error,
        response_envelope_json={"status": "error"},
        allow_rewrite=True,
    )
    assert tc_svc.require(tc.id).mcp_status == ToolCallMcpStatus.error


def test_artifact_attach_and_repositories(run_bundle) -> None:
    session, settings, run, _u, _p = run_bundle
    steps = RunStepService(session)
    st = steps.create(run.id, 1, label="pipeline")
    art_svc = ArtifactService(session, settings=settings)
    a = art_svc.save_bytes(
        b"x",
        role_key="test",
        analysis_run_id=run.id,
        filename_suffix=".txt",
    )
    art_repo = ArtifactRepository(session)
    assert len(art_repo.list_for_analysis_run(run.id)) == 1
    art_svc.attach_to_run_step(a.id, st.id)
    session.commit()
    assert len(art_repo.list_for_run_step(st.id)) == 1
    art_svc.detach_from_run_step(a.id)
    session.commit()
    assert art_repo.get(a.id).run_step_id is None
    art_svc.merge_meta_json(a.id, {"k": 1})
    session.commit()
    assert art_repo.get(a.id).meta_json == {"k": 1}


def test_repositories_injectable_for_testing(session_and_settings) -> None:
    """Services accept repository instances (mock-friendly)."""
    session, settings = session_and_settings
    runs = AnalysisRunRepository(session)
    svc = AnalysisRunService(session, runs=runs)
    u = User(email=f"y-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u)
    session.flush()
    p = Project(owner_user_id=u.id, name="Q")
    session.add(p)
    session.flush()
    r = svc.create(p.id)
    assert runs.get(r.id) is not None
