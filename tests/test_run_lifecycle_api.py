"""Cancel, retry, and GET .../status for analysis runs."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

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


def _create_run(
    client: TestClient,
    project_id: str,
    headers: dict[str, str],
    *,
    enqueue: bool = False,
) -> str:
    r = client.post(
        "/v1/runs",
        headers=headers,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "g",
            "input_payload_json": {"tickers": ["X"]},
            "enqueue_execution": enqueue,
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


def _replace_execution_history(
    factory: sessionmaker[Session],
    run_id: str,
    *,
    run_status: AnalysisRunStatus,
    jobs: list[tuple[RunExecutionJobStatus, int, str | None]],
) -> None:
    db = factory()
    try:
        run = db.get(AnalysisRun, UUID(run_id))
        assert run is not None
        run.status = run_status
        for row in db.scalars(
            select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run.id)
        ).all():
            db.delete(row)
        for status, attempt_count, error_detail in jobs:
            db.add(
                RunExecutionJob(
                    analysis_run_id=run.id,
                    status=status,
                    attempt_count=attempt_count,
                    error_detail=error_detail,
                )
            )
        db.commit()
    finally:
        db.close()


def test_get_status_pending(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    run_id = _create_run(client, project_id, h, enqueue=False)
    r = client.get(f"/v1/runs/{run_id}/status", headers=h)
    assert r.status_code == 200
    b = r.json()
    assert b["analysis_run_id"] == run_id
    assert b["status"] == "pending"
    assert b["is_terminal"] is False
    assert b["has_open_execution_job"] is False
    assert b["latest_execution_job"] is None
    assert b["execution_job_history"] == []


def test_cancel_pending(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    run_id = _create_run(client, project_id, h, enqueue=False)
    r = client.post(f"/v1/runs/{run_id}/cancel", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_queued_cancels_job(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    run_id = _create_run(client, project_id, h, enqueue=True)
    r = client.post(f"/v1/runs/{run_id}/cancel", headers=h)
    assert r.status_code == 200


def test_cancel_terminal_conflict(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    run_id = _create_run(client, project_id, h, enqueue=False)
    client.post(f"/v1/runs/{run_id}/cancel", headers=h)
    r2 = client.post(f"/v1/runs/{run_id}/cancel", headers=h)
    assert r2.status_code == 409
    assert "finished" in r2.json()["detail"].lower()


def test_retry_conflict_when_success(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    from unittest.mock import patch

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult
    from edgar_project.orchestration.schemas import (
        InterpretedGoal,
        InterpretedGoalCode,
        OrchestrationOutput,
        OrchestrationRunStatus,
    )

    run_id = _create_run(client, project_id, h, enqueue=False)

    def _out() -> OrchestrationOutput:
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

    def _fake_traceable(_session, _analysis_run_id, _orch_in, **_: object) -> TraceableEdgarPipelineResult:
        return TraceableEdgarPipelineResult(_out(), {})

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        _fake_traceable,
    ):
        ex = client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h)
        assert ex.status_code == 200

    r = client.post(f"/v1/runs/{run_id}/retry", json={}, headers=h)
    assert r.status_code == 409
    assert "cannot" in r.json()["detail"].lower() or "successful" in r.json()["detail"].lower()


def test_retry_after_error_queues_again(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    from unittest.mock import patch

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult
    from edgar_project.orchestration.schemas import (
        InterpretedGoal,
        InterpretedGoalCode,
        OrchestrationOutput,
        OrchestrationRunStatus,
    )

    run_id = _create_run(client, project_id, h, enqueue=False)

    def _out() -> OrchestrationOutput:
        return OrchestrationOutput(
            status=OrchestrationRunStatus.error,
            message="bad",
            interpreted_goal=InterpretedGoal(
                code=InterpretedGoalCode.full_pipeline,
                description="d",
                user_goal_text="g",
            ),
            artifact_paths={},
        )

    def _fake_traceable(_session, _analysis_run_id, _orch_in, **_: object) -> TraceableEdgarPipelineResult:
        return TraceableEdgarPipelineResult(_out(), {})

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        _fake_traceable,
    ):
        ex = client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h)
        assert ex.status_code == 200

    r = client.post(f"/v1/runs/{run_id}/retry", json={}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "queued"

    st = client.get(f"/v1/runs/{run_id}/status", headers=h)
    assert st.status_code == 200
    body = st.json()
    snap = body["latest_execution_job"]
    assert body["has_open_execution_job"] is True
    assert snap["status"] == "pending"
    assert snap["attempt_count"] == 1
    assert body["execution_job_history"] == [snap]


def test_status_history_is_newest_first_and_additive(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, factory = api_client
    run_id = _create_run(client, project_id, h, enqueue=False)
    _replace_execution_history(
        factory,
        run_id,
        run_status=AnalysisRunStatus.queued,
        jobs=[
            (RunExecutionJobStatus.failed, 1, "transient failure"),
            (RunExecutionJobStatus.pending, 2, None),
        ],
    )

    r = client.get(f"/v1/runs/{run_id}/status", headers=h)
    assert r.status_code == 200
    body = r.json()

    assert body["has_open_execution_job"] is True
    assert body["latest_execution_job"]["status"] == "pending"
    assert body["latest_execution_job"]["attempt_count"] == 2
    assert [job["attempt_count"] for job in body["execution_job_history"]] == [2, 1]
    assert [job["status"] for job in body["execution_job_history"]] == ["pending", "failed"]
    assert body["execution_job_history"][0] == body["latest_execution_job"]


def test_cancelled_status_exposes_cancelled_history_without_pending_replacement(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, h, _factory = api_client
    run_id = _create_run(client, project_id, h, enqueue=True)

    cancelled = client.post(f"/v1/runs/{run_id}/cancel", headers=h)
    assert cancelled.status_code == 200

    status = client.get(f"/v1/runs/{run_id}/status", headers=h)
    assert status.status_code == 200
    body = status.json()

    assert body["status"] == "cancelled"
    assert body["has_open_execution_job"] is False
    assert body["latest_execution_job"]["status"] == "cancelled"
    assert len(body["execution_job_history"]) == 1
    assert body["execution_job_history"][0] == body["latest_execution_job"]
    assert all(job["status"] != "pending" for job in body["execution_job_history"])


def test_status_not_found(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, _, h, _factory = api_client
    fake = "00000000-0000-4000-8000-000000000001"
    r = client.get(f"/v1/runs/{fake}/status", headers=h)
    assert r.status_code == 404
