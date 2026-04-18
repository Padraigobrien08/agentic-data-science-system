"""API foundation coverage for the evaluation control plane."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.evaluation_case_result import EvaluationCaseResult
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


def test_start_fixture_evaluation_run_persists_case_rows(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = api_client

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_fixtures_v1"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = created.json()["id"]

    started = client.post(
        f"/v1/evaluations/{evaluation_run_id}/start",
        headers=headers,
        json={},
    )
    assert started.status_code == 200, started.text
    started_body = started.json()
    assert started_body["status"] == "passed"
    assert started_body["case_count"] == 5

    with factory() as db:
        case_rows = list(
            db.scalars(
                select(EvaluationCaseResult).where(
                    EvaluationCaseResult.evaluation_run_id == UUID(evaluation_run_id)
                )
            ).all()
        )
    assert len(case_rows) == 5


def test_start_live_evaluation_run_without_allow_live_persists_policy_skipped_case(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = api_client

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_smoke"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = created.json()["id"]

    started = client.post(
        f"/v1/evaluations/{evaluation_run_id}/start",
        headers=headers,
        json={},
    )
    assert started.status_code == 200, started.text
    started_body = started.json()
    assert started_body["status"] == "skipped"
    assert started_body["case_count"] == 1

    with factory() as db:
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == UUID(evaluation_run_id)
            )
        )
    assert case_row is not None
    assert case_row.degradation_class == "policy_skipped"
    assert case_row.policy_json is not None


def test_start_hybrid_evaluation_run_with_allow_live_persists_case_and_policy_metadata(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = api_client

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_hybrid_smoke_v1"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = created.json()["id"]

    started = client.post(
        f"/v1/evaluations/{evaluation_run_id}/start",
        headers=headers,
        json={"allow_live": True},
    )
    assert started.status_code == 200, started.text
    started_body = started.json()
    assert started_body["status"] == "skipped"
    assert started_body["case_count"] == 1

    with factory() as db:
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == UUID(evaluation_run_id)
            )
        )
    assert case_row is not None
    assert case_row.input_mode == "hybrid"
    assert case_row.policy_json is not None
    assert case_row.observation_json is not None
    assert case_row.observation_json["freshness_window_seconds"] == 300


def test_start_route_returns_409_for_non_pending_evaluation_run(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, _factory = api_client

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_smoke"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = created.json()["id"]

    first = client.post(
        f"/v1/evaluations/{evaluation_run_id}/start",
        headers=headers,
        json={},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"/v1/evaluations/{evaluation_run_id}/start",
        headers=headers,
        json={},
    )
    assert second.status_code == 409


def test_list_fixture_case_results_and_reopen_one_case(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, _factory = api_client

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_fixtures_v1"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = created.json()["id"]

    started = client.post(
        f"/v1/evaluations/{evaluation_run_id}/start",
        headers=headers,
        json={},
    )
    assert started.status_code == 200, started.text

    listed = client.get(
        f"/v1/evaluations/{evaluation_run_id}/cases?input_mode=fixture",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    listed_body = listed.json()
    assert len(listed_body) == 5
    assert {row["input_mode"] for row in listed_body} == {"fixture"}

    case_id = listed_body[0]["case_id"]
    detail = client.get(
        f"/v1/evaluations/{evaluation_run_id}/cases/{case_id}",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["case_id"] == case_id
    assert detail_body["checks_json"] is not None


def test_filter_policy_skipped_case_results_and_enforce_owner_scope(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, _factory = api_client
    _other_project_id, other_headers = register_project_and_headers(client)

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_smoke"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = created.json()["id"]

    started = client.post(
        f"/v1/evaluations/{evaluation_run_id}/start",
        headers=headers,
        json={},
    )
    assert started.status_code == 200, started.text

    filtered = client.get(
        f"/v1/evaluations/{evaluation_run_id}/cases?degradation_class=policy_skipped",
        headers=headers,
    )
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    assert len(filtered_body) == 1
    assert filtered_body[0]["degradation_class"] == "policy_skipped"
    assert filtered_body[0]["policy_json"] is not None
    case_id = filtered_body[0]["case_id"]

    other_list = client.get(
        f"/v1/evaluations/{evaluation_run_id}/cases",
        headers=other_headers,
    )
    assert other_list.status_code == 404

    other_detail = client.get(
        f"/v1/evaluations/{evaluation_run_id}/cases/{case_id}",
        headers=other_headers,
    )
    assert other_detail.status_code == 404
