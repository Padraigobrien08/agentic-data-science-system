"""Auth endpoint rate limiting (backlog C2)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401  (register ORM metadata)
from backend.api.rate_limit import SlidingWindowRateLimiter
from backend.config.settings import get_settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app


class _FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_allows_up_to_limit_then_blocks() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowRateLimiter(max_attempts=3, window_seconds=60, clock=clock)
    assert [limiter.hit("k").allowed for _ in range(3)] == [True, True, True]
    blocked = limiter.hit("k")
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 60  # oldest hit expires a full window out


def test_window_slides_and_recovers() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowRateLimiter(max_attempts=2, window_seconds=60, clock=clock)
    assert limiter.hit("k").allowed is True
    assert limiter.hit("k").allowed is True
    assert limiter.hit("k").allowed is False
    clock.advance(61)  # both prior hits age out
    assert limiter.hit("k").allowed is True


def test_keys_are_isolated() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowRateLimiter(max_attempts=1, window_seconds=60, clock=clock)
    assert limiter.hit("a").allowed is True
    assert limiter.hit("a").allowed is False
    assert limiter.hit("b").allowed is True  # different key unaffected


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_attempts=0, window_seconds=60)
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_attempts=1, window_seconds=0)


@pytest.fixture
def rate_limited_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("EDGAR_BACKEND_AUTH_RATE_LIMIT_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("EDGAR_BACKEND_AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()

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
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_login_burst_gets_429(rate_limited_client: TestClient) -> None:
    """Integration: bad logins beyond the budget return 429 + Retry-After."""
    client = rate_limited_client
    assert client.app.state.auth_rate_limiter is not None
    payload = {"email": "nobody@example.com", "password": "wrong-password"}

    # Budget is 3 (set by the fixture): first three are processed (401), then 429.
    statuses = [client.post("/v1/auth/login", json=payload).status_code for _ in range(5)]
    assert statuses[:3] == [401, 401, 401]
    assert statuses[3:] == [429, 429]

    blocked = client.post("/v1/auth/login", json=payload)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def test_rate_limit_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDGAR_BACKEND_AUTH_RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    try:
        app = create_app()
        assert app.state.auth_rate_limiter is None
    finally:
        get_settings.cache_clear()
