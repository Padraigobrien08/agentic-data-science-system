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
from backend.models.project import Project
from backend.models.run_execution_job import RunExecutionJob
from backend.models.user import User
from backend.worker.loop import process_next_job
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
)


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, str, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    u = User(email=f"q-{uuid.uuid4().hex[:8]}@example.com")
    seed.add(u)
    seed.flush()
    p = Project(owner_user_id=u.id, name="QueueProj")
    seed.add(p)
    seed.commit()
    project_id = str(p.id)
    seed.close()

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, project_id, factory
    app.dependency_overrides.clear()


def test_post_run_enqueue_execution_sets_queued(api_client: tuple[TestClient, str, sessionmaker[Session]]) -> None:
    client, project_id, _factory = api_client
    r = client.post(
        "/v1/runs",
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


def test_sync_execute_returns_409_when_queued(api_client: tuple[TestClient, str, sessionmaker[Session]]) -> None:
    client, project_id, _factory = api_client
    r = client.post(
        "/v1/runs",
        json={
            "project_id": project_id,
            "orchestration_goal_text": "goal",
            "input_payload_json": {"tickers": ["MSFT"]},
            "enqueue_execution": True,
        },
    )
    run_id = r.json()["id"]
    r2 = client.post(f"/v1/runs/{run_id}/execute", json={})
    assert r2.status_code == 409


def test_worker_process_next_job_mocked(api_client: tuple[TestClient, str, sessionmaker[Session]]) -> None:
    client, project_id, factory = api_client
    r = client.post(
        "/v1/runs",
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

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_analysis_agent",
        lambda _req: _fake_out(),
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
