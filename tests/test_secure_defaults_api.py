"""Secure-default API regressions for ops auth and privileged expansions."""

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
from tests.api_auth import bootstrap_admin_and_headers

OPS_HEADERS = {"Authorization": "Bearer pytest-ops-token"}
WRONG_OPS_HEADERS = {"Authorization": "Bearer wrong-ops-token"}


@pytest.fixture
def secure_defaults_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "false")
    monkeypatch.setenv("EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN", "pytest-bootstrap-token")
    monkeypatch.setenv("EDGAR_BACKEND_OPS_API_TOKEN", "pytest-ops-token")
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
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.parametrize("path", ["/health", "/v1/health", "/ready", "/v1/ready"])
def test_public_health_routes_remain_public_under_secure_defaults(
    secure_defaults_client: TestClient,
    path: str,
) -> None:
    response = secure_defaults_client.get(path)
    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/metrics", "/v1/worker/health"])
def test_ops_routes_require_exact_ops_token_under_secure_defaults(
    secure_defaults_client: TestClient,
    path: str,
) -> None:
    response = secure_defaults_client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    wrong = secure_defaults_client.get(path, headers=WRONG_OPS_HEADERS)
    assert wrong.status_code == 401
    assert wrong.headers["www-authenticate"] == "Bearer"

    _, user_headers = bootstrap_admin_and_headers(secure_defaults_client)
    user_bearer = secure_defaults_client.get(path, headers=user_headers)
    assert user_bearer.status_code == 401
    assert user_bearer.headers["www-authenticate"] == "Bearer"

    ok = secure_defaults_client.get(path, headers=OPS_HEADERS)
    assert ok.status_code == 200
