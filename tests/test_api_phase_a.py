"""Phase A HTTP API (in-memory DB via dependency override)."""

from __future__ import annotations

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
from tests.api_auth import register_project_and_headers


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, str, dict[str, str]]]:
    # StaticPool: one connection so :memory: SQLite is shared across TestClient requests
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
        yield client, project_id, headers
    app.dependency_overrides.clear()


def test_root_and_v1_health(api_client: tuple[TestClient, str, dict[str, str]]) -> None:
    client, _, _ = api_client
    for path in ("/health", "/v1/health"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["database"]["ok"] is True


def test_runs_list_create_get_steps_artifacts(
    api_client: tuple[TestClient, str, dict[str, str]],
) -> None:
    client, project_id, h = api_client
    r = client.get("/v1/runs", params={"project_id": project_id}, headers=h)
    assert r.status_code == 200
    assert r.json() == []

    r_all = client.get("/v1/runs", headers=h)
    assert r_all.status_code == 200
    assert r_all.json() == []

    r = client.post(
        "/v1/runs",
        headers=h,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "find unusual changes",
            "input_payload_json": {"tickers": ["AAPL"]},
        },
    )
    assert r.status_code == 201
    run = r.json()
    run_id = run["id"]
    assert run["status"] == "pending"
    assert "input_payload_json" not in run or run.get("input_payload_json") is None

    r = client.get(f"/v1/runs/{run_id}", params={"include_payloads": "true"}, headers=h)
    assert r.status_code == 200
    detail = r.json()
    assert detail["input_payload_json"] == {"tickers": ["AAPL"]}

    r = client.get("/v1/runs", params={"project_id": project_id}, headers=h)
    assert len(r.json()) == 1

    r_all2 = client.get("/v1/runs", headers=h)
    assert len(r_all2.json()) == 1
    assert r_all2.json()[0]["id"] == run_id

    r = client.get(f"/v1/runs/{run_id}/steps", headers=h)
    assert r.status_code == 200
    assert r.json() == []

    r = client.get(f"/v1/runs/{run_id}/artifacts", headers=h)
    assert r.status_code == 200
    assert r.json() == []

    r = client.get(f"/v1/runs/{run_id}/model-calls", headers=h)
    assert r.status_code == 200
    assert r.json() == []


def test_post_execute_run_mocked(api_client: tuple[TestClient, str, dict[str, str]]) -> None:
    from unittest.mock import patch

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult
    from edgar_project.orchestration.schemas import (
        InterpretedGoal,
        InterpretedGoalCode,
        OrchestrationOutput,
        OrchestrationRunStatus,
    )

    client, project_id, h = api_client

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

    def _fake_traceable(_session, _analysis_run_id, _orch_in, **_: object) -> TraceableEdgarPipelineResult:
        return TraceableEdgarPipelineResult(_fake_out(), {})

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        _fake_traceable,
    ):
        r = client.post(
            "/v1/runs",
            headers=h,
            json={
                "project_id": project_id,
                "orchestration_goal_text": "test goal",
                "input_payload_json": {"tickers": ["AAPL"]},
            },
        )
        assert r.status_code == 201
        run_id = r.json()["id"]
        r2 = client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h)
        assert r2.status_code == 200
        body = r2.json()
        assert body["orchestration_status"] == "success"
        assert body["artifact_count"] == 0
        r3 = client.get(f"/v1/runs/{run_id}", params={"include_payloads": "true"}, headers=h)
        assert r3.json()["status"] == "success"


def test_get_artifact_404(api_client: tuple[TestClient, str, dict[str, str]]) -> None:
    client, _, h = api_client
    fake = "00000000-0000-4000-8000-000000000001"
    r = client.get(f"/v1/artifacts/{fake}", headers=h)
    assert r.status_code == 404


def test_runs_require_auth(api_client: tuple[TestClient, str, dict[str, str]]) -> None:
    client, project_id, _ = api_client
    r = client.get("/v1/runs", params={"project_id": project_id})
    assert r.status_code == 401
