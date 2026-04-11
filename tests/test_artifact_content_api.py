"""Artifact GET /content and GET /preview routes."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.api import deps as api_deps
from backend.config.settings import Settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.services.artifact_service import ArtifactService
from backend.services.edgar_pipeline_execution_service import EdgarPipelineExecutionService
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
)
from tests.api_auth import register_project_and_headers


@pytest.fixture
def content_api_client(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, str, dict[str, str]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    blob_root = tmp_path / "blobs"
    blob_root.mkdir()
    test_settings = Settings(artifact_storage_root=blob_root)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    def _artifact_service(db: Session = Depends(get_db)) -> ArtifactService:
        return ArtifactService(db, settings=test_settings)

    def _pipeline(db: Session = Depends(get_db)) -> EdgarPipelineExecutionService:
        return EdgarPipelineExecutionService(
            db,
            artifact_service=ArtifactService(db, settings=test_settings),
        )

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[api_deps.get_artifact_service] = _artifact_service
    app.dependency_overrides[api_deps.get_edgar_pipeline_execution_service] = _pipeline

    with TestClient(app) as client:
        project_id, headers = register_project_and_headers(client)
        yield client, project_id, headers
    app.dependency_overrides.clear()


def test_artifact_content_and_preview_404(
    content_api_client: tuple[TestClient, str, dict[str, str]],
) -> None:
    client, _, h = content_api_client
    missing = str(uuid.uuid4())
    assert client.get(f"/v1/artifacts/{missing}/content", headers=h).status_code == 404
    assert client.get(f"/v1/artifacts/{missing}/preview", headers=h).status_code == 404


def test_artifact_content_streams_csv_after_mock_execute(
    content_api_client: tuple[TestClient, str, dict[str, str]],
    tmp_path: Path,
) -> None:
    client, project_id, h = content_api_client
    csv_path = tmp_path / "panel.csv"
    csv_path.write_text("c1,c2\n1,2\n", encoding="utf-8")

    def _fake_out() -> OrchestrationOutput:
        return OrchestrationOutput(
            status=OrchestrationRunStatus.success,
            message="mock",
            interpreted_goal=InterpretedGoal(
                code=InterpretedGoalCode.full_pipeline,
                description="d",
                user_goal_text="g",
            ),
            artifact_paths={"panel_csv": str(csv_path)},
        )

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult

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
                "orchestration_goal_text": "goal",
                "input_payload_json": {"tickers": ["MSFT"]},
            },
        )
        assert r.status_code == 201
        run_id = r.json()["id"]
        ex = client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h)
        assert ex.status_code == 200

    arts = client.get(f"/v1/runs/{run_id}/artifacts", headers=h)
    art_id = arts.json()[0]["id"]

    c = client.get(f"/v1/artifacts/{art_id}/content", headers=h)
    assert c.status_code == 200
    assert b"c1,c2" in c.content
    assert c.headers.get("content-type", "").startswith("text/csv")
    cd = c.headers.get("content-disposition", "").lower()
    assert "filename=" in cd
    assert "inline" in cd  # text/* defaults to inline

    p = client.get(f"/v1/artifacts/{art_id}/preview", headers=h)
    assert p.status_code == 200
    body = p.json()
    assert body["format"] == "text"
    assert "c1,c2" in body["text"]
    assert body["truncated"] is False


def test_artifact_preview_json_format(
    content_api_client: tuple[TestClient, str, dict[str, str]],
    tmp_path: Path,
) -> None:
    client, project_id, h = content_api_client
    json_path = tmp_path / "data.json"
    json_path.write_text('{"hello": "world"}', encoding="utf-8")

    def _fake_out() -> OrchestrationOutput:
        return OrchestrationOutput(
            status=OrchestrationRunStatus.success,
            message="mock",
            interpreted_goal=InterpretedGoal(
                code=InterpretedGoalCode.full_pipeline,
                description="d",
                user_goal_text="g",
            ),
            artifact_paths={"config_json": str(json_path)},
        )

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult

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
                "orchestration_goal_text": "goal",
                "input_payload_json": {"tickers": ["MSFT"]},
            },
        )
        run_id = r.json()["id"]
        assert client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h).status_code == 200

    arts = client.get(f"/v1/runs/{run_id}/artifacts", headers=h)
    art_id = arts.json()[0]["id"]
    p = client.get(f"/v1/artifacts/{art_id}/preview", headers=h)
    assert p.status_code == 200
    body = p.json()
    assert body["format"] == "json"
    assert body["json_valid"] is True
    assert '"hello"' in body["text"]


def test_artifact_preview_415_binary(
    content_api_client: tuple[TestClient, str, dict[str, str]],
    tmp_path: Path,
) -> None:
    client, project_id, h = content_api_client
    bin_path = tmp_path / "blob.bin"
    bin_path.write_bytes(b"\x00\x01\xff")

    def _fake_out() -> OrchestrationOutput:
        return OrchestrationOutput(
            status=OrchestrationRunStatus.success,
            message="mock",
            interpreted_goal=InterpretedGoal(
                code=InterpretedGoalCode.full_pipeline,
                description="d",
                user_goal_text="g",
            ),
            artifact_paths={"raw_bin": str(bin_path)},
        )

    from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult

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
                "orchestration_goal_text": "goal",
                "input_payload_json": {"tickers": ["MSFT"]},
            },
        )
        run_id = r.json()["id"]
        assert client.post(f"/v1/runs/{run_id}/execute", json={}, headers=h).status_code == 200

    arts = client.get(f"/v1/runs/{run_id}/artifacts", headers=h)
    art_id = arts.json()[0]["id"]
    assert client.get(f"/v1/artifacts/{art_id}/preview", headers=h).status_code == 415
    down = client.get(f"/v1/artifacts/{art_id}/content", headers=h)
    assert down.status_code == 200
    assert down.content == b"\x00\x01\xff"
