"""Auth endpoints and cross-tenant isolation."""

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
from tests.api_auth import TEST_PASSWORD, register_project_and_headers


@pytest.fixture
def auth_api_client() -> Iterator[TestClient]:
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
        yield client
    app.dependency_overrides.clear()


def test_authenticated_access_to_protected_endpoints(auth_api_client: TestClient) -> None:
    """Bearer token allows projects and runs list (baseline happy path)."""
    client = auth_api_client
    pid, headers = register_project_and_headers(client)
    r = client.get("/v1/projects", headers=headers)
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert pid in ids

    r2 = client.get(f"/v1/projects/{pid}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["id"] == pid

    r3 = client.get("/v1/runs", params={"project_id": pid}, headers=headers)
    assert r3.status_code == 200
    assert r3.json() == []


def test_protected_endpoints_reject_unauthenticated_requests(auth_api_client: TestClient) -> None:
    client = auth_api_client
    fake_project = "00000000-0000-4000-8000-000000000002"
    fake_run = "00000000-0000-4000-8000-000000000003"
    fake_artifact = "00000000-0000-4000-8000-000000000004"
    cases: list[tuple[str, str, dict]] = [
        ("get", "/v1/projects", {}),
        ("post", "/v1/projects", {"json": {"name": "n"}}),
        ("get", "/v1/auth/me", {}),
        ("get", "/v1/runs", {}),
        ("get", f"/v1/runs/{fake_run}", {}),
        ("get", f"/v1/runs/{fake_run}/steps", {}),
        ("get", f"/v1/runs/{fake_run}/artifacts", {}),
        ("get", f"/v1/artifacts/{fake_artifact}", {}),
        ("get", f"/v1/artifacts/{fake_artifact}/content", {}),
        ("get", f"/v1/artifacts/{fake_artifact}/preview", {}),
    ]
    for method, path, kw in cases:
        r = getattr(client, method.lower())(path, **kw)
        assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


def test_invalid_bearer_token_rejected(auth_api_client: TestClient) -> None:
    client = auth_api_client
    r = client.get(
        "/v1/projects",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.invalid"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid or expired token"


def test_project_and_run_listing_scoped_to_owner(auth_api_client: TestClient) -> None:
    """Lists only own projects; foreign project_id and run_id yield 404 (no enumeration)."""
    client = auth_api_client
    pid_a, h_a = register_project_and_headers(client)
    _, h_b = register_project_and_headers(client)

    ra = client.get("/v1/projects", headers=h_a).json()
    assert len(ra) == 1 and ra[0]["id"] == pid_a

    rb = client.get("/v1/projects", headers=h_b).json()
    assert len(rb) == 1
    assert rb[0]["id"] != pid_a

    assert client.get("/v1/runs", params={"project_id": pid_a}, headers=h_b).status_code == 404

    r_run = client.post(
        "/v1/runs",
        headers=h_a,
        json={
            "project_id": pid_a,
            "orchestration_goal_text": "goal",
            "input_payload_json": {"tickers": ["X"]},
        },
    )
    assert r_run.status_code == 201
    run_id = r_run.json()["id"]
    assert client.get(f"/v1/runs/{run_id}", headers=h_b).status_code == 404


def test_register_login_me(auth_api_client: TestClient) -> None:
    client = auth_api_client
    email = "auth-me-test@example.com"
    r = client.post(
        "/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "display_name": "Me"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == email
    assert "password" not in body
    assert "hashed" not in str(body)

    r2 = client.post("/v1/auth/login", json={"email": email, "password": TEST_PASSWORD})
    assert r2.status_code == 200
    tok = r2.json()
    assert tok["token_type"] == "bearer"
    assert "access_token" in tok
    assert tok["expires_in"] > 0

    r3 = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {tok['access_token']}"},
    )
    assert r3.status_code == 200
    assert r3.json()["email"] == email


def test_login_invalid_credentials(auth_api_client: TestClient) -> None:
    client = auth_api_client
    r = client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-password-1"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


def test_register_duplicate_email(auth_api_client: TestClient) -> None:
    client = auth_api_client
    email = "dup@example.com"
    assert client.post(
        "/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    ).status_code == 201
    r2 = client.post(
        "/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert r2.status_code == 409


def test_get_project_owned_vs_other_user(auth_api_client: TestClient) -> None:
    client = auth_api_client
    pid_a, h_a = register_project_and_headers(client)
    r = client.get(f"/v1/projects/{pid_a}", headers=h_a)
    assert r.status_code == 200
    assert r.json()["id"] == pid_a

    _, h_b = register_project_and_headers(client)
    assert client.get(f"/v1/projects/{pid_a}", headers=h_b).status_code == 404


def test_cross_user_cannot_read_artifact(auth_api_client: TestClient, tmp_path) -> None:
    """Owner A can read artifact; owner B gets 404 (no id leak)."""
    from unittest.mock import patch

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult
    from edgar_project.orchestration.schemas import (
        InterpretedGoal,
        InterpretedGoalCode,
        OrchestrationOutput,
        OrchestrationRunStatus,
    )

    client = auth_api_client
    pid_a, h_a = register_project_and_headers(client)

    csv_path = tmp_path / "panel.csv"
    csv_path.write_text("c1,c2\n1,2\n", encoding="utf-8")

    def _fake_out() -> OrchestrationOutput:
        return OrchestrationOutput(
            status=OrchestrationRunStatus.success,
            message="m",
            interpreted_goal=InterpretedGoal(
                code=InterpretedGoalCode.full_pipeline,
                description="d",
                user_goal_text="g",
            ),
            artifact_paths={"panel_csv": str(csv_path)},
        )

    def _fake_traceable(_session, _analysis_run_id, _orch_in, **_: object) -> TraceableEdgarPipelineResult:
        return TraceableEdgarPipelineResult(_fake_out(), {})

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        _fake_traceable,
    ):
        r = client.post(
            "/v1/runs",
            headers=h_a,
            json={
                "project_id": pid_a,
                "orchestration_goal_text": "g",
                "input_payload_json": {"tickers": ["X"]},
            },
        )
        run_id = r.json()["id"]
        ex = client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h_a)
        assert ex.status_code == 200

    arts = client.get(f"/v1/runs/{run_id}/artifacts", headers=h_a).json()
    assert len(arts) >= 1
    art_id = arts[0]["id"]

    assert client.get(f"/v1/artifacts/{art_id}", headers=h_a).status_code == 200

    _, h_b = register_project_and_headers(client)
    r_denied = client.get(f"/v1/artifacts/{art_id}", headers=h_b)
    assert r_denied.status_code == 404

    r_content = client.get(f"/v1/artifacts/{art_id}/content", headers=h_b)
    assert r_content.status_code == 404

    r_preview = client.get(f"/v1/artifacts/{art_id}/preview", headers=h_b)
    assert r_preview.status_code == 404
