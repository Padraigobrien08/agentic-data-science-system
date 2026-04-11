"""Smoke tests for the FastAPI app (package ``backend`` at repo root).

Run ``alembic upgrade head`` first so the default SQLite DB exists and
``GET /v1/health`` can execute ``SELECT 1``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from backend.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health_returns_ok_and_version(client: TestClient) -> None:
    for path in ("/health", "/v1/health"):
        r = client.get(path)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["version"]
        assert body["database"]["ok"] is True


def test_ready_returns_ready_when_db_ok(client: TestClient) -> None:
    for path in ("/ready", "/v1/ready"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["status"] == "ready"


def test_metrics_prometheus_text(client: TestClient) -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    assert b"edgar_http_requests_total" in r.content
