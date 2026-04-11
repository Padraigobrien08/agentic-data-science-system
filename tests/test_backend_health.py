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
        assert "llm" in body
        llm = body["llm"]
        assert llm["provider"] in ("off", "openai")
        assert isinstance(llm["ready"], bool)
        assert llm["message"]  # never null — explains status or confirms ready


def test_ready_returns_ready_when_db_ok(client: TestClient) -> None:
    for path in ("/ready", "/v1/ready"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["status"] == "ready"


def test_metrics_prometheus_text(client: TestClient) -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    assert b"edgar_http_requests_total" in r.content
    assert b"edgar_worker_queue_depth" in r.content
    assert b"edgar_worker_queue_pending_claimable" in r.content
    assert b"edgar_worker_last_terminal_job_unixtime" in r.content


def test_worker_health_json(client: TestClient) -> None:
    r = client.get("/v1/worker/health")
    assert r.status_code == 200
    body = r.json()
    assert "queue_depth" in body
    assert "jobs_running_lease_ok" in body
    assert "stale_running_jobs" in body
    assert "backlog_without_active_lease" in body
