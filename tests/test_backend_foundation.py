"""
Focused, deterministic tests for backend persistence, services, storage, and HTTP API.

Uses in-memory SQLite (StaticPool for API), tmp_path for blobs, and mocked orchestration
— no live SEC or network.
"""

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

import backend.models  # noqa: F401 — register ORM metadata
from backend.config.settings import Settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.api import deps as api_deps
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind, RunStepStatus
from backend.models.project import Project
from backend.models.run_step import RunStep
from backend.models.user import User
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from backend.services.edgar_pipeline_execution_service import EdgarPipelineExecutionService
from backend.services.exceptions import InvalidStatusTransition
from backend.storage.local import LocalFilesystemStore
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
)


@pytest.fixture
def orm_session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def session_settings_artifacts(tmp_path: Path) -> Iterator[tuple[Session, Settings]]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    root = tmp_path / "blobs"
    root.mkdir()
    settings = Settings(artifact_storage_root=root)
    try:
        yield session, settings
    finally:
        session.close()


@pytest.fixture
def foundation_api_client(tmp_path: Path) -> Iterator[tuple[TestClient, str]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    u = User(email=f"fb-{uuid.uuid4().hex[:8]}@example.com")
    seed.add(u)
    seed.flush()
    p = Project(owner_user_id=u.id, name="FoundationProj")
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

    # Isolate artifact blobs from developer machine for this app instance.
    blob_root = tmp_path / "api_artifacts"
    blob_root.mkdir()
    test_settings = Settings(artifact_storage_root=blob_root)

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
        yield client, project_id
    app.dependency_overrides.clear()


# --- DB models ---


def test_db_models_create_and_relate(orm_session: Session) -> None:
    u = User(email=f"orm-{uuid.uuid4().hex[:8]}@example.com")
    orm_session.add(u)
    orm_session.flush()
    p = Project(owner_user_id=u.id, name="ORMProj")
    orm_session.add(p)
    orm_session.flush()
    run = AnalysisRun(project_id=p.id, status=AnalysisRunStatus.pending)
    orm_session.add(run)
    orm_session.flush()
    step = RunStep(
        analysis_run_id=run.id,
        step_index=0,
        status=RunStepStatus.pending,
        label="ingest",
    )
    orm_session.add(step)
    orm_session.flush()
    art = Artifact(
        analysis_run_id=run.id,
        run_step_id=step.id,
        role_key="fixture",
        kind=ArtifactKind.document,
        storage_uri="local:artifacts/analysis_runs/x/y.txt",
        mime_type="text/plain",
        byte_size=3,
        meta_json={"source": "test"},
    )
    orm_session.add(art)
    orm_session.commit()

    loaded = orm_session.get(Artifact, art.id)
    assert loaded is not None
    assert loaded.analysis_run_id == run.id
    assert loaded.run_step_id == step.id
    assert loaded.kind == ArtifactKind.document
    re_run = orm_session.get(AnalysisRun, run.id)
    assert re_run is not None
    assert len(re_run.run_steps) == 1
    assert len(re_run.artifacts) == 1


# --- Run lifecycle ---


def test_run_creation_and_status_transitions(session_settings_artifacts: tuple[Session, Settings]) -> None:
    session, _settings = session_settings_artifacts
    u = User(email=f"run-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u)
    session.flush()
    p = Project(owner_user_id=u.id, name="P")
    session.add(p)
    session.flush()
    svc = AnalysisRunService(session)
    run = svc.create(p.id, orchestration_goal_text="g", input_payload_json={"tickers": ["MSFT"]})
    session.commit()
    assert run.status == AnalysisRunStatus.pending

    svc.transition_status(run.id, AnalysisRunStatus.running)
    svc.transition_status(run.id, AnalysisRunStatus.success)
    session.commit()
    row = session.get(AnalysisRun, run.id)
    assert row is not None and row.status == AnalysisRunStatus.success
    assert row.finished_at is not None

    with pytest.raises(InvalidStatusTransition):
        svc.transition_status(run.id, AnalysisRunStatus.running)

    # Restart path after terminal non-success
    run2 = svc.create(p.id, correlation_id=f"c-{uuid.uuid4().hex[:12]}")
    session.commit()
    svc.transition_status(run2.id, AnalysisRunStatus.running)
    svc.transition_status(run2.id, AnalysisRunStatus.error)
    session.commit()
    svc.transition_status(run2.id, AnalysisRunStatus.running)
    assert session.get(AnalysisRun, run2.id).status == AnalysisRunStatus.running


# --- Artifact metadata + storage ---


def test_artifact_metadata_registration_and_load(session_settings_artifacts: tuple[Session, Settings]) -> None:
    session, settings = session_settings_artifacts
    u = User(email=f"art-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u)
    session.flush()
    p = Project(owner_user_id=u.id, name="AP")
    session.add(p)
    session.flush()
    run = AnalysisRun(project_id=p.id, status=AnalysisRunStatus.pending)
    session.add(run)
    session.flush()

    art_svc = ArtifactService(session, settings=settings)
    a = art_svc.save_bytes(
        b"payload",
        role_key="summary",
        analysis_run_id=run.id,
        filename_suffix=".txt",
        meta_json={"version": 1},
    )
    session.flush()
    assert a.role_key == "summary"
    assert a.meta_json == {"version": 1}

    art_svc.merge_meta_json(a.id, {"checksum": "abc"})
    session.commit()
    row = art_svc.get(a.id)
    assert row is not None and row.meta_json == {"version": 1, "checksum": "abc"}
    assert art_svc.load_bytes(a.id) == b"payload"


def test_local_store_put_get_roundtrip(tmp_path: Path) -> None:
    store = LocalFilesystemStore(tmp_path)
    key = "runs/0001/out.bin"
    store.put(key, b"\x00\x01\x02", content_type="application/octet-stream")
    assert store.get(key) == b"\x00\x01\x02"
    assert store.key_from_uri(store.put("a.json", b"{}", content_type="application/json").uri).endswith("a.json")


# --- API ---


def test_api_health_reports_database_ok(foundation_api_client: tuple[TestClient, str]) -> None:
    client, _ = foundation_api_client
    for path in ("/health", "/v1/health"):
        r = client.get(path)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["database"]["ok"] is True


def test_api_runs_list_unknown_project_404(foundation_api_client: tuple[TestClient, str]) -> None:
    client, _ = foundation_api_client
    bad = "00000000-0000-4000-8000-000000000099"
    r = client.get("/v1/runs", params={"project_id": bad})
    assert r.status_code == 404


def test_api_run_get_404_and_artifact_get_with_mocked_pipeline(
    foundation_api_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, project_id = foundation_api_client
    missing = "00000000-0000-4000-8000-000000000088"
    assert client.get(f"/v1/runs/{missing}").status_code == 404

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
            json={
                "project_id": project_id,
                "orchestration_goal_text": "goal",
                "input_payload_json": {"tickers": ["MSFT"]},
            },
        )
        assert r.status_code == 201
        run_id = r.json()["id"]
        ex = client.post(f"/v1/runs/{run_id}/execute", json={})
        assert ex.status_code == 200
        assert ex.json()["artifact_count"] == 1

    arts = client.get(f"/v1/runs/{run_id}/artifacts")
    assert arts.status_code == 200
    items = arts.json()
    assert len(items) == 1
    assert items[0]["role_key"] == "panel_csv"

    art_id = items[0]["id"]
    d = client.get(f"/v1/artifacts/{art_id}")
    assert d.status_code == 200
    assert d.json()["kind"] == "tabular"
    assert client.get(f"/v1/artifacts/{missing}").status_code == 404
