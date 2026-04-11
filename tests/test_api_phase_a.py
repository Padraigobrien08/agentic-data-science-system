"""Phase A HTTP API (in-memory DB via dependency override)."""

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
    # StaticPool: one connection so :memory: SQLite is shared across TestClient requests
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    u = User(email=f"api-{uuid.uuid4().hex[:8]}@example.com")
    seed.add(u)
    seed.flush()
    p = Project(owner_user_id=u.id, name="ApiProj")
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


def test_root_and_v1_health(api_client: tuple[TestClient, str]) -> None:
    client, _ = api_client
    for path in ("/health", "/v1/health"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["database"]["ok"] is True


def test_runs_list_create_get_steps_artifacts(api_client: tuple[TestClient, str]) -> None:
    client, project_id = api_client
    r = client.get("/v1/runs", params={"project_id": project_id})
    assert r.status_code == 200
    assert r.json() == []

    r = client.post(
        "/v1/runs",
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

    r = client.get(f"/v1/runs/{run_id}", params={"include_payloads": "true"})
    assert r.status_code == 200
    detail = r.json()
    assert detail["input_payload_json"] == {"tickers": ["AAPL"]}

    r = client.get("/v1/runs", params={"project_id": project_id})
    assert len(r.json()) == 1

    r = client.get(f"/v1/runs/{run_id}/steps")
    assert r.status_code == 200
    assert r.json() == []

    r = client.get(f"/v1/runs/{run_id}/artifacts")
    assert r.status_code == 200
    assert r.json() == []


def test_post_execute_run_mocked(api_client: tuple[TestClient, str]) -> None:
    from unittest.mock import patch

    from edgar_project.orchestration.schemas import (
        InterpretedGoal,
        InterpretedGoalCode,
        OrchestrationOutput,
        OrchestrationRunStatus,
    )

    client, project_id = api_client

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
        r = client.post(
            "/v1/runs",
            json={
                "project_id": project_id,
                "orchestration_goal_text": "test goal",
                "input_payload_json": {"tickers": ["AAPL"]},
            },
        )
        assert r.status_code == 201
        run_id = r.json()["id"]
        r2 = client.post(f"/v1/runs/{run_id}/execute", json={})
        assert r2.status_code == 200
        body = r2.json()
        assert body["orchestration_status"] == "success"
        assert body["artifact_count"] == 0
        r3 = client.get(f"/v1/runs/{run_id}", params={"include_payloads": "true"})
        assert r3.json()["status"] == "success"


def test_get_artifact_404(api_client: tuple[TestClient, str]) -> None:
    client, _ = api_client
    fake = "00000000-0000-4000-8000-000000000001"
    r = client.get(f"/v1/artifacts/{fake}")
    assert r.status_code == 404
