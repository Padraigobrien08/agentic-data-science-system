"""Production-safe cancel/retry: running cancel, zombie job cleanup, attempt counter on retry."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
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
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.exceptions import RunCancelledDuringExecution
from backend.services.run_lifecycle_service import RunLifecycleService
from backend.worker.failure_classification import is_transient_pipeline_failure
from tests.api_auth import register_project_and_headers


@pytest.fixture
def api_client_and_engine() -> Iterator[tuple[TestClient, str, dict[str, str], Any]]:
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
        yield client, project_id, headers, engine
    app.dependency_overrides.clear()


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)


def _seed_running_with_job(db: Session) -> tuple[uuid.UUID, uuid.UUID]:
    uid = uuid.uuid4()
    db.add(User(id=uid, email=f"{uid.hex[:8]}@t.example", is_active=True))
    pid = uuid.uuid4()
    db.add(Project(id=pid, owner_user_id=uid, name="p"))
    rid = uuid.uuid4()
    db.add(
        AnalysisRun(
            id=rid,
            project_id=pid,
            status=AnalysisRunStatus.running,
            orchestration_goal_text="g",
            input_payload_json={"tickers": ["X"]},
        )
    )
    jid = uuid.uuid4()
    db.add(
        RunExecutionJob(
            id=jid,
            analysis_run_id=rid,
            status=RunExecutionJobStatus.running,
            attempt_count=1,
            claimed_at=None,
            lease_expires_at=None,
        )
    )
    db.commit()
    return rid, jid


def test_cancel_running_cancels_jobs_and_run(session_factory: sessionmaker[Session]) -> None:
    db = session_factory()
    try:
        rid, jid = _seed_running_with_job(db)
    finally:
        db.close()

    db2 = session_factory()
    try:
        svc = RunLifecycleService(db2)
        row = svc.cancel_analysis_run(rid)
        assert row.status == AnalysisRunStatus.cancelled
        job = db2.get(RunExecutionJob, jid)
        assert job is not None
        assert job.status == RunExecutionJobStatus.cancelled
        assert job.error_detail is not None
    finally:
        db2.close()


def test_claim_next_cleans_open_job_when_run_cancelled(session_factory: sessionmaker[Session]) -> None:
    db = session_factory()
    try:
        rid, _jid = _seed_running_with_job(db)
        run = db.get(AnalysisRun, rid)
        assert run is not None
        run.status = AnalysisRunStatus.cancelled
        db.commit()
    finally:
        db.close()

    db2 = session_factory()
    try:
        repo = RunExecutionJobRepository(db2)
        claimed = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=3)
        assert claimed is None
        job = db2.scalars(
            select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == rid)
        ).first()
        assert job is not None
        assert job.status == RunExecutionJobStatus.cancelled
        db2.commit()
    finally:
        db2.close()


def test_run_cancelled_during_execution_not_transient() -> None:
    assert is_transient_pipeline_failure(RunCancelledDuringExecution("x")) is False


def test_cancel_running_via_api(api_client_and_engine: tuple[TestClient, str, dict[str, str], Any]) -> None:
    client, project_id, h, engine = api_client_and_engine
    r = client.post(
        "/v1/runs",
        headers=h,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "g",
            "input_payload_json": {"tickers": ["X"]},
            "enqueue_execution": True,
        },
    )
    assert r.status_code == 201
    run_id = r.json()["id"]
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE analysis_runs SET status = 'running' WHERE id = :id"),
            {"id": run_id},
        )
        conn.commit()

    cr = client.post(f"/v1/runs/{run_id}/cancel", headers=h)
    assert cr.status_code == 200
    assert cr.json()["status"] == "cancelled"

    st = client.get(f"/v1/runs/{run_id}/status", headers=h)
    assert st.status_code == 200
    body = st.json()
    assert body["has_open_execution_job"] is False
    assert body["latest_execution_job"]["status"] == "cancelled"
    assert len(body["execution_job_history"]) == 1
    assert body["execution_job_history"][0] == body["latest_execution_job"]
    assert all(job["status"] != "pending" for job in body["execution_job_history"])
