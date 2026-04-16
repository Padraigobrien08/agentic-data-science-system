"""Async run queue: enqueue on create, worker loop, sync /execute conflict with ``queued``."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob
from backend.worker.loop import process_next_job
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
)
from tests.api_auth import register_project_and_headers


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, str, dict[str, str], sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        project_id, headers = register_project_and_headers(client)
        yield client, project_id, headers, factory
    app.dependency_overrides.clear()


def test_post_run_enqueue_execution_sets_queued(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, factory = api_client
    r = client.post(
        "/v1/runs",
        headers=h,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "goal",
            "input_payload_json": {"tickers": ["MSFT"]},
            "enqueue_execution": True,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "queued"

    db = factory()
    try:
        run_row = db.get(AnalysisRun, uuid.UUID(body["id"]))
        assert run_row is not None
        job = db.scalars(
            select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_row.id)
        ).first()
        assert job is not None
        assert job.status == RunExecutionJobStatus.pending
        assert job.attempt_count == 1
    finally:
        db.close()


def test_enqueue_persists_w3c_trace_context_for_worker(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    """Queued jobs store traceparent so the worker can continue the API trace."""
    client, project_id, h, factory = api_client
    r = client.post(
        "/v1/runs",
        headers=h,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "goal",
            "input_payload_json": {"tickers": ["MSFT"]},
            "enqueue_execution": True,
        },
    )
    assert r.status_code == 201
    run_uuid = uuid.UUID(r.json()["id"])
    db = factory()
    try:
        job = db.scalars(
            select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_uuid).limit(1)
        ).first()
        assert job is not None
        assert isinstance(job.trace_context_json, dict)
        assert "traceparent" in job.trace_context_json
        assert job.trace_context_json["traceparent"].startswith("00-")
    finally:
        db.close()


def test_sync_execute_returns_409_when_queued(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    r = client.post(
        "/v1/runs",
        headers=h,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "goal",
            "input_payload_json": {"tickers": ["MSFT"]},
            "enqueue_execution": True,
        },
    )
    run_id = r.json()["id"]
    r2 = client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h)
    assert r2.status_code == 409


def test_worker_process_next_job_mocked(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, factory = api_client
    r = client.post(
        "/v1/runs",
        headers=h,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "goal",
            "input_payload_json": {"tickers": ["MSFT"]},
            "enqueue_execution": True,
        },
    )
    run_id = r.json()["id"]

    def _fake_out() -> OrchestrationOutput:
        return OrchestrationOutput(
            status=OrchestrationRunStatus.success,
            message="ok",
            interpreted_goal=InterpretedGoal(
                code=InterpretedGoalCode.full_pipeline,
                description="d",
                user_goal_text="g",
            ),
            artifact_paths={},
        )

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult

    def _fake_traceable(_session, _analysis_run_id, _orch_in, **_: object) -> TraceableEdgarPipelineResult:
        return TraceableEdgarPipelineResult(_fake_out(), {})

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        _fake_traceable,
    ):
        assert process_next_job(factory) is True

    s = factory()
    try:
        run_row = s.get(AnalysisRun, uuid.UUID(run_id))
        assert run_row is not None
        assert run_row.status == AnalysisRunStatus.success
        jobs = list(
            s.scalars(
                select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_row.id),
            ).all()
        )
        assert len(jobs) == 1
        assert jobs[0].status == RunExecutionJobStatus.completed
    finally:
        s.close()
