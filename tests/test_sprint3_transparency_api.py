"""
Sprint 3 transparency: API + persistence (deterministic; no live LLM).

Covers prompt/version on model calls (see also ``test_agents_intent_planning`` for
intent/planning persistence), step transparency / phase_output projection, trace fields,
run-detail stability when toggling ``include_transparency``, evidence ids.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
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
from backend.models.enums import AnalysisRunStatus, ArtifactKind, ModelCallStatus, RunStepStatus
from backend.models.model_call import ModelCall
from backend.models.run_step import RunStep
from backend.schemas.api_phase_a import run_step_to_detail
from tests.api_auth import register_project_and_headers


@pytest.fixture
def sprint3_client() -> Iterator[tuple[TestClient, str, dict[str, str], sessionmaker[Session]]]:
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


def _create_run(client: TestClient, project_id: str, headers: dict[str, str]) -> UUID:
    r = client.post(
        "/v1/runs",
        headers=headers,
        json={
            "project_id": project_id,
            "orchestration_goal_text": "sprint3 transparency test",
            "input_payload_json": {"tickers": ["X"]},
        },
    )
    assert r.status_code == 201, r.text
    return UUID(r.json()["id"])


def test_model_call_prompt_version_exposed_on_model_calls_endpoint(
    sprint3_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = sprint3_client
    run_id = _create_run(client, project_id, headers)
    mc_id = uuid4()
    db = factory()
    try:
        db.add(
            ModelCall(
                id=mc_id,
                analysis_run_id=run_id,
                provider="stub",
                model_name="test-model",
                prompt_id="edgar.agent.critic",
                prompt_version="9.9.9",
                status=ModelCallStatus.success,
                prompt_tokens=5,
                completion_tokens=7,
                latency_ms=42,
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get(f"/v1/runs/{run_id}/model-calls", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    row = body[0]
    assert row["prompt_id"] == "edgar.agent.critic"
    assert row["prompt_version"] == "9.9.9"
    assert row["model_name"] == "test-model"
    assert row["latency_ms"] == 42
    assert row["request_payload_json"] is None
    assert row["response_payload_json"] is None


def test_run_steps_include_transparency_phase_output_and_trace(
    sprint3_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = sprint3_client
    run_id = _create_run(client, project_id, headers)
    mc_id = uuid4()
    step_id = uuid4()
    db = factory()
    try:
        db.add(
            RunStep(
                id=step_id,
                analysis_run_id=run_id,
                step_index=0,
                status=RunStepStatus.success,
                label="critic_agent",
                planned_tool_name=None,
                meta_json={
                    "trace": "critic_agent",
                    "phase": "llm",
                    "model_call_id": str(mc_id),
                    "phase_output": {
                        "phase_status": "degraded",
                        "issue_count": 2,
                        "overall_confidence": "low",
                        "weak_evidence_signals": ["flagged_issues"],
                    },
                },
            )
        )
        db.commit()
    finally:
        db.close()

    r0 = client.get(f"/v1/runs/{run_id}/steps", headers=headers)
    assert r0.status_code == 200
    assert r0.json()[0].get("transparency") is None

    r = client.get(
        f"/v1/runs/{run_id}/steps",
        params={"include_transparency": "true"},
        headers=headers,
    )
    assert r.status_code == 200
    step = r.json()[0]
    tr = step["transparency"]
    assert tr["trace"] == "critic_agent"
    assert tr["phase"] == "llm"
    assert tr["model_call_id"] == str(mc_id)
    osum = tr["output_summary"]
    assert osum["issue_count"] == 2
    assert osum["overall_confidence"] == "low"
    assert osum["phase_status"] == "degraded"
    assert osum["weak_evidence_signals"] == ["flagged_issues"]
    assert tr["linked_artifact_ids"] == []


def test_run_step_linked_artifact_ids_in_transparency(
    sprint3_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = sprint3_client
    run_id = _create_run(client, project_id, headers)
    step_id = uuid4()
    art_id = uuid4()
    db = factory()
    try:
        db.add(
            RunStep(
                id=step_id,
                analysis_run_id=run_id,
                step_index=0,
                status=RunStepStatus.success,
                planned_tool_name="run_pipeline",
                meta_json={"trace": "mcp_executor"},
            )
        )
        db.add(
            Artifact(
                id=art_id,
                analysis_run_id=run_id,
                run_step_id=step_id,
                role_key="panel_csv",
                kind=ArtifactKind.tabular,
                storage_uri="local:sprint3-test/panel.csv",
                byte_size=100,
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get(
        f"/v1/runs/{run_id}/steps",
        params={"include_transparency": "true"},
        headers=headers,
    )
    tr = r.json()[0]["transparency"]
    assert tr["linked_artifact_ids"] == [str(art_id)]
    assert tr["trace"] == "mcp_executor"
    assert r.json()[0]["planned_tool_name"] == "run_pipeline"


def test_run_detail_include_transparency_evidence_and_prompt_versions(
    sprint3_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = sprint3_client
    run_id = _create_run(client, project_id, headers)
    art_id = uuid4()
    db = factory()
    try:
        row = db.get(AnalysisRun, run_id)
        assert row is not None
        row.meta_json = {
            "ai_agents": {
                "prompt_versions": {"report": "3.1.0", "critic": "2.0.0"},
                "traceability": {
                    "evidence_artifact_ids": [str(art_id)],
                    "evidence_artifacts_by_role": {"panel_csv": str(art_id)},
                },
            },
        }
        db.add(
            ModelCall(
                id=uuid4(),
                analysis_run_id=run_id,
                provider="stub",
                model_name="m",
                prompt_id="edgar.agent.report",
                prompt_version="3.1.0",
                status=ModelCallStatus.success,
            )
        )
        db.add(
            Artifact(
                id=art_id,
                analysis_run_id=run_id,
                run_step_id=None,
                role_key="panel_csv",
                kind=ArtifactKind.tabular,
                storage_uri="local:sprint3-test/x.csv",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get(
        f"/v1/runs/{run_id}",
        params={"include_transparency": "true"},
        headers=headers,
    )
    assert r.status_code == 200
    tr = r.json()["transparency"]
    assert tr["model_call_count"] == 1
    assert tr["evidence_artifact_ids"] == [str(art_id)]
    assert tr["evidence_artifacts_by_role"] == {"panel_csv": str(art_id)}
    assert tr["prompt_versions"] == {"report": "3.1.0", "critic": "2.0.0"}


def test_run_detail_include_transparency_does_not_mutate_payload_fields(
    sprint3_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    """Richer response extends safely: same core fields when transparency is requested."""
    client, project_id, headers, factory = sprint3_client
    run_id = _create_run(client, project_id, headers)
    db = factory()
    try:
        row = db.get(AnalysisRun, run_id)
        assert row is not None
        row.output_payload_json = {"run_id": "orch-1", "status": "success"}
        row.meta_json = {"ai_agents": {"prompt_versions": {"intent": "1.0.0"}}}
        db.commit()
    finally:
        db.close()

    base = client.get(
        f"/v1/runs/{run_id}",
        params={"include_payloads": "true"},
        headers=headers,
    )
    assert base.status_code == 200
    rich = client.get(
        f"/v1/runs/{run_id}",
        params={"include_payloads": "true", "include_transparency": "true"},
        headers=headers,
    )
    assert rich.status_code == 200
    bj, rj = base.json(), rich.json()
    for key in bj:
        if key == "transparency":
            continue
        assert rj[key] == bj[key], key
    assert rj.get("transparency") is not None
    assert bj.get("transparency") is None


def test_schema_run_step_transparency_matches_orm_row() -> None:
    """Converter stays aligned with stored meta_json (regression guard)."""
    step_id = uuid4()
    run_id = uuid4()
    now = datetime.now(tz=UTC)
    row = RunStep(
        id=step_id,
        analysis_run_id=run_id,
        step_index=1,
        status=RunStepStatus.success,
        created_at=now,
        updated_at=now,
        meta_json={
            "trace": "report_agent",
            "model_call_id": str(uuid4()),
            "phase_output": {
                "key_takeaways": ["a", "b"],
                "markdown_char_count": 1200,
                "artifact_refs": [{"role": "report_md", "basename": "out.md"}],
            },
        },
    )
    item = run_step_to_detail(
        row,
        include_payloads=False,
        include_transparency=True,
        linked_artifact_ids=[],
    )
    assert item.transparency is not None
    assert item.transparency.trace == "report_agent"
    osum = item.transparency.output_summary
    assert osum is not None
    assert osum.key_takeaway_count == 2
    assert osum.markdown_char_count == 1200
    assert osum.artifact_roles == ["report_md"]
