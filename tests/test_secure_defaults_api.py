"""Secure-default API regressions for ops auth and privileged expansions."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.config.settings import get_settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind, ModelCallStatus, RunStepStatus
from backend.models.model_call import ModelCall
from backend.models.project import Project
from backend.models.run_step import RunStep
from backend.models.user import User
from backend.security.passwords import hash_password
from tests.api_auth import TEST_PASSWORD, bootstrap_admin_and_headers

OPS_HEADERS = {"Authorization": "Bearer pytest-ops-token"}
WRONG_OPS_HEADERS = {"Authorization": "Bearer wrong-ops-token"}


@pytest.fixture
def secure_defaults_client_and_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "false")
    monkeypatch.setenv("EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN", "pytest-bootstrap-token")
    monkeypatch.setenv("EDGAR_BACKEND_OPS_API_TOKEN", "pytest-ops-token")
    get_settings.cache_clear()

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
        yield client, factory
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def secure_defaults_client(
    secure_defaults_client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> Iterator[TestClient]:
    client, _factory = secure_defaults_client_and_factory
    yield client


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_debug_access_fixture(
    factory: sessionmaker[Session],
    *,
    is_admin: bool,
) -> tuple[str, UUID, UUID]:
    db = factory()
    email = f"{'admin' if is_admin else 'owner'}-{uuid4().hex[:12]}@example.com"
    try:
        user = User(
            email=email,
            hashed_password=hash_password(TEST_PASSWORD),
            is_active=True,
            is_admin=is_admin,
        )
        db.add(user)
        db.flush()

        project = Project(owner_user_id=user.id, name=f"debug-project-{uuid4().hex[:6]}")
        db.add(project)
        db.flush()

        run = AnalysisRun(
            project_id=project.id,
            initiated_by_user_id=user.id,
            status=AnalysisRunStatus.success,
            orchestration_goal_text="debug goal",
            input_payload_json={"tickers": ["MSFT"]},
            output_payload_json={"status": "success"},
            meta_json={"debug": {"raw_run": True}},
        )
        db.add(run)
        db.flush()

        step = RunStep(
            analysis_run_id=run.id,
            step_index=0,
            status=RunStepStatus.success,
            planner_tool_input_json={"step": "fetch_filings"},
            meta_json={"debug": {"raw_step": True}},
        )
        db.add(step)
        db.flush()

        db.add(
            ModelCall(
                analysis_run_id=run.id,
                provider="stub",
                model_name="test-model",
                status=ModelCallStatus.success,
                request_payload_json={"messages": ["hello"]},
                response_payload_json={"output": "world"},
            )
        )
        artifact = Artifact(
            analysis_run_id=run.id,
            run_step_id=step.id,
            role_key="report_md",
            kind=ArtifactKind.document,
            storage_uri=f"local:test/{run.id}/report.md",
            meta_json={"debug": {"raw_artifact": True}},
        )
        db.add(artifact)
        db.commit()
        return email, run.id, artifact.id
    finally:
        db.close()


@pytest.mark.parametrize("path", ["/health", "/v1/health", "/ready", "/v1/ready"])
def test_public_health_routes_remain_public_under_secure_defaults(
    secure_defaults_client: TestClient,
    path: str,
) -> None:
    response = secure_defaults_client.get(path)
    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/metrics", "/v1/worker/health"])
def test_ops_routes_require_exact_ops_token_under_secure_defaults(
    secure_defaults_client: TestClient,
    path: str,
) -> None:
    response = secure_defaults_client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    wrong = secure_defaults_client.get(path, headers=WRONG_OPS_HEADERS)
    assert wrong.status_code == 401
    assert wrong.headers["www-authenticate"] == "Bearer"

    _, user_headers = bootstrap_admin_and_headers(secure_defaults_client)
    user_bearer = secure_defaults_client.get(path, headers=user_headers)
    assert user_bearer.status_code == 401
    assert user_bearer.headers["www-authenticate"] == "Bearer"

    ok = secure_defaults_client.get(path, headers=OPS_HEADERS)
    assert ok.status_code == 200


def test_non_admin_owner_cannot_request_raw_expansions(
    secure_defaults_client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = secure_defaults_client_and_factory
    email, run_id, artifact_id = _seed_debug_access_fixture(factory, is_admin=False)
    headers = _login_headers(client, email)

    assert client.get(f"/v1/runs/{run_id}", headers=headers).status_code == 200
    assert client.get(f"/v1/runs/{run_id}/steps", headers=headers).status_code == 200
    assert client.get(f"/v1/runs/{run_id}/model-calls", headers=headers).status_code == 200
    assert client.get(f"/v1/artifacts/{artifact_id}", headers=headers).status_code == 200

    assert client.get(
        f"/v1/runs/{run_id}",
        params={"include_payloads": "true"},
        headers=headers,
    ).status_code == 403
    assert client.get(
        f"/v1/runs/{run_id}/steps",
        params={"include_payloads": "true"},
        headers=headers,
    ).status_code == 403
    assert client.get(
        f"/v1/runs/{run_id}/model-calls",
        params={"include_payloads": "true"},
        headers=headers,
    ).status_code == 403
    assert client.get(
        f"/v1/artifacts/{artifact_id}",
        params={"include_meta": "true"},
        headers=headers,
    ).status_code == 403


def test_admin_owner_can_request_raw_expansions(
    secure_defaults_client_and_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = secure_defaults_client_and_factory
    email, run_id, artifact_id = _seed_debug_access_fixture(factory, is_admin=True)
    headers = _login_headers(client, email)

    run_response = client.get(
        f"/v1/runs/{run_id}",
        params={"include_payloads": "true"},
        headers=headers,
    )
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["input_payload_json"] == {"tickers": ["MSFT"]}
    assert run_body["output_payload_json"] == {"status": "success"}
    assert run_body["meta_json"] == {"debug": {"raw_run": True}}

    steps_response = client.get(
        f"/v1/runs/{run_id}/steps",
        params={"include_payloads": "true"},
        headers=headers,
    )
    assert steps_response.status_code == 200
    step_body = steps_response.json()[0]
    assert step_body["planner_tool_input_json"] == {"step": "fetch_filings"}
    assert step_body["meta_json"] == {"debug": {"raw_step": True}}

    model_calls_response = client.get(
        f"/v1/runs/{run_id}/model-calls",
        params={"include_payloads": "true"},
        headers=headers,
    )
    assert model_calls_response.status_code == 200
    model_call_body = model_calls_response.json()[0]
    assert model_call_body["request_payload_json"] == {"messages": ["hello"]}
    assert model_call_body["response_payload_json"] == {"output": "world"}

    artifact_response = client.get(
        f"/v1/artifacts/{artifact_id}",
        params={"include_meta": "true"},
        headers=headers,
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json()["meta_json"] == {"debug": {"raw_artifact": True}}
