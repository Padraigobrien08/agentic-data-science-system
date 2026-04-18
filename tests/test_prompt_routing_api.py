"""Deterministic prompt-routing preview API regressions."""

from __future__ import annotations

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
from tests.api_auth import register_project_and_headers


@pytest.fixture
def prompt_routing_api_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, str, dict[str, str]]]:
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "true")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
        project_id, headers = register_project_and_headers(client)
        yield client, project_id, headers
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_route_preview_returns_supported_scope_narrowing(
    prompt_routing_api_client: tuple[TestClient, str, dict[str, str]],
) -> None:
    client, project_id, headers = prompt_routing_api_client

    response = client.post(
        "/v1/runs/route-preview",
        headers=headers,
        json={
            "project_id": project_id,
            "analysis_goal": "Analyze MSFT over the last 8 quarters for margin pressure",
            "tickers": ["AAPL", "MSFT", "NVDA"],
            "refresh": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["routing_source"] == "deterministic"
    assert body["effective_tickers"] == ["MSFT"]
    assert body["out_of_scope_tickers"] == []
    assert body["rewrite_suggestions"] == []
    assert body["intent"] == "anomaly_analysis"
    assert body["goal_code"] == "trend_deterioration"
    assert body["plan_template_id"] == "trend_deterioration"


def test_route_preview_returns_unsupported_guidance_for_out_of_scope_ticker(
    prompt_routing_api_client: tuple[TestClient, str, dict[str, str]],
) -> None:
    client, project_id, headers = prompt_routing_api_client

    response = client.post(
        "/v1/runs/route-preview",
        headers=headers,
        json={
            "project_id": project_id,
            "analysis_goal": "Analyze TSLA over the last 8 quarters for margin pressure",
            "tickers": ["AAPL", "MSFT", "NVDA"],
            "refresh": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is False
    assert body["routing_source"] == "deterministic"
    assert body["effective_tickers"] == ["AAPL", "MSFT", "NVDA"]
    assert body["out_of_scope_tickers"] == ["TSLA"]
    assert body["reason"] == "Requested tickers fall outside the current workspace scope."
    assert body["intent"] is None
    assert body["goal_code"] is None
    assert body["plan_template_id"] is None
    assert any("TSLA" in suggestion for suggestion in body["rewrite_suggestions"])


def test_route_preview_requires_project_ownership(
    prompt_routing_api_client: tuple[TestClient, str, dict[str, str]],
) -> None:
    client, project_id, _headers = prompt_routing_api_client
    _, foreign_headers = register_project_and_headers(client)

    response = client.post(
        "/v1/runs/route-preview",
        headers=foreign_headers,
        json={
            "project_id": project_id,
            "analysis_goal": "Analyze MSFT over the last 8 quarters for margin pressure",
            "tickers": ["AAPL", "MSFT", "NVDA"],
            "refresh": False,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
