"""
Focused tests for GET /v1/artifacts/{id}/content and /preview.

Uses in-memory SQLite, tmp_path blob root, and ArtifactService.save_bytes only
(no live EDGAR, no network).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

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
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind
from backend.services.artifact_service import ArtifactService
from backend.storage.local import LocalFilesystemStore
from tests.api_auth import register_project_and_headers


@dataclass
class ContentDeliveryHarness:
    """HTTP client + factory for analysis runs and stored artifacts."""

    client: TestClient
    project_id: uuid.UUID
    factory: sessionmaker[Session]
    settings: Settings
    auth_headers: dict[str, str]

    def api_get(self, path: str, **kwargs: Any) -> Any:
        merged = dict(self.auth_headers)
        extra = kwargs.pop("headers", None)
        if extra:
            merged.update(extra)
        return self.client.get(path, headers=merged, **kwargs)

    def create_run(self, db: Session) -> AnalysisRun:
        run = AnalysisRun(project_id=self.project_id, status=AnalysisRunStatus.success)
        db.add(run)
        db.flush()
        return run

    def save_artifact(
        self,
        *,
        body: bytes,
        role_key: str,
        filename_suffix: str,
        mime_type: str,
        kind: ArtifactKind | None = None,
    ) -> uuid.UUID:
        db = self.factory()
        try:
            run = self.create_run(db)
            svc = ArtifactService(db, settings=self.settings)
            row = svc.save_bytes(
                body,
                role_key=role_key,
                analysis_run_id=run.id,
                filename_suffix=filename_suffix,
                mime_type=mime_type,
                kind=kind,
            )
            db.commit()
            return row.id
        finally:
            db.close()


@pytest.fixture
def delivery_harness(tmp_path) -> Iterator[ContentDeliveryHarness]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    blob_root = tmp_path / "artifact_blobs"
    blob_root.mkdir()
    settings = Settings(artifact_storage_root=blob_root)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    def _artifact_service(db: Session = Depends(get_db)) -> ArtifactService:
        return ArtifactService(db, settings=settings)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[api_deps.get_artifact_service] = _artifact_service

    with TestClient(app) as client:
        project_id_str, auth_headers = register_project_and_headers(client)
        yield ContentDeliveryHarness(
            client=client,
            project_id=uuid.UUID(project_id_str),
            factory=factory,
            settings=settings,
            auth_headers=auth_headers,
        )
    app.dependency_overrides.clear()


# --- 1–3: content body, Content-Type, Content-Disposition ---


def test_content_returns_stored_text_bytes(delivery_harness: ContentDeliveryHarness) -> None:
    aid = delivery_harness.save_artifact(
        body=b"alpha\nbeta\n",
        role_key="notes",
        filename_suffix=".txt",
        mime_type="text/plain",
        kind=ArtifactKind.document,
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/content")
    assert r.status_code == 200
    assert r.content == b"alpha\nbeta\n"


@pytest.mark.parametrize(
    ("suffix", "mime", "expected_prefix"),
    [
        (".md", "text/markdown", "text/markdown"),
        (".json", "application/json", "application/json"),
        (".csv", "text/csv", "text/csv"),
    ],
)
def test_content_type_matches_stored_mime(
    delivery_harness: ContentDeliveryHarness,
    suffix: str,
    mime: str,
    expected_prefix: str,
) -> None:
    aid = delivery_harness.save_artifact(
        body=b"x",
        role_key="doc",
        filename_suffix=suffix,
        mime_type=mime,
        kind=ArtifactKind.json if mime == "application/json" else ArtifactKind.document,
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/content")
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert ct.startswith(expected_prefix), ct


def test_content_disposition_auto_inline_for_text_plain(
    delivery_harness: ContentDeliveryHarness,
) -> None:
    aid = delivery_harness.save_artifact(
        body=b"hi",
        role_key="readme",
        filename_suffix=".txt",
        mime_type="text/plain",
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/content")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "inline" in cd.lower()
    assert "filename=" in cd.lower()


def test_content_disposition_auto_attachment_for_octet_stream(
    delivery_harness: ContentDeliveryHarness,
) -> None:
    aid = delivery_harness.save_artifact(
        body=b"\x80\xff",
        role_key="bin",
        filename_suffix=".bin",
        mime_type="application/octet-stream",
        kind=ArtifactKind.binary,
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/content")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert "filename=" in cd.lower()


def test_content_disposition_query_inline_and_attachment_override(
    delivery_harness: ContentDeliveryHarness,
) -> None:
    aid = delivery_harness.save_artifact(
        body=b"x",
        role_key="data",
        filename_suffix=".bin",
        mime_type="application/octet-stream",
        kind=ArtifactKind.binary,
    )
    r_inline = delivery_harness.api_get(
        f"/v1/artifacts/{aid}/content",
        params={"disposition": "inline"},
    )
    assert r_inline.status_code == 200
    assert "inline" in r_inline.headers.get("content-disposition", "").lower()

    r_att = delivery_harness.api_get(
        f"/v1/artifacts/{aid}/content",
        params={"disposition": "attachment"},
    )
    assert r_att.status_code == 200
    assert "attachment" in r_att.headers.get("content-disposition", "").lower()


# --- 4: missing artifact ---


def test_missing_artifact_404_with_stable_detail(delivery_harness: ContentDeliveryHarness) -> None:
    missing = uuid.uuid4()
    for path in ("content", "preview"):
        r = delivery_harness.api_get(f"/v1/artifacts/{missing}/{path}")
        assert r.status_code == 404
        assert r.json().get("detail") == "Artifact not found"


# --- 5–6: preview supported / unsupported ---


def test_preview_text_plain_truncated_flag_false_for_small_payload(
    delivery_harness: ContentDeliveryHarness,
) -> None:
    aid = delivery_harness.save_artifact(
        body="line".encode(),
        role_key="small",
        filename_suffix=".txt",
        mime_type="text/plain",
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/preview")
    assert r.status_code == 200
    data = r.json()
    assert data["format"] == "text"
    assert data["text"] == "line"
    assert data["truncated"] is False
    assert data["mime_type"] == "text/plain"


def test_preview_json_pretty_when_valid(delivery_harness: ContentDeliveryHarness) -> None:
    aid = delivery_harness.save_artifact(
        body=b'{"z":1,"a":2}',
        role_key="cfg",
        filename_suffix=".json",
        mime_type="application/json",
        kind=ArtifactKind.json,
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/preview")
    assert r.status_code == 200
    data = r.json()
    assert data["format"] == "json"
    assert data["json_valid"] is True
    assert "\n" in data["text"]  # pretty-printed


def test_preview_csv_tabular_artifact(delivery_harness: ContentDeliveryHarness) -> None:
    aid = delivery_harness.save_artifact(
        body=b"a,b\n1,2\n",
        role_key="panel",
        filename_suffix=".csv",
        mime_type="text/csv",
        kind=ArtifactKind.tabular,
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/preview")
    assert r.status_code == 200
    assert "a,b" in r.json()["text"]


def test_preview_kind_fallback_when_mime_type_cleared(
    delivery_harness: ContentDeliveryHarness,
) -> None:
    """With empty MIME, preview eligibility uses document/json/tabular kind."""
    aid = delivery_harness.save_artifact(
        body=b"# Title",
        role_key="report",
        filename_suffix=".md",
        mime_type="text/markdown",
        kind=ArtifactKind.document,
    )
    db = delivery_harness.factory()
    try:
        row = db.get(Artifact, aid)
        assert row is not None
        row.mime_type = None
        db.commit()
    finally:
        db.close()

    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/preview")
    assert r.status_code == 200
    assert "# Title" in r.json()["text"]


def test_preview_415_binary_octet_stream(delivery_harness: ContentDeliveryHarness) -> None:
    aid = delivery_harness.save_artifact(
        body=b"\x00\x01",
        role_key="raw",
        filename_suffix=".bin",
        mime_type="application/octet-stream",
        kind=ArtifactKind.binary,
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/preview")
    assert r.status_code == 415
    assert "preview" in r.json()["detail"].lower()


def test_preview_415_application_pdf(delivery_harness: ContentDeliveryHarness) -> None:
    aid = delivery_harness.save_artifact(
        body=b"%PDF-1.4 minimal",
        role_key="report",
        filename_suffix=".pdf",
        mime_type="application/pdf",
        kind=ArtifactKind.other,
    )
    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/preview")
    assert r.status_code == 415


# --- 7: storage errors, no internal leak ---


def test_content_404_when_blob_deleted_but_row_exists(
    delivery_harness: ContentDeliveryHarness,
) -> None:
    aid = delivery_harness.save_artifact(
        body=b"gone",
        role_key="tmp",
        filename_suffix=".txt",
        mime_type="text/plain",
    )
    db = delivery_harness.factory()
    try:
        row = db.get(Artifact, aid)
        assert row is not None
        uri = row.storage_uri
    finally:
        db.close()

    store = LocalFilesystemStore(delivery_harness.settings.artifact_storage_root)
    store.delete(store.key_from_uri(uri))

    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/content")
    assert r.status_code == 404
    payload = r.json()
    assert payload.get("detail") == "Artifact content not found in storage"
    text = str(payload).lower()
    assert "artifact_storage_root" not in text
    assert str(delivery_harness.settings.artifact_storage_root).lower() not in text


def test_content_502_unsupported_uri_scheme_generic_detail(
    delivery_harness: ContentDeliveryHarness,
) -> None:
    aid = delivery_harness.save_artifact(
        body=b"x",
        role_key="x",
        filename_suffix=".txt",
        mime_type="text/plain",
    )
    db = delivery_harness.factory()
    try:
        row = db.get(Artifact, aid)
        assert row is not None
        row.storage_uri = "s3:my-bucket/secret/path/object.dat"
        db.commit()
    finally:
        db.close()

    r = delivery_harness.api_get(f"/v1/artifacts/{aid}/content")
    assert r.status_code == 502
    payload = r.json()
    assert payload.get("detail") == "Storage backend is not configured for this artifact"
    assert "bucket" not in str(payload)
    assert "secret" not in str(payload)
    assert "s3:" not in str(payload)
