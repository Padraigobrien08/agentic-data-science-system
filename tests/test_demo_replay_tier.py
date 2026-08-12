"""
The public replay tier: publication as authorization.

``/v1/demos`` is the only unauthenticated read surface in the product, so most of what is
asserted here is what it must *refuse*: unpublished investigations, artifacts from a different
run, and anything at all once a slug is revoked.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.config.settings import get_settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind
from backend.models.investigation import Investigation
from backend.models.project import Project
from backend.models.user import User
from backend.services.demo_publication_service import (
    DemoNotFound,
    InvalidDemoSlug,
    publish,
    unpublish,
    validate_slug,
)

SLUG = "edgar-margin-deterioration"


@pytest.fixture
def demo_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker]]:
    monkeypatch.setenv("EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT", str(tmp_path / "blobs"))
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
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
        yield client, factory
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _seed(factory: sessionmaker, tmp_path, *, slug: str | None) -> dict:
    """One investigation with a run and a text artifact; published when ``slug`` is given."""
    storage_root = get_settings().artifact_storage_root
    storage_root.mkdir(parents=True, exist_ok=True)
    key = f"{uuid.uuid4().hex}.md"
    (storage_root / key).write_text("# Recorded finding\n\nMargin fell.", encoding="utf-8")

    with factory() as db:
        user = User(email=f"owner-{uuid.uuid4().hex[:8]}@example.com")
        db.add(user)
        db.flush()
        project = Project(owner_user_id=user.id, name="Demo project")
        db.add(project)
        db.flush()
        run = AnalysisRun(
            project_id=project.id,
            initiated_by_user_id=user.id,
            status=AnalysisRunStatus.success,
        )
        db.add(run)
        db.flush()
        artifact = Artifact(
            analysis_run_id=run.id,
            kind=ArtifactKind.document,
            role_key="finding_md",
            storage_uri=f"local:{key}",
            mime_type="text/markdown",
            byte_size=(storage_root / key).stat().st_size,
        )
        db.add(artifact)
        investigation = Investigation(
            domain_id=f"inv_{uuid.uuid4().hex[:10]}",
            project_id=project.id,
            initiated_by_user_id=user.id,
            analysis_run_id=run.id,
            status="concluded",
            demo_slug=slug,
        )
        db.add(investigation)
        db.commit()
        return {
            "investigation_id": investigation.id,
            "run_id": run.id,
            "artifact_id": artifact.id,
        }


# ------------------------------------------------------------------ slug validation


@pytest.mark.parametrize("bad", ["", "  ", "under_score", "trailing-", "a--b", "x" * 65, "sp ace", "a/b"])
def test_invalid_slugs_are_rejected(bad: str) -> None:
    with pytest.raises(InvalidDemoSlug):
        validate_slug(bad)


@pytest.mark.parametrize("good", ["a", "edgar-margin-deterioration", "csv-delivery-delays", "run2"])
def test_valid_slugs_are_accepted(good: str) -> None:
    assert validate_slug(good) == good


@pytest.mark.parametrize("raw", ["  EDGAR-Margin-Deterioration  ", "Run2", "\tcsv-delivery-delays\n"])
def test_slugs_are_normalized_not_rejected_for_case_and_whitespace(raw: str) -> None:
    """A CLI argument that differs only in case or padding should work, not fail."""
    assert validate_slug(raw) == raw.strip().lower()


# ----------------------------------------------------------------------- read access


def test_published_demo_is_readable_without_a_token(demo_env, tmp_path) -> None:
    client, factory = demo_env
    seeded = _seed(factory, tmp_path, slug=SLUG)

    listing = client.get("/v1/demos")
    assert listing.status_code == 200, listing.text
    assert [row["id"] for row in listing.json()] == [str(seeded["investigation_id"])]

    detail = client.get(f"/v1/demos/{SLUG}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == str(seeded["investigation_id"])


def test_unpublished_investigation_is_invisible(demo_env, tmp_path) -> None:
    client, factory = demo_env
    _seed(factory, tmp_path, slug=None)

    assert client.get("/v1/demos").json() == []
    assert client.get(f"/v1/demos/{SLUG}").status_code == 404


def test_demo_artifact_is_readable_without_a_token(demo_env, tmp_path) -> None:
    client, factory = demo_env
    seeded = _seed(factory, tmp_path, slug=SLUG)
    aid = seeded["artifact_id"]

    preview = client.get(f"/v1/demos/{SLUG}/artifacts/{aid}/preview")
    assert preview.status_code == 200, preview.text
    assert "Margin fell." in preview.json()["text"]

    content = client.get(f"/v1/demos/{SLUG}/artifacts/{aid}/content")
    assert content.status_code == 200, content.text
    assert b"Margin fell." in content.content


def test_artifact_from_another_run_is_not_readable_through_a_demo(demo_env, tmp_path) -> None:
    """Publication authorizes one run's artifacts, not the artifact table."""
    client, factory = demo_env
    _seed(factory, tmp_path, slug=SLUG)
    other = _seed(factory, tmp_path, slug=None)

    r = client.get(f"/v1/demos/{SLUG}/artifacts/{other['artifact_id']}/preview")
    assert r.status_code == 404, r.text


def test_unknown_artifact_id_is_indistinguishable_from_an_unpublished_one(demo_env, tmp_path) -> None:
    """Same 404 either way, so the public route cannot be used to probe for ids."""
    client, factory = demo_env
    _seed(factory, tmp_path, slug=SLUG)

    missing = client.get(f"/v1/demos/{SLUG}/artifacts/{uuid.uuid4()}/preview")
    assert missing.status_code == 404
    other = _seed(factory, tmp_path, slug=None)
    unauthorized = client.get(f"/v1/demos/{SLUG}/artifacts/{other['artifact_id']}/preview")
    assert unauthorized.status_code == 404
    assert missing.json()["detail"] == unauthorized.json()["detail"]


# ------------------------------------------------------------------------ revocation


def test_unpublishing_revokes_the_investigation_and_its_artifacts(demo_env, tmp_path) -> None:
    client, factory = demo_env
    seeded = _seed(factory, tmp_path, slug=SLUG)
    aid = seeded["artifact_id"]
    assert client.get(f"/v1/demos/{SLUG}/artifacts/{aid}/content").status_code == 200

    with factory() as db:
        unpublish(db, SLUG)
        db.commit()

    assert client.get(f"/v1/demos/{SLUG}").status_code == 404
    assert client.get(f"/v1/demos/{SLUG}/artifacts/{aid}/preview").status_code == 404
    assert client.get(f"/v1/demos/{SLUG}/artifacts/{aid}/content").status_code == 404


# ----------------------------------------------------------------------- publication


def test_publish_attaches_a_normalized_slug(demo_env, tmp_path) -> None:
    _, factory = demo_env
    seeded = _seed(factory, tmp_path, slug=None)
    with factory() as db:
        row = publish(db, seeded["investigation_id"], "  EDGAR-Margin-Deterioration  ")
        db.commit()
        assert row.demo_slug == SLUG


def test_publishing_a_taken_slug_is_refused(demo_env, tmp_path) -> None:
    _, factory = demo_env
    _seed(factory, tmp_path, slug=SLUG)
    second = _seed(factory, tmp_path, slug=None)
    with factory() as db:
        with pytest.raises(InvalidDemoSlug, match="already published"):
            publish(db, second["investigation_id"], SLUG)


def test_republishing_the_same_investigation_under_its_own_slug_is_allowed(demo_env, tmp_path) -> None:
    _, factory = demo_env
    seeded = _seed(factory, tmp_path, slug=SLUG)
    with factory() as db:
        row = publish(db, seeded["investigation_id"], SLUG)
        db.commit()
        assert row.demo_slug == SLUG


def test_publishing_an_unknown_investigation_is_refused(demo_env, tmp_path) -> None:
    _, factory = demo_env
    with factory() as db:
        with pytest.raises(DemoNotFound):
            publish(db, uuid.uuid4(), SLUG)
