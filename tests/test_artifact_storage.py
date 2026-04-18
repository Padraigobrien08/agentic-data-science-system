"""Tests for object storage + :class:`~backend.services.artifact_service.ArtifactService`."""

from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

import pytest
from pydantic import SecretStr
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
from backend.storage.factory import get_s3_object_store
from backend.storage.local import LocalFilesystemStore, assert_safe_key
from backend.storage.types import InvalidStorageKey, ObjectNotFound

SECURE_JWT_SECRET = "secure-jwt-secret-minimum-32-characters-long"
BOOTSTRAP_TOKEN = "pytest-bootstrap-token"
OPS_TOKEN = "pytest-ops-token"


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


def _s3_settings(tmp_path: Path, **overrides: object) -> Settings:
    root = tmp_path / "artifact_root_s3"
    root.mkdir(exist_ok=True)
    defaults: dict[str, object] = {
        "artifact_storage_root": root,
        "artifact_storage_backend": "s3",
        "artifact_storage_s3_bucket": "artifact-bucket",
        "artifact_storage_s3_region": "us-east-1",
        "jwt_secret": SecretStr(SECURE_JWT_SECRET),
        "bootstrap_admin_token": SecretStr(BOOTSTRAP_TOKEN),
        "ops_api_token": SecretStr(OPS_TOKEN),
    }
    defaults.update(overrides)
    return Settings(**defaults)


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


def test_local_store_put_fileobj_streams_and_preserves_digest(tmp_path) -> None:
    store = LocalFilesystemStore(tmp_path)
    payload = (b"0123456789abcdef" * 80_000) + b"tail"

    stored = store.put_fileobj(
        "a/b/payload.bin",
        io.BytesIO(payload),
        content_type="application/octet-stream",
    )

    assert stored.uri.startswith("local:")
    assert stored.byte_size == len(payload)
    assert stored.sha256_hex == hashlib.sha256(payload).hexdigest()
    assert stored.content_type == "application/octet-stream"
    assert store.get("a/b/payload.bin") == payload


def test_local_store_put_fileobj_removes_temp_file_on_failure(tmp_path) -> None:
    store = LocalFilesystemStore(tmp_path)

    class BrokenStream:
        def __init__(self) -> None:
            self._reads = 0

        def read(self, _size: int = -1) -> bytes:
            self._reads += 1
            if self._reads == 1:
                return b"partial"
            raise OSError("stream failure")

    with pytest.raises(OSError, match="stream failure"):
        store.put_fileobj("a/b/payload.bin", BrokenStream())

    assert not store.exists("a/b/payload.bin")
    assert not list((tmp_path / "a" / "b").glob(".payload.bin.*.tmp"))


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


def test_artifact_service_ingest_pipeline_file_streams_without_read_bytes(
    analysis_run_row,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, run, settings = analysis_run_row
    svc = ArtifactService(session, settings=settings)
    src = settings.artifact_storage_root.parent / "report.md"
    content = "# streamed report\n"
    src.write_text(content, encoding="utf-8")

    def _fail_read_bytes(self) -> bytes:  # pragma: no cover - exercised through monkeypatch
        raise AssertionError("read_bytes should not be called")

    monkeypatch.setattr(Path, "read_bytes", _fail_read_bytes)

    art = svc.ingest_pipeline_file(src, role_key="report_md", analysis_run_id=run.id)
    session.commit()

    assert art.kind == ArtifactKind.document
    assert art.byte_size == len(content.encode("utf-8"))
    assert art.meta_json == {"source_filename": "report.md"}

    store = LocalFilesystemStore(settings.artifact_storage_root)
    stored_path = settings.artifact_storage_root / store.key_from_uri(art.storage_uri)
    with stored_path.open("rb") as fh:
        assert fh.read() == content.encode("utf-8")


def test_artifact_service_ingest_pipeline_file_cleans_temp_files_on_store_failure(
    analysis_run_row,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, run, settings = analysis_run_row
    svc = ArtifactService(session, settings=settings)
    src = settings.artifact_storage_root.parent / "panel.csv"
    src.write_text("value\n1\n", encoding="utf-8")

    def _fail_replace(_src: str, _dest: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("backend.storage.local.os.replace", _fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        svc.ingest_pipeline_file(src, role_key="panel_csv", analysis_run_id=run.id)

    target_dir = settings.artifact_storage_root / "artifacts" / "analysis_runs" / str(run.id)
    tmp_files = list(target_dir.glob(".*.tmp"))
    assert not tmp_files, f"leftover temp files: {tmp_files}"


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


def test_artifact_service_s3_save_bytes_and_ingest_round_trip(
    memory_session: Session,
    tmp_path,
) -> None:
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")

    with moto.mock_aws():
        settings = _s3_settings(tmp_path)
        boto3.client("s3", region_name=settings.artifact_storage_s3_region).create_bucket(
            Bucket=settings.artifact_storage_s3_bucket,
        )

        session = memory_session
        u = User(email=f"s3-{uuid.uuid4().hex[:8]}@example.com", display_name="S3")
        session.add(u)
        session.flush()
        p = Project(owner_user_id=u.id, name="Proj")
        session.add(p)
        session.flush()
        run = AnalysisRun(project_id=p.id, status=AnalysisRunStatus.pending)
        session.add(run)
        session.flush()

        svc = ArtifactService(session, settings=settings)
        raw = svc.save_bytes(
            b"hello remote",
            role_key="notes",
            analysis_run_id=run.id,
            filename_suffix=".txt",
            mime_type="text/plain",
            kind=ArtifactKind.document,
        )
        source = settings.artifact_storage_root.parent / "remote-report.md"
        source.write_text("# remote\n", encoding="utf-8")
        ingested = svc.ingest_pipeline_file(source, role_key="report_md", analysis_run_id=run.id)
        session.commit()

        assert raw.storage_uri.startswith("s3:")
        assert ingested.storage_uri.startswith("s3:")
        assert raw.content_sha256
        assert ingested.content_sha256
        assert svc.load_bytes(raw.id) == b"hello remote"
        assert svc.load_bytes(ingested.id) == b"# remote\n"


def test_artifact_service_s3_cleans_uploaded_object_when_row_insert_fails(
    memory_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")

    with moto.mock_aws():
        settings = _s3_settings(tmp_path)
        boto3.client("s3", region_name=settings.artifact_storage_s3_region).create_bucket(
            Bucket=settings.artifact_storage_s3_bucket,
        )

        session = memory_session
        u = User(email=f"cleanup-{uuid.uuid4().hex[:8]}@example.com", display_name="Cleanup")
        session.add(u)
        session.flush()
        p = Project(owner_user_id=u.id, name="Proj")
        session.add(p)
        session.flush()
        run = AnalysisRun(project_id=p.id, status=AnalysisRunStatus.pending)
        session.add(run)
        session.flush()

        s3_store = get_s3_object_store(settings)
        svc = ArtifactService(session, settings=settings, store=s3_store)
        uploaded_uri: str | None = None
        original_put = s3_store.put

        def _track_put(key: str, data: bytes, *, content_type: str | None = None):
            nonlocal uploaded_uri
            stored = original_put(key, data, content_type=content_type)
            uploaded_uri = stored.uri
            return stored

        monkeypatch.setattr(s3_store, "put", _track_put)

        def _flush_fail() -> None:
            raise RuntimeError("flush failed")

        monkeypatch.setattr(svc._artifacts, "flush", _flush_fail)

        with pytest.raises(RuntimeError, match="flush failed"):
            svc.save_bytes(
                b"cleanup me",
                role_key="notes",
                analysis_run_id=run.id,
                filename_suffix=".txt",
                mime_type="text/plain",
                kind=ArtifactKind.document,
            )

        assert uploaded_uri is not None
        assert s3_store.exists(s3_store.key_from_uri(uploaded_uri)) is False


def test_artifact_service_delete_failure_marks_storage_reconciliation(
    analysis_run_row,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, run, settings = analysis_run_row
    svc = ArtifactService(session, settings=settings)
    src = settings.artifact_storage_root.parent / "delete.txt"
    src.write_text("delete me", encoding="utf-8")
    art = svc.ingest_pipeline_file(src, role_key="notes", analysis_run_id=run.id)
    session.commit()

    def _delete_fail(_uri: str, *, settings: Settings | None = None) -> None:
        raise OSError("delete failed")

    monkeypatch.setattr("backend.services.artifact_service.delete_at_uri", _delete_fail)

    with pytest.raises(OSError, match="delete failed"):
        svc.delete(art.id)

    session.commit()
    row = svc.get(art.id)
    assert row is not None
    assert isinstance(row.meta_json, dict)
    reconciliation = row.meta_json["storage_reconciliation"]
    assert reconciliation["status"] == "repair_required"
    assert reconciliation["operation"] == "delete"
    assert reconciliation["uri_scheme"] == "local"
