"""Tests for object storage + :class:`~backend.services.artifact_service.ArtifactService`."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401 — register metadata
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, ArtifactKind
from backend.models.project import Project
from backend.models.user import User
from backend.services.artifact_service import ArtifactService, infer_artifact_kind_and_mime
from backend.storage.local import LocalFilesystemStore, assert_safe_key
from backend.storage.types import InvalidStorageKey, ObjectNotFound


@pytest.fixture
def memory_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


@pytest.fixture
def analysis_run_row(memory_session: Session, tmp_path) -> tuple[Session, AnalysisRun, Settings]:
    root = tmp_path / "artifact_root"
    root.mkdir()
    settings = Settings(artifact_storage_root=root)
    u = User(email=f"u-{uuid.uuid4().hex[:8]}@example.com", display_name="Test")
    memory_session.add(u)
    memory_session.flush()
    p = Project(owner_user_id=u.id, name="Proj")
    memory_session.add(p)
    memory_session.flush()
    run = AnalysisRun(project_id=p.id, status=AnalysisRunStatus.pending)
    memory_session.add(run)
    memory_session.flush()
    return memory_session, run, settings


def test_infer_kind_mime() -> None:
    k, m = infer_artifact_kind_and_mime(Path("x.csv"))
    assert k == ArtifactKind.tabular and m == "text/csv"
    k2, m2 = infer_artifact_kind_and_mime(Path("r.md"))
    assert k2 == ArtifactKind.document and m2 == "text/markdown"


def test_local_store_put_get_list_delete(tmp_path) -> None:
    store = LocalFilesystemStore(tmp_path)
    so = store.put("a/b/c.txt", b"hello", content_type="text/plain")
    assert so.uri.startswith("local:")
    assert store.get(store.key_from_uri(so.uri)) == b"hello"
    assert store.list_keys_under("a/b") == ["a/b/c.txt"]
    store.delete("a/b/c.txt")
    with pytest.raises(ObjectNotFound):
        store.get("a/b/c.txt")


def test_assert_safe_key_rejects_traversal() -> None:
    with pytest.raises(InvalidStorageKey):
        assert_safe_key("../x")
    with pytest.raises(InvalidStorageKey):
        assert_safe_key("")


def test_artifact_service_ingest_and_load(analysis_run_row) -> None:
    session, run, settings = analysis_run_row
    svc = ArtifactService(session, settings=settings)
    src = settings.artifact_storage_root.parent / "panel.csv"
    src.write_text("m,v\n1,2\n", encoding="utf-8")
    art = svc.ingest_pipeline_file(src, role_key="panel_csv", analysis_run_id=run.id)
    session.commit()
    assert art.role_key == "panel_csv"
    assert art.meta_json == {"source_filename": "panel.csv"}
    assert art.byte_size == len(src.read_bytes())
    assert art.content_sha256
    assert svc.load_bytes(art.id) == src.read_bytes()
    listed = svc.list_for_analysis_run(run.id)
    assert len(listed) == 1
    keys = svc.list_storage_keys_for_analysis_run(run.id)
    assert len(keys) == 1
    assert keys[0].startswith(f"artifacts/analysis_runs/{run.id}/")


def test_ingest_pipeline_paths_and_json(analysis_run_row) -> None:
    session, run, settings = analysis_run_row
    svc = ArtifactService(session, settings=settings)
    d = settings.artifact_storage_root.parent
    f1 = d / "a.csv"
    f1.write_text("x\n", encoding="utf-8")
    f2 = d / "b.md"
    f2.write_text("# hi", encoding="utf-8")
    arts = svc.ingest_pipeline_paths(
        {"anomalies_csv": f1, "report_md": f2},
        analysis_run_id=run.id,
    )
    assert len(arts) == 2
    assert arts[0].meta_json == {"source_filename": "a.csv"}
    assert arts[1].meta_json == {"source_filename": "b.md"}
    j = svc.ingest_json_payload({"ok": True}, role_key="summary_json", analysis_run_id=run.id)
    assert j.kind == ArtifactKind.json
    session.commit()


def test_delete_removes_blob(analysis_run_row) -> None:
    session, run, settings = analysis_run_row
    svc = ArtifactService(session, settings=settings)
    src = settings.artifact_storage_root.parent / "x.csv"
    src.write_bytes(b"x")
    art = svc.ingest_pipeline_file(src, role_key="x", analysis_run_id=run.id)
    session.commit()
    uri = art.storage_uri
    store = LocalFilesystemStore(settings.artifact_storage_root)
    assert store.exists(store.key_from_uri(uri))
    svc.delete(art.id)
    session.commit()
    assert not store.exists(store.key_from_uri(uri))
    assert svc.get(art.id) is None
