"""Interest-signal capture endpoint."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.config.settings import get_settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.interest_signal import InterestSignal


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


def test_interest_capture_stores_email() -> None:
    client, factory = _make_client()
    r = client.post("/v1/interest", json={"email": "Investor@Example.com", "source": "landing"})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "received"

    with factory() as db:
        row = db.scalar(select(InterestSignal))
        assert row is not None
        assert row.email == "investor@example.com"  # normalized
        assert row.source == "landing"


def test_interest_rejects_bad_email() -> None:
    client, _ = _make_client()
    r = client.post("/v1/interest", json={"email": "not-an-email"})
    assert r.status_code == 422, r.text
