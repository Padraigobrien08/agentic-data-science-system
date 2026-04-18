"""Trace-summary API contract for Phase 08."""

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
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import ArtifactKind, ModelCallStatus, RunStepStatus
from backend.models.model_call import ModelCall
from backend.models.run_step import RunStep
from tests.api_auth import bootstrap_admin_and_headers, register_project_and_headers


@pytest.fixture
def trace_client() -> Iterator[tuple[TestClient, str, dict[str, str], sessionmaker[Session]]]:
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
        project_id, headers = bootstrap_admin_and_headers(client)
        yield client, project_id, headers, factory
    app.dependency_overrides.clear()


def _create_run(client: TestClient, project_id: str, headers: dict[str, str]) -> UUID:
    response = client.post(
        "/v1/runs",
        headers=headers,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "trace summary run",
            "input_payload_json": {"tickers": ["AAPL", "MSFT"]},
        },
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _seed_trace_run(factory: sessionmaker[Session], run_id: UUID) -> dict[str, UUID]:
    step_ids = {
        "step_0": uuid4(),
        "step_1": uuid4(),
        "step_2": uuid4(),
        "model_0": uuid4(),
        "model_1": uuid4(),
        "model_2": uuid4(),
        "artifact_0": uuid4(),
        "artifact_1": uuid4(),
        "artifact_2": uuid4(),
    }
    db = factory()
    try:
        run = db.get(AnalysisRun, run_id)
        assert run is not None
        run.output_payload_json = {"run_id": "orch-1", "status": "success"}
        run.meta_json = {
            "ai_agents": {
                "prompt_versions": {"report": "3.1.0", "critic": "2.0.0"},
                "traceability": {
                    "evidence_artifact_ids": [str(step_ids["artifact_0"]), str(step_ids["artifact_1"])],
                    "evidence_artifacts_by_role": {
                        "panel_csv": str(step_ids["artifact_0"]),
                        "report_md": str(step_ids["artifact_1"]),
                    },
                },
            }
        }
        db.add_all(
            [
                RunStep(
                    id=step_ids["step_0"],
                    analysis_run_id=run_id,
                    step_index=0,
                    status=RunStepStatus.success,
                    label="panel load",
                    planned_tool_name="load_panel",
                    detail="Load comparison panels",
                    planner_tool_input_json={"tickers": ["AAPL"]},
                    meta_json={
                        "trace": "mcp_executor",
                        "phase": "plan",
                        "phase_output": {"phase_status": "ok"},
                    },
                ),
                RunStep(
                    id=step_ids["step_1"],
                    analysis_run_id=run_id,
                    step_index=1,
                    status=RunStepStatus.success,
                    label="critic pass",
                    planned_tool_name=None,
                    detail="Critic reasoning",
                    planner_tool_input_json={"prompt": "critic"},
                    meta_json={
                        "trace": "critic_agent",
                        "phase": "llm",
                        "model_call_id": str(step_ids["model_1"]),
                        "phase_output": {
                            "phase_status": "degraded",
                            "issue_count": 1,
                            "overall_confidence": "low",
                        },
                    },
                ),
                RunStep(
                    id=step_ids["step_2"],
                    analysis_run_id=run_id,
                    step_index=2,
                    status=RunStepStatus.success,
                    label="report compile",
                    planned_tool_name="write_report",
                    detail="Render final report",
                    planner_tool_input_json={"format": "markdown"},
                    meta_json={
                        "trace": "mcp_executor",
                        "phase": "report",
                        "model_call_id": str(step_ids["model_2"]),
                        "phase_output": {
                            "phase_status": "ok",
                            "artifact_refs": [{"role": "report_md"}],
                        },
                    },
                ),
                ModelCall(
                    id=step_ids["model_0"],
                    analysis_run_id=run_id,
                    provider="stub",
                    model_name="planner-mini",
                    prompt_id="edgar.agent.plan",
                    prompt_version="1.0.0",
                    status=ModelCallStatus.success,
                    request_payload_json={"messages": ["plan"]},
                    response_payload_json={"result": "ok"},
                ),
                ModelCall(
                    id=step_ids["model_1"],
                    analysis_run_id=run_id,
                    provider="stub",
                    model_name="critic-mini",
                    prompt_id="edgar.agent.critic",
                    prompt_version="2.0.0",
                    status=ModelCallStatus.success,
                    request_payload_json={"messages": ["critic"]},
                    response_payload_json={"issues": 1},
                ),
                ModelCall(
                    id=step_ids["model_2"],
                    analysis_run_id=run_id,
                    provider="stub",
                    model_name="report-mini",
                    prompt_id="edgar.agent.report",
                    prompt_version="3.1.0",
                    status=ModelCallStatus.success,
                    request_payload_json={"messages": ["report"]},
                    response_payload_json={"markdown": "# Report"},
                ),
                Artifact(
                    id=step_ids["artifact_0"],
                    analysis_run_id=run_id,
                    run_step_id=step_ids["step_0"],
                    role_key="panel_csv",
                    kind=ArtifactKind.tabular,
                    storage_uri="local:trace-summary/panel.csv",
                ),
                Artifact(
                    id=step_ids["artifact_1"],
                    analysis_run_id=run_id,
                    run_step_id=step_ids["step_2"],
                    role_key="report_md",
                    kind=ArtifactKind.document,
                    storage_uri="local:trace-summary/report.md",
                ),
                Artifact(
                    id=step_ids["artifact_2"],
                    analysis_run_id=run_id,
                    run_step_id=step_ids["step_2"],
                    role_key="debug_json",
                    kind=ArtifactKind.json,
                    storage_uri="local:trace-summary/debug.json",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
    return step_ids


def test_trace_summary_route_returns_typed_preview_without_raw_payloads(
    trace_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = trace_client
    run_id = _create_run(client, project_id, headers)
    ids = _seed_trace_run(factory, run_id)

    response = client.get(
        f"/v1/runs/{run_id}/trace-summary",
        params={"steps_limit": "2", "artifacts_limit": "1", "model_calls_limit": "1"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["run"]["id"] == str(run_id)
    assert "input_payload_json" not in body["run"]
    assert "output_payload_json" not in body["run"]
    assert "meta_json" not in body["run"]
    assert body["transparency"]["model_call_count"] == 3
    assert body["transparency"]["prompt_versions"] == {"report": "3.1.0", "critic": "2.0.0"}

    assert len(body["timeline_preview"]) == 2
    assert body["timeline_preview"][0]["planner_tool_input_json"] is None
    assert body["timeline_preview"][0]["meta_json"] is None
    assert body["timeline_preview"][0]["transparency"]["trace"] == "mcp_executor"

    assert body["steps"]["total"] == 3
    assert body["steps"]["limit"] == 2
    assert body["steps"]["has_more"] is True
    assert body["steps"]["items"][1]["id"] == str(ids["step_1"])

    assert body["artifacts"]["total"] == 3
    assert body["artifacts"]["limit"] == 1
    assert body["artifacts"]["has_more"] is True
    assert body["artifacts"]["items"][0]["storage_uri"].startswith("local:")

    assert body["model_calls"]["total"] == 3
    assert body["model_calls"]["limit"] == 1
    assert body["model_calls"]["has_more"] is True
    assert body["model_calls"]["items"][0]["request_payload_json"] is None
    assert body["model_calls"]["items"][0]["response_payload_json"] is None


def test_trace_collections_support_filters_and_admin_item_payload_fetches(
    trace_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = trace_client
    run_id = _create_run(client, project_id, headers)
    ids = _seed_trace_run(factory, run_id)

    steps = client.get(
        f"/v1/runs/{run_id}/steps",
        params={
            "include_transparency": "true",
            "trace": "mcp_executor",
            "q": "report",
            "limit": "1",
            "offset": "0",
        },
        headers=headers,
    )
    assert steps.status_code == 200, steps.text
    step_rows = steps.json()
    assert len(step_rows) == 1
    assert step_rows[0]["id"] == str(ids["step_2"])
    assert step_rows[0]["transparency"]["trace"] == "mcp_executor"

    artifacts = client.get(
        f"/v1/runs/{run_id}/artifacts",
        params={"role_key": "report_md", "kind": "document", "limit": "1"},
        headers=headers,
    )
    assert artifacts.status_code == 200, artifacts.text
    artifact_rows = artifacts.json()
    assert len(artifact_rows) == 1
    assert artifact_rows[0]["id"] == str(ids["artifact_1"])

    model_calls = client.get(
        f"/v1/runs/{run_id}/model-calls",
        params={"prompt_id": "edgar.agent.critic", "q": "critic", "limit": "1"},
        headers=headers,
    )
    assert model_calls.status_code == 200, model_calls.text
    model_rows = model_calls.json()
    assert len(model_rows) == 1
    assert model_rows[0]["id"] == str(ids["model_1"])
    assert model_rows[0]["request_payload_json"] is None

    step_item = client.get(
        f"/v1/runs/{run_id}/steps/{ids['step_1']}",
        params={"include_payloads": "true", "include_transparency": "true"},
        headers=headers,
    )
    assert step_item.status_code == 200, step_item.text
    step_body = step_item.json()
    assert step_body["planner_tool_input_json"] == {"prompt": "critic"}
    assert step_body["meta_json"]["trace"] == "critic_agent"
    assert step_body["transparency"]["model_call_id"] == str(ids["model_1"])

    model_item = client.get(
        f"/v1/runs/{run_id}/model-calls/{ids['model_1']}",
        params={"include_payloads": "true"},
        headers=headers,
    )
    assert model_item.status_code == 200, model_item.text
    model_body = model_item.json()
    assert model_body["request_payload_json"] == {"messages": ["critic"]}
    assert model_body["response_payload_json"] == {"issues": 1}


def test_non_admin_owner_cannot_fetch_raw_item_payloads(
    trace_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, _, _, factory = trace_client
    project_id, headers = register_project_and_headers(client)
    run_id = _create_run(client, project_id, headers)
    ids = _seed_trace_run(factory, run_id)

    step_slim = client.get(
        f"/v1/runs/{run_id}/steps/{ids['step_0']}",
        params={"include_transparency": "true"},
        headers=headers,
    )
    assert step_slim.status_code == 200, step_slim.text
    assert step_slim.json()["planner_tool_input_json"] is None

    step_raw = client.get(
        f"/v1/runs/{run_id}/steps/{ids['step_0']}",
        params={"include_payloads": "true"},
        headers=headers,
    )
    assert step_raw.status_code == 403
    assert "Admin access required" in step_raw.json()["detail"]

    model_raw = client.get(
        f"/v1/runs/{run_id}/model-calls/{ids['model_0']}",
        params={"include_payloads": "true"},
        headers=headers,
    )
    assert model_raw.status_code == 403
    assert "Admin access required" in model_raw.json()["detail"]
