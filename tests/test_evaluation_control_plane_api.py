"""API foundation coverage for the evaluation control plane."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

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


def test_list_supported_evaluation_suites_returns_curated_ids(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, _project_id, headers, _factory = api_client

    response = client.get("/v1/evaluations/suites", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [row["suite_id"] for row in body] == [
        "suite_fixtures_v1",
        "suite_smoke",
        "suite_hybrid_smoke_v1",
    ]
    assert {row["primary_mode"] for row in body} == {"fixture", "live", "hybrid"}


def test_create_evaluation_run_resolves_curated_suite_and_lists_by_project(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, _factory = api_client

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={
            "project_id": project_id,
            "suite_id": "suite_fixtures_v1",
            "notes": "fixture eval",
            "suite_manifest_path": "/tmp/evil.json",
        },
    )
    assert created.status_code == 201, created.text
    created_body = created.json()
    assert created_body["project_id"] == project_id
    assert created_body["suite_id"] == "suite_fixtures_v1"
    assert created_body["suite_manifest_path"].endswith("suite_fixtures_v1.json")
    assert created_body["suite_manifest_path"] != "/tmp/evil.json"
    assert created_body["status"] == "pending"
    assert created_body["case_count"] == 0

    listed = client.get(f"/v1/evaluations?project_id={project_id}", headers=headers)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert len(listed_body) == 1
    assert listed_body[0]["id"] == created_body["id"]

    detail = client.get(f"/v1/evaluations/{created_body['id']}", headers=headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["id"] == created_body["id"]
    assert detail_body["case_count"] == 0


def test_unknown_suite_id_returns_400(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, _factory = api_client

    response = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "not-real"},
    )

    assert response.status_code == 400
    assert "Unsupported evaluation suite" in response.json()["detail"]


def test_evaluation_run_detail_is_owner_scoped(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, _factory = api_client
    other_project_id, other_headers = register_project_and_headers(client)

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_smoke"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = created.json()["id"]

    detail = client.get(f"/v1/evaluations/{evaluation_run_id}", headers=other_headers)
    assert detail.status_code == 404

    listed = client.get(f"/v1/evaluations?project_id={other_project_id}", headers=headers)
    assert listed.status_code == 404

    assert UUID(evaluation_run_id)
