"""HTTP read-API for the generalized investigation model (owner-scoped, in-memory DB)."""

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
from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.domain.examples import example_investigation
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.services.agentic_investigation_execution_service import AgenticInvestigationExecutionService
from tests.api_auth import bootstrap_admin_and_headers, register_project_and_headers


@pytest.fixture
def api_ctx() -> Iterator[tuple[TestClient, str, dict[str, str], sessionmaker[Session]]]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
        project_id, headers = bootstrap_admin_and_headers(client)
        yield client, project_id, headers, factory
    app.dependency_overrides.clear()


def _seed_example(factory: sessionmaker[Session], project_id: str) -> str:
    s = factory()
    row = SqlAlchemyInvestigationRepository(s).create(example_investigation(), project_id=UUID(project_id))
    s.commit()
    inv_id = str(row.id)
    s.close()
    return inv_id


def _seed_agentic_run(factory: sessionmaker[Session], project_id: str) -> str:
    s = factory()
    run = AnalysisRun(
        project_id=UUID(project_id),
        status=AnalysisRunStatus.pending,
        input_payload_json={
            "engine": "agentic",
            "analysis_goal": "revenue is increasing over time",
            "dataset": {
                "adapter": "in_memory",
                "name": "rev",
                "records": [{"entity": "A", "period": f"2021-{i}", "revenue": 5 + 6 * i} for i in range(8)],
                "time_field": "period",
                "entity_id_fields": ["entity"],
            },
        },
    )
    s.add(run)
    s.commit()
    run_id = run.id
    AgenticInvestigationExecutionService(s, policy_factory=lambda st: FixtureAgentPolicy()).execute_analysis_run(run_id)
    s.close()
    return str(run_id)


# --- list -------------------------------------------------------------------


def test_list_empty(api_ctx) -> None:
    client, project_id, h, _ = api_ctx
    r = client.get("/v1/investigations", params={"project_id": project_id}, headers=h)
    assert r.status_code == 200
    assert r.json() == []


def test_list_returns_seeded_summary(api_ctx) -> None:
    client, project_id, h, factory = api_ctx
    inv_id = _seed_example(factory, project_id)

    r = client.get("/v1/investigations", params={"project_id": project_id}, headers=h)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    item = items[0]
    assert item["id"] == inv_id
    assert item["objective"]
    assert item["counts"]["hypotheses"] == 1
    assert item["counts"]["evidence"] == 1

    # unscoped listing also finds it (owned via the project)
    r_all = client.get("/v1/investigations", headers=h)
    assert r_all.status_code == 200
    assert [i["id"] for i in r_all.json()] == [inv_id]


# --- detail -----------------------------------------------------------------


def test_detail_projects_full_state(api_ctx) -> None:
    client, project_id, h, factory = api_ctx
    inv_id = _seed_example(factory, project_id)

    r = client.get(f"/v1/investigations/{inv_id}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == inv_id
    assert len(body["hypotheses"]) == 1
    assert len(body["evidence"]) == 1
    assert body["conclusion_detail"] is not None
    assert body["evidence"][0]["hypothesis_ids"]  # evidence↔hypothesis link surfaced
    assert isinstance(body["events"], list) and len(body["events"]) >= 1


def test_detail_from_agentic_run_end_to_end(api_ctx) -> None:
    client, project_id, h, factory = api_ctx
    run_id = _seed_agentic_run(factory, project_id)

    # the list carries analysis_run_id, so a client maps a run to its investigation
    listed = client.get("/v1/investigations", params={"project_id": project_id}, headers=h).json()
    match = next(i for i in listed if i["analysis_run_id"] == run_id)

    r = client.get(f"/v1/investigations/{match['id']}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_run_id"] == run_id
    assert body["status"] in ("converged", "exhausted")
    assert len(body["experiments"]) >= 1
    assert len(body["decisions"]) >= 1
    assert body["conclusion_detail"]["disposition"] == "supported"


# --- ownership --------------------------------------------------------------


def test_other_user_cannot_read_investigation(api_ctx) -> None:
    client, project_id, _, factory = api_ctx
    inv_id = _seed_example(factory, project_id)

    _, other_headers = register_project_and_headers(client)
    r = client.get(f"/v1/investigations/{inv_id}", headers=other_headers)
    assert r.status_code == 404

    r_list = client.get("/v1/investigations", headers=other_headers)
    assert r_list.status_code == 200
    assert r_list.json() == []


def test_unknown_investigation_is_404(api_ctx) -> None:
    client, _, h, _ = api_ctx
    r = client.get("/v1/investigations/00000000-0000-0000-0000-000000000000", headers=h)
    assert r.status_code == 404
