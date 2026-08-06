"""
The orchestration MCP server, exercised against the real API.

The MCP server is a client of ``/v1``, so these tests drive the actual tool functions
through the actual FastAPI app and database rather than against mocks. That is the only way
to verify the property that matters most: the MCP surface grants no access the caller's
token does not already have.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401 — register ORM metadata
from agentic.agent.fixture_policy import FixtureAgentPolicy
from backend.api.deps import get_db
from backend.config.settings import Settings
from backend.db.base import Base
from backend.main import create_app
from backend.mcp import client as client_mod
from backend.mcp import server as mcp_server
from backend.services import agentic_investigation_execution_service as exec_mod
from backend.services import investigation_create_service as create_mod
from tests.api_auth import bootstrap_admin_and_headers, register_project_and_headers

CSV = "entity,period,revenue\n" + "\n".join(f"A,2021-{i},{5 + 6 * i}" for i in range(8))
GOAL = "revenue is increasing over time"


@pytest.fixture
def api(monkeypatch) -> Iterator[tuple[TestClient, str, dict[str, str]]]:
    """The real app on an in-memory database, with the agentic engine enabled offline."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(create_mod, "get_settings", lambda: Settings(agentic_engine_enabled=True))
    monkeypatch.setattr(exec_mod, "build_agent_policy", lambda s: FixtureAgentPolicy())

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        project_id, headers = bootstrap_admin_and_headers(client)
        yield client, project_id, headers
    app.dependency_overrides.clear()


@pytest.fixture
def mcp_env(api, monkeypatch):
    """Point the MCP client's transport at the TestClient, authenticated as the admin."""
    client, project_id, headers = api

    def _route(method, url, headers=None, timeout=None, params=None, json=None):
        path = url.split("://", 1)[-1].split("/", 1)[-1]
        return client.request(method, f"/{path}", headers=headers, params=params, json=json)

    monkeypatch.setattr(client_mod.requests, "request", _route)
    monkeypatch.setenv("EDGAR_MCP_API_URL", "http://testserver")
    monkeypatch.setenv("EDGAR_MCP_TOKEN", headers["Authorization"].removeprefix("Bearer "))
    return client, project_id, headers


def _start(project_id: str, **kwargs) -> dict:
    return mcp_server.start_investigation(
        project_id=project_id, goal=GOAL, csv_text=CSV,
        time_field="period", entity_id_fields=["entity"], **kwargs)


def _investigation_id(started: dict) -> str:
    return started["data"]["investigation_id"]


# -- commissioning work ------------------------------------------------------


def test_start_investigation_creates_a_real_investigation(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    result = _start(project_id)

    assert result["status"] == "success", result
    assert result["data"]["analysis_run_id"]
    assert result["data"]["investigation_id"]


def test_start_investigation_accepts_records(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    records = [{"entity": "A", "period": f"2021-{i}", "revenue": 5 + 6 * i} for i in range(8)]
    result = mcp_server.start_investigation(
        project_id=project_id, goal=GOAL, records=records,
        time_field="period", entity_id_fields=["entity"])
    assert result["status"] == "success", result


@pytest.mark.parametrize(
    "kwargs",
    [
        {},  # neither csv_text nor records
        {"csv_text": CSV, "records": [{"a": 1}]},  # both
    ],
)
def test_start_investigation_validates_its_dataset(mcp_env, kwargs) -> None:
    _client, project_id, _h = mcp_env
    result = mcp_server.start_investigation(project_id=project_id, goal=GOAL, **kwargs)
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "VALIDATION_ERROR"


# -- reading investigations --------------------------------------------------


def test_the_read_tools_return_real_investigation_state(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    investigation_id = _investigation_id(_start(project_id))

    listed = mcp_server.list_investigations(project_id=project_id)
    assert listed["status"] == "success"
    assert listed["data"]["count"] >= 1

    detail = mcp_server.get_investigation(investigation_id)
    assert detail["status"] == "success"
    assert detail["data"]["id"]

    conclusion = mcp_server.get_conclusion(investigation_id)
    assert conclusion["status"] == "success"
    assert conclusion["data"]["objective"] == GOAL

    hypotheses = mcp_server.list_hypotheses(investigation_id)
    assert hypotheses["status"] == "success"
    assert hypotheses["data"]["count"] >= 1

    evidence = mcp_server.get_evidence(investigation_id)
    assert evidence["status"] == "success"
    assert evidence["data"]["count"] >= 1


def test_evidence_can_be_filtered_to_one_hypothesis(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    investigation_id = _investigation_id(_start(project_id))

    hypothesis_id = mcp_server.list_hypotheses(investigation_id)["data"]["hypotheses"][0]["id"]
    filtered = mcp_server.get_evidence(investigation_id, hypothesis_id=hypothesis_id)

    assert filtered["status"] == "success"
    assert filtered["data"]["hypothesis_id"] == hypothesis_id
    assert all(
        hypothesis_id in item["hypothesis_ids"] for item in filtered["data"]["evidence"]
    )


def test_list_investigations_bounds_its_limit(mcp_env) -> None:
    """A tool must never be able to flood an agent's context."""
    _client, project_id, _h = mcp_env
    result = mcp_server.list_investigations(project_id=project_id, limit=10_000)
    assert result["data"]["limit"] == mcp_server.MAX_LIST_LIMIT


# -- runs and artifacts ------------------------------------------------------


def test_run_status_and_artifacts_are_reachable(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    started = _start(project_id)
    run_id = started["data"]["analysis_run_id"]

    status = mcp_server.get_run_status(run_id)
    assert status["status"] == "success"

    artifacts = mcp_server.list_artifacts(run_id)
    assert artifacts["status"] == "success"
    assert artifacts["data"]["count"] >= 1

    artifact_id = artifacts["data"]["artifacts"][0]["id"]
    preview = mcp_server.get_artifact_preview(artifact_id)
    assert preview["status"] == "success"


@pytest.mark.parametrize(
    ("mime", "expected"),
    [
        ("application/json", True),
        ("application/vnd.chart+json", True),  # the loop's chart specs — regression
        ("text/csv", True),
        ("text/markdown", True),
        ("application/pdf", False),
        ("image/png", False),
    ],
)
def test_structured_json_suffix_types_are_previewable(mime: str, expected: bool) -> None:
    """
    Regression: the agentic loop emits chart specs as ``application/vnd.chart+json``, which
    was rejected with a 415 even though its bytes are plain JSON — making those artifacts
    unreadable through every surface, not only MCP. Any RFC 6839 ``+json`` type previews.
    """
    from backend.models.artifact import Artifact
    from backend.services.artifact_delivery import artifact_previewable

    assert artifact_previewable(Artifact(mime_type=mime)) is expected


def test_artifact_resource_returns_text(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    run_id = _start(project_id)["data"]["analysis_run_id"]
    artifact_id = mcp_server.list_artifacts(run_id)["data"]["artifacts"][0]["id"]

    body = mcp_server.artifact_resource(artifact_id)
    assert isinstance(body, str) and body


def test_conclusion_resource_renders_the_answer(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    investigation_id = _investigation_id(_start(project_id))

    body = mcp_server.conclusion_resource(investigation_id)
    assert GOAL in body
    assert "Conclusion:" in body


# -- the security property ---------------------------------------------------


def test_a_token_cannot_read_another_users_investigation(mcp_env, monkeypatch) -> None:
    """
    The MCP surface must grant no access the token does not already have. Ownership is
    enforced by the API (404 for both missing and unauthorized) and simply relayed here.
    """
    client, project_id, _h = mcp_env
    investigation_id = _investigation_id(_start(project_id))

    # A second, unrelated user's token.
    _other_project, other_headers = register_project_and_headers(client)
    monkeypatch.setenv("EDGAR_MCP_TOKEN", other_headers["Authorization"].removeprefix("Bearer "))

    result = mcp_server.get_investigation(investigation_id)
    assert result["status"] == "error"
    assert result["errors"][0]["http_status"] == 404


def test_an_unauthenticated_server_reports_rather_than_crashes(monkeypatch) -> None:
    monkeypatch.delenv("EDGAR_MCP_TOKEN", raising=False)
    result = mcp_server.list_investigations()
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "PLATFORM_NOT_CONFIGURED"


def test_resources_degrade_to_a_message_when_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("EDGAR_MCP_TOKEN", raising=False)
    assert "unavailable" in mcp_server.artifact_resource("does-not-matter")
    assert "unavailable" in mcp_server.conclusion_resource("does-not-matter")


# -- the envelope contract ---------------------------------------------------


def test_errors_never_cross_the_boundary_as_exceptions(mcp_env) -> None:
    """An agent must get a typed envelope it can reason about, not a transport failure."""
    result = mcp_server.get_investigation("00000000-0000-0000-0000-000000000000")
    assert result["status"] == "error"
    assert result["errors"], "an error envelope must carry at least one error"
    assert result["errors"][0]["message"]


def test_every_tool_returns_the_shared_envelope_shape(mcp_env) -> None:
    _client, project_id, _h = mcp_env
    investigation_id = _investigation_id(_start(project_id))

    for result in (
        mcp_server.list_investigations(project_id=project_id),
        mcp_server.get_investigation(investigation_id),
        mcp_server.get_conclusion(investigation_id),
        mcp_server.list_hypotheses(investigation_id),
        mcp_server.get_evidence(investigation_id),
    ):
        assert set(result) >= {"status", "message", "data", "artifacts", "errors"}


# -- hosted (HTTP) transport auth --------------------------------------------


class _FakeHeaders(dict):
    """Header mapping that is case-insensitive on lookup, like Starlette's."""

    def get(self, key, default=None):  # type: ignore[override]
        for k, v in self.items():
            if k.lower() == str(key).lower():
                return v
        return default


def _as_http_mode(monkeypatch, headers: dict | None) -> None:
    """Put the server in hosted mode with a given in-flight request's headers."""
    from types import SimpleNamespace

    from backend.mcp import auth as auth_mod

    monkeypatch.setattr(auth_mod, "_MODE", auth_mod.TransportMode.http)
    context = SimpleNamespace(
        request_context=SimpleNamespace(
            request=SimpleNamespace(headers=_FakeHeaders(headers)) if headers is not None else None
        )
    )
    monkeypatch.setattr(mcp_server.mcp, "get_context", lambda: context)


def test_hosted_mode_acts_as_the_calling_user(mcp_env, monkeypatch) -> None:
    """Each HTTP caller's own bearer token is what the downstream API sees."""
    _client, project_id, headers = mcp_env
    monkeypatch.setenv("EDGAR_MCP_TOKEN", "not-this-one")
    _as_http_mode(monkeypatch, {"Authorization": headers["Authorization"]})

    result = mcp_server.list_investigations(project_id=project_id)
    assert result["status"] == "success", result


def test_hosted_mode_never_falls_back_to_the_server_token(mcp_env, monkeypatch) -> None:
    """
    The security property that makes hosting safe. If a request without credentials fell back
    to EDGAR_MCP_TOKEN, every anonymous caller would inherit the operator's access.
    """
    _client, project_id, headers = mcp_env
    monkeypatch.setenv("EDGAR_MCP_TOKEN", headers["Authorization"].removeprefix("Bearer "))
    _as_http_mode(monkeypatch, {})  # a request carrying no Authorization header

    result = mcp_server.list_investigations(project_id=project_id)
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "PLATFORM_NOT_CONFIGURED"
    assert "hosted" in result["errors"][0]["message"].lower()


@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Basic abc123"},       # wrong scheme
        {"Authorization": "Bearer"},             # no value
        {"Authorization": "   "},                # blank
        {"X-Api-Key": "abc123"},                 # not an Authorization header
    ],
)
def test_hosted_mode_rejects_unusable_credentials(mcp_env, monkeypatch, header) -> None:
    _client, project_id, headers = mcp_env
    monkeypatch.setenv("EDGAR_MCP_TOKEN", headers["Authorization"].removeprefix("Bearer "))
    _as_http_mode(monkeypatch, header)

    result = mcp_server.list_investigations(project_id=project_id)
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "PLATFORM_NOT_CONFIGURED"


def test_hosted_mode_with_no_active_request_is_refused(mcp_env, monkeypatch) -> None:
    _client, project_id, headers = mcp_env
    monkeypatch.setenv("EDGAR_MCP_TOKEN", headers["Authorization"].removeprefix("Bearer "))
    _as_http_mode(monkeypatch, None)  # no in-flight request at all

    result = mcp_server.list_investigations(project_id=project_id)
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "PLATFORM_NOT_CONFIGURED"


def test_two_hosted_callers_are_isolated(mcp_env, monkeypatch) -> None:
    """A hosted server must not leak one caller's data to another."""
    client, project_id, headers = mcp_env
    investigation_id = _investigation_id(_start(project_id))
    _other_project, other_headers = register_project_and_headers(client)

    _as_http_mode(monkeypatch, {"Authorization": headers["Authorization"]})
    assert mcp_server.get_investigation(investigation_id)["status"] == "success"

    _as_http_mode(monkeypatch, {"Authorization": other_headers["Authorization"]})
    denied = mcp_server.get_investigation(investigation_id)
    assert denied["status"] == "error"
    assert denied["errors"][0]["http_status"] == 404


def test_stdio_mode_still_uses_the_environment_token(mcp_env, monkeypatch) -> None:
    """stdio is a per-user subprocess, so the environment token remains correct there."""
    from backend.mcp import auth as auth_mod

    _client, project_id, _h = mcp_env
    monkeypatch.setattr(auth_mod, "_MODE", auth_mod.TransportMode.stdio)
    assert mcp_server.list_investigations(project_id=project_id)["status"] == "success"


def test_transport_mode_defaults_to_stdio() -> None:
    """The safer default: require an explicit token rather than trusting an inbound header."""
    from backend.mcp.auth import TransportMode, get_transport_mode

    assert get_transport_mode() is TransportMode.stdio


def test_the_registered_tool_surface_is_the_platform(mcp_env) -> None:
    """The point of this server: the platform is reachable, not just EDGAR computation."""
    import asyncio

    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert {
        "start_investigation",
        "get_investigation",
        "list_hypotheses",
        "get_evidence",
        "get_conclusion",
        "list_artifacts",
    } <= names
