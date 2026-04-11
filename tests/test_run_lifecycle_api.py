"""Cancel, retry, and GET .../status for analysis runs."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.project import Project
from backend.models.user import User


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, str]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    u = User(email=f"lc-{uuid.uuid4().hex[:8]}@example.com")
    seed.add(u)
    seed.flush()
    p = Project(owner_user_id=u.id, name="Life")
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
        yield client, project_id
    app.dependency_overrides.clear()


def _create_run(
    client: TestClient,
    project_id: str,
    *,
    enqueue: bool = False,
) -> str:
    r = client.post(
        "/v1/runs",
        json={
            "project_id": project_id,
            "orchestration_goal_text": "g",
            "input_payload_json": {"tickers": ["X"]},
            "enqueue_execution": enqueue,
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_get_status_pending(api_client: tuple[TestClient, str]) -> None:
    client, project_id = api_client
    run_id = _create_run(client, project_id, enqueue=False)
    r = client.get(f"/v1/runs/{run_id}/status")
    assert r.status_code == 200
    b = r.json()
    assert b["analysis_run_id"] == run_id
    assert b["status"] == "pending"
    assert b["is_terminal"] is False
    assert b["has_open_execution_job"] is False
    assert b["latest_execution_job"] is None


def test_cancel_pending(api_client: tuple[TestClient, str]) -> None:
    client, project_id = api_client
    run_id = _create_run(client, project_id, enqueue=False)
    r = client.post(f"/v1/runs/{run_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_queued_cancels_job(api_client: tuple[TestClient, str]) -> None:
    client, project_id = api_client
    run_id = _create_run(client, project_id, enqueue=True)
    r = client.post(f"/v1/runs/{run_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_terminal_conflict(api_client: tuple[TestClient, str]) -> None:
    client, project_id = api_client
    run_id = _create_run(client, project_id, enqueue=False)
    client.post(f"/v1/runs/{run_id}/cancel")
    r2 = client.post(f"/v1/runs/{run_id}/cancel")
    assert r2.status_code == 409
    assert "finished" in r2.json()["detail"].lower()


def test_retry_conflict_when_success(api_client: tuple[TestClient, str]) -> None:
    client, project_id = api_client
    from unittest.mock import patch

    from edgar_project.orchestration.schemas import (
        InterpretedGoal,
        InterpretedGoalCode,
        OrchestrationOutput,
        OrchestrationRunStatus,
    )

    run_id = _create_run(client, project_id, enqueue=False)

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

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult

    def _fake_traceable(_session, _analysis_run_id, _orch_in, **_: object) -> TraceableEdgarPipelineResult:
        return TraceableEdgarPipelineResult(_out(), {})

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        _fake_traceable,
    ):
        ex = client.post(f"/v1/runs/{run_id}/execute", json={})
        assert ex.status_code == 200

    r = client.post(f"/v1/runs/{run_id}/retry", json={})
    assert r.status_code == 409
    assert "cannot" in r.json()["detail"].lower() or "successful" in r.json()["detail"].lower()


def test_retry_after_error_queues_again(api_client: tuple[TestClient, str]) -> None:
    client, project_id = api_client
    from unittest.mock import patch

    from edgar_project.orchestration.schemas import (
        InterpretedGoal,
        InterpretedGoalCode,
        OrchestrationOutput,
        OrchestrationRunStatus,
    )

    run_id = _create_run(client, project_id, enqueue=False)

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

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult

    def _fake_traceable(_session, _analysis_run_id, _orch_in, **_: object) -> TraceableEdgarPipelineResult:
        return TraceableEdgarPipelineResult(_out(), {})

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        _fake_traceable,
    ):
        ex = client.post(f"/v1/runs/{run_id}/execute", json={})
        assert ex.status_code == 200

    r = client.post(f"/v1/runs/{run_id}/retry", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "queued"

    st = client.get(f"/v1/runs/{run_id}/status")
    assert st.status_code == 200
    assert st.json()["has_open_execution_job"] is True
    assert st.json()["latest_execution_job"]["status"] == "pending"


def test_status_not_found(api_client: tuple[TestClient, str]) -> None:
    client, _ = api_client
    fake = "00000000-0000-4000-8000-000000000001"
    r = client.get(f"/v1/runs/{fake}/status")
    assert r.status_code == 404
