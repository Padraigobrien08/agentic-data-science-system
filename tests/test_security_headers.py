"""HTTP security headers + CORS posture (backlog C3)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

import backend.models  # noqa: F401  (register ORM metadata)
from backend.api.security_headers import SecurityHeadersMiddleware


def _app(*, hsts: int = 63_072_000, csp: str = "default-src 'none'", origins: list[str] | None = None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age_seconds=hsts,
        content_security_policy=csp,
    )
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/thing")
    def thing() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/docs")
    def docs() -> dict[str, str]:  # stand-in for the interactive docs path
        return {"docs": "yes"}

    return app


def test_baseline_security_headers_present() -> None:
    client = TestClient(_app())
    resp = client.get("/thing")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert resp.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert resp.headers["Content-Security-Policy"] == "default-src 'none'"


def test_csp_exempts_docs_paths() -> None:
    client = TestClient(_app())
    assert "Content-Security-Policy" not in client.get("/docs").headers


def test_hsts_only_on_https() -> None:
    client = TestClient(_app())
    assert "Strict-Transport-Security" not in client.get("/thing").headers  # http
    https = client.get("/thing", headers={"X-Forwarded-Proto": "https"})
    assert https.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains"


def test_hsts_disabled_when_zero() -> None:
    client = TestClient(_app(hsts=0))
    resp = client.get("/thing", headers={"X-Forwarded-Proto": "https"})
    assert "Strict-Transport-Security" not in resp.headers


def test_cors_closed_by_default() -> None:
    client = TestClient(_app(origins=None))
    resp = client.get("/thing", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


def test_cors_allows_configured_origin() -> None:
    client = TestClient(_app(origins=["https://app.example"]))
    resp = client.get("/thing", headers={"Origin": "https://app.example"})
    assert resp.headers["access-control-allow-origin"] == "https://app.example"
