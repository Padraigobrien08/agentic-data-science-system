"""Guest demo session endpoint."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.config.settings import get_settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun  # noqa: F401  (metadata)
from backend.models.project import Project


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _make_client() -> tuple[TestClient, sessionmaker[Session]]:
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
    return TestClient(app), factory


def test_guest_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_GUEST_DEMO", "false")
    get_settings.cache_clear()
    client, _ = _make_client()
    r = client.post("/v1/auth/guest")
    assert r.status_code == 403, r.text


def test_guest_session_provisions_isolated_workspace(monkeypatch) -> None:
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_GUEST_DEMO", "true")
    get_settings.cache_clear()
    client, factory = _make_client()

    r1 = client.post("/v1/auth/guest")
    assert r1.status_code == 201, r1.text
    body = r1.json()
    assert body["access_token"] and body["token_type"] == "bearer"
    project_id = body["project_id"]

    # The returned token can immediately reach the guest's own project.
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    proj = client.get(f"/v1/projects/{project_id}", headers=headers)
    assert proj.status_code == 200, proj.text
    assert proj.json()["tickers"] == ["AAPL", "MSFT", "NVDA"]

    # A second guest gets a distinct, isolated workspace.
    r2 = client.post("/v1/auth/guest")
    assert r2.status_code == 201
    assert r2.json()["project_id"] != project_id

    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Project)) == 2
