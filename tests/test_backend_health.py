"""Smoke tests for the FastAPI app (package ``backend`` at repo root).

Run ``alembic upgrade head`` first so the default SQLite DB exists and
``GET /v1/health`` can execute ``SELECT 1``.
"""

from __future__ import annotations

import math
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
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

OPS_HEADERS = {"Authorization": "Bearer pytest-ops-token"}


@pytest.fixture
def client_and_factory() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()


def _seed_run_with_job(
    factory: sessionmaker[Session],
    *,
    run_status: AnalysisRunStatus,
    job_status: RunExecutionJobStatus,
    attempt_count: int,
    lease_expires_at=None,
) -> None:
    db = factory()
    try:
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        run_id = uuid.uuid4()
        db.add(
            User(
                id=user_id,
                email=f"user-{attempt_count}-{job_status.value}-{user_id.hex[:8]}@example.test",
                is_active=True,
            )
        )
        project = Project(
            id=project_id,
            owner_user_id=user_id,
            name=f"project-{attempt_count}-{job_status.value}",
        )
        db.add(project)
        run = AnalysisRun(
            id=run_id,
            project_id=project.id,
            status=run_status,
            orchestration_goal_text="goal",
            input_payload_json={"tickers": ["MSFT"]},
        )
        db.add(run)
        db.add(
            RunExecutionJob(
                analysis_run_id=run.id,
                status=job_status,
                attempt_count=attempt_count,
                lease_expires_at=lease_expires_at,
            )
        )
        db.commit()
    finally:
        db.close()


def _metric_value(payload: str, metric_name: str) -> float:
    prefix = f"{metric_name} "
    for line in payload.splitlines():
        if line.startswith(prefix):
            return float(line.split()[-1])
    raise AssertionError(f"Metric {metric_name} missing from /metrics output")


def test_health_returns_ok_and_version(client_and_factory: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _factory = client_and_factory
    for path in ("/health", "/v1/health"):
        r = client.get(path)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["version"]
        assert body["database"]["ok"] is True
        assert "llm" in body
        llm = body["llm"]
        assert llm["provider"] in ("off", "openai")
        assert isinstance(llm["ready"], bool)
        assert llm["message"]  # never null — explains status or confirms ready


def test_ready_returns_ready_when_db_ok(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = client_and_factory
    for path in ("/ready", "/v1/ready"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["status"] == "ready"


@pytest.mark.parametrize("path", ["/metrics", "/v1/worker/health"])
def test_ops_routes_require_ops_bearer_token(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
    path: str,
) -> None:
    client, _factory = client_and_factory
    r = client.get(path)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert r.json()["detail"] == "Not authenticated"


def test_metrics_prometheus_text(client_and_factory: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _factory = client_and_factory
    r = client.get("/metrics", headers=OPS_HEADERS)
    assert r.status_code == 200
    assert b"edgar_http_requests_total" in r.content
    assert b"edgar_worker_queue_depth" in r.content
    assert b"edgar_worker_queue_pending_claimable" in r.content
    assert b"edgar_worker_last_terminal_job_unixtime" in r.content


def test_worker_health_json(client_and_factory: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _factory = client_and_factory
    r = client.get("/v1/worker/health", headers=OPS_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "queue_depth" in body
    assert "jobs_running_lease_ok" in body
    assert "stale_running_jobs" in body
    assert "backlog_without_active_lease" in body


def test_worker_health_reports_degraded_when_queue_observability_read_fails(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _factory = client_and_factory

    def _raise_queue_read_error(self, *, max_attempts: int):
        raise SQLAlchemyError("queue observability unavailable")

    monkeypatch.setattr(
        "backend.repositories.run_execution_job_repository.RunExecutionJobRepository.queue_observability_snapshot",
        _raise_queue_read_error,
    )

    response = client.get("/v1/worker/health", headers=OPS_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"]["ok"] is False
    assert body["queue_state_known"] is False
    assert body["queue_depth"] is None
    assert body["backlog_without_active_lease"] is None


def test_worker_health_counts_final_allowed_attempt_and_stale_running_truthfully(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    from datetime import datetime, timedelta, timezone

    client, factory = client_and_factory
    _seed_run_with_job(
        factory,
        run_status=AnalysisRunStatus.queued,
        job_status=RunExecutionJobStatus.pending,
        attempt_count=4,
    )
    _seed_run_with_job(
        factory,
        run_status=AnalysisRunStatus.running,
        job_status=RunExecutionJobStatus.running,
        attempt_count=1,
        lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=30),
    )

    health = client.get("/v1/worker/health", headers=OPS_HEADERS)
    assert health.status_code == 200
    body = health.json()
    assert body["queue_depth"] == 1
    assert body["jobs_running_lease_ok"] == 0
    assert body["jobs_running_stale_lease"] == 1
    assert body["stale_running_jobs"] is True
    assert body["backlog_without_active_lease"] is True

    metrics = client.get("/metrics", headers=OPS_HEADERS)
    assert metrics.status_code == 200
    payload = metrics.text
    assert _metric_value(payload, "edgar_worker_queue_depth") == 1.0
    assert _metric_value(payload, "edgar_worker_queue_pending_claimable") == 1.0
    assert _metric_value(payload, "edgar_worker_queue_jobs_running_stale_lease") == 1.0
    assert _metric_value(payload, "edgar_worker_queue_jobs_running_lease_ok") == 0.0


def test_worker_health_ignores_exhausted_attempts_and_active_lease_blocks_backlog_flag(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    from datetime import datetime, timedelta, timezone

    client, factory = client_and_factory
    _seed_run_with_job(
        factory,
        run_status=AnalysisRunStatus.queued,
        job_status=RunExecutionJobStatus.pending,
        attempt_count=5,
    )
    _seed_run_with_job(
        factory,
        run_status=AnalysisRunStatus.queued,
        job_status=RunExecutionJobStatus.pending,
        attempt_count=4,
    )
    _seed_run_with_job(
        factory,
        run_status=AnalysisRunStatus.running,
        job_status=RunExecutionJobStatus.running,
        attempt_count=1,
        lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
    )

    health = client.get("/v1/worker/health", headers=OPS_HEADERS)
    assert health.status_code == 200
    body = health.json()
    assert body["queue_depth"] == 1
    assert body["jobs_running_lease_ok"] == 1
    assert body["jobs_running_stale_lease"] == 0
    assert body["stale_running_jobs"] is False
    assert body["backlog_without_active_lease"] is False

    metrics = client.get("/metrics", headers=OPS_HEADERS)
    assert metrics.status_code == 200
    payload = metrics.text
    assert _metric_value(payload, "edgar_worker_queue_depth") == 1.0
    assert _metric_value(payload, "edgar_worker_queue_pending_claimable") == 1.0
    assert _metric_value(payload, "edgar_worker_queue_jobs_running_lease_ok") == 1.0
    assert _metric_value(payload, "edgar_worker_queue_jobs_running_stale_lease") == 0.0


def test_metrics_report_degraded_queue_observability_with_nan_unknown_values(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _factory = client_and_factory

    def _raise_queue_read_error(self, *, max_attempts: int):
        raise SQLAlchemyError("queue observability unavailable")

    monkeypatch.setattr(
        "backend.repositories.run_execution_job_repository.RunExecutionJobRepository.queue_observability_snapshot",
        _raise_queue_read_error,
    )

    response = client.get("/metrics", headers=OPS_HEADERS)

    assert response.status_code == 200
    payload = response.text
    assert _metric_value(payload, "edgar_worker_queue_observability_up") == 0.0
    assert math.isnan(_metric_value(payload, "edgar_worker_queue_depth"))
    assert math.isnan(_metric_value(payload, "edgar_worker_last_terminal_job_unixtime"))
