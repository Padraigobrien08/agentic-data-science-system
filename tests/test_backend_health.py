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
from backend.models.evaluation_case_result import EvaluationCaseResult
from backend.models.evaluation_run import EvaluationRun
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


def _seed_evaluation_case_with_run(
    factory: sessionmaker[Session],
    *,
    degradation_class: str,
    metadata_json: dict[str, object],
    latest_run_status: AnalysisRunStatus,
    case_status: str = "error",
    input_mode: str = "live",
) -> None:
    db = factory()
    try:
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        evaluation_run_id = uuid.uuid4()
        analysis_run_id = uuid.uuid4()
        db.add(
            User(
                id=user_id,
                email=f"evaluation-{evaluation_run_id.hex[:8]}@example.test",
                is_active=True,
            )
        )
        project = Project(
            id=project_id,
            owner_user_id=user_id,
            name=f"evaluation-project-{evaluation_run_id.hex[:8]}",
        )
        db.add(project)
        evaluation_run = EvaluationRun(
            id=evaluation_run_id,
            project_id=project_id,
            initiated_by_user_id=user_id,
            suite_id="suite_smoke" if input_mode == "live" else "suite_hybrid_smoke_v1",
            status="running",
        )
        db.add(evaluation_run)
        child_run = AnalysisRun(
            id=analysis_run_id,
            project_id=project_id,
            initiated_by_user_id=user_id,
            status=latest_run_status,
            orchestration_goal_text="evaluation run",
            error_summary=str(metadata_json.get("analysis_run_error_summary") or "dependency degraded"),
        )
        db.add(child_run)
        db.add(
            EvaluationCaseResult(
                evaluation_run_id=evaluation_run_id,
                case_id=f"case-{analysis_run_id.hex[:8]}",
                input_mode=input_mode,
                status=case_status,
                degradation_class=degradation_class,
                run_goal="goal",
                message="dependency degraded",
                metadata_json=metadata_json,
                latest_analysis_run_id=analysis_run_id,
                latest_analysis_run_status=latest_run_status.value,
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
        assert llm["message"]
        evaluation = body["evaluation"]
        assert evaluation["state_known"] is True
        assert evaluation["sec_dependency_ok"] is True
        assert evaluation["storage_dependency_ok"] is True
        assert evaluation["recent_degraded_case_count"] == 0
        background_delivery = body["background_delivery"]
        assert background_delivery["delivery_mode"] == "sync_only"
        assert background_delivery["background_available"] is False
        assert background_delivery["detail"]


def test_health_can_report_background_delivery_ready(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _factory = client_and_factory
    monkeypatch.setenv("EDGAR_BACKEND_CHAT_FORCE_SYNCHRONOUS", "false")

    from backend.config.settings import get_settings

    get_settings.cache_clear()
    try:
        r = client.get("/v1/health")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 200
    body = r.json()
    assert body["background_delivery"]["delivery_mode"] == "background_ready"
    assert body["background_delivery"]["background_available"] is True
    assert body["background_delivery"]["detail"] is None


def test_health_can_report_background_delivery_degraded(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory = client_and_factory
    _seed_run_with_job(
        factory,
        run_status=AnalysisRunStatus.queued,
        job_status=RunExecutionJobStatus.pending,
        attempt_count=1,
    )
    monkeypatch.setenv("EDGAR_BACKEND_CHAT_FORCE_SYNCHRONOUS", "false")

    from backend.config.settings import get_settings

    get_settings.cache_clear()
    try:
        r = client.get("/v1/health")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 200
    body = r.json()
    assert body["background_delivery"]["delivery_mode"] == "background_degraded"
    assert body["background_delivery"]["background_available"] is False
    assert "queued without an active worker lease" in body["background_delivery"]["detail"]


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
    assert b"edgar_evaluation_dependency_observability_up" in r.content
    assert b"edgar_evaluation_sec_dependency_up" in r.content
    assert b"edgar_evaluation_storage_dependency_up" in r.content
    assert b"edgar_evaluation_recent_degraded_cases" in r.content


def test_worker_health_json(client_and_factory: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _factory = client_and_factory
    r = client.get("/v1/worker/health", headers=OPS_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "queue_depth" in body
    assert "jobs_running_lease_ok" in body
    assert "stale_running_jobs" in body
    assert "backlog_without_active_lease" in body
    assert "evaluation" in body
    assert body["evaluation"]["state_known"] is True


def test_health_routes_report_recent_sec_and_storage_evaluation_degradation(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = client_and_factory
    _seed_evaluation_case_with_run(
        factory,
        degradation_class="upstream_sec_degraded",
        metadata_json={"upstream_error_code": "sec_rate_limited"},
        latest_run_status=AnalysisRunStatus.error,
    )
    _seed_evaluation_case_with_run(
        factory,
        degradation_class="product_regression",
        metadata_json={"storage_error_code": "artifact_storage_unavailable"},
        latest_run_status=AnalysisRunStatus.error,
        input_mode="hybrid",
    )

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "degraded"
    assert body["evaluation"]["state_known"] is True
    assert body["evaluation"]["sec_dependency_ok"] is False
    assert body["evaluation"]["storage_dependency_ok"] is False
    assert body["evaluation"]["recent_degraded_case_count"] == 2
    assert "SEC degradation" in body["evaluation"]["detail"]
    assert "storage degradation" in body["evaluation"]["detail"]

    worker = client.get("/v1/worker/health", headers=OPS_HEADERS)
    assert worker.status_code == 200
    worker_body = worker.json()
    assert worker_body["status"] == "degraded"
    assert worker_body["evaluation"]["recent_degraded_case_count"] == 2
    assert worker_body["evaluation"]["sec_dependency_ok"] is False
    assert worker_body["evaluation"]["storage_dependency_ok"] is False


def test_health_routes_report_degraded_when_evaluation_observability_read_fails(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _factory = client_and_factory

    def _raise_scalars(self, *args, **kwargs):
        raise SQLAlchemyError("evaluation observability unavailable")

    monkeypatch.setattr("sqlalchemy.orm.session.Session.scalars", _raise_scalars)

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "degraded"
    assert body["database"]["ok"] is True
    assert body["evaluation"]["state_known"] is False
    assert body["evaluation"]["sec_dependency_ok"] is None
    assert body["evaluation"]["storage_dependency_ok"] is None
    assert body["evaluation"]["recent_degraded_case_count"] is None

    worker = client.get("/v1/worker/health", headers=OPS_HEADERS)
    assert worker.status_code == 200
    worker_body = worker.json()
    assert worker_body["status"] == "degraded"
    assert worker_body["database"]["ok"] is True
    assert worker_body["evaluation"]["state_known"] is False
    assert worker_body["evaluation"]["detail"] == "evaluation observability unavailable"


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


def test_metrics_report_evaluation_dependency_gauges_for_sec_and_storage_degradation(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = client_and_factory
    _seed_evaluation_case_with_run(
        factory,
        degradation_class="upstream_sec_degraded",
        metadata_json={"upstream_error_code": "sec_rate_limited"},
        latest_run_status=AnalysisRunStatus.error,
    )
    _seed_evaluation_case_with_run(
        factory,
        degradation_class="product_regression",
        metadata_json={"storage_error_code": "artifact_storage_unavailable"},
        latest_run_status=AnalysisRunStatus.error,
        input_mode="hybrid",
    )

    response = client.get("/metrics", headers=OPS_HEADERS)

    assert response.status_code == 200
    payload = response.text
    assert _metric_value(payload, "edgar_evaluation_dependency_observability_up") == 1.0
    assert _metric_value(payload, "edgar_evaluation_sec_dependency_up") == 0.0
    assert _metric_value(payload, "edgar_evaluation_storage_dependency_up") == 0.0
    assert _metric_value(payload, "edgar_evaluation_recent_degraded_cases") == 2.0


def test_metrics_report_degraded_evaluation_observability_with_nan_unknown_values(
    client_and_factory: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _factory = client_and_factory

    def _raise_scalars(self, *args, **kwargs):
        raise SQLAlchemyError("evaluation observability unavailable")

    monkeypatch.setattr("sqlalchemy.orm.session.Session.scalars", _raise_scalars)

    response = client.get("/metrics", headers=OPS_HEADERS)

    assert response.status_code == 200
    payload = response.text
    assert _metric_value(payload, "edgar_evaluation_dependency_observability_up") == 0.0
    assert math.isnan(_metric_value(payload, "edgar_evaluation_sec_dependency_up"))
    assert math.isnan(_metric_value(payload, "edgar_evaluation_storage_dependency_up"))
    assert math.isnan(_metric_value(payload, "edgar_evaluation_recent_degraded_cases"))
