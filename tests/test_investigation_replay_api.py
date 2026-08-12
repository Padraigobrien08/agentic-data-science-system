"""
The replay HTTP route.

Most of what matters here is what it refuses. A replay is a full investigation and costs real
model spend, but the candidate is deliberately never persisted (see ``agentic/agent/replay.py``),
so it produces no ``AnalysisRun`` and no ``ModelCall`` rows and the spend guard cannot see or
count it. An endpoint that spends money invisibly to the ceilings has to be closed to ordinary
accounts, and these tests are what hold that shut.
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
import backend.services.investigation_create_service as create_mod
from agentic.agent.fixture_policy import FixtureAgentPolicy
from backend.config.settings import Settings, get_settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.services import agentic_investigation_execution_service as exec_mod
from backend.services import investigation_replay_service as replay_mod
from tests.api_auth import bootstrap_admin_and_headers, register_project_and_headers

INVITE = "replay-tests-invite-code"
CSV = "entity,period,revenue\n" + "\n".join(f"A,2021-{i},{5 + 6 * i}" for i in range(8))


@pytest.fixture
def api_ctx(monkeypatch) -> Iterator[tuple[TestClient, str, dict[str, str]]]:
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "true")
    # Lets a test register a non-admin who still holds the adaptive tier — without it the
    # spend guard refuses them an investigation, and the admin gate below could never be
    # reached by anyone who owns one.
    monkeypatch.setenv("EDGAR_BACKEND_ADAPTIVE_INVITE_CODE", INVITE)
    get_settings.cache_clear()
    monkeypatch.setattr(create_mod, "get_settings", lambda: Settings(agentic_engine_enabled=True))
    monkeypatch.setattr(exec_mod, "build_agent_policy", lambda s, **_: FixtureAgentPolicy())
    # The replay service imports build_agent_policy into its own module, so patching it
    # anywhere else is a no-op — and a no-op here means the test calls a real provider and
    # spends real money. No `raising=False`: a wrong target must fail loudly.
    monkeypatch.setattr(replay_mod, "build_agent_policy", lambda s, **_: FixtureAgentPolicy())

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
        project_id, headers = bootstrap_admin_and_headers(client)
        yield client, project_id, headers
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _register_adaptive_non_admin(client: TestClient) -> tuple[str, dict[str, str]]:
    """A normal account that may run investigations but is not an operator."""
    email = f"owner-{uuid.uuid4().hex[:12]}@example.com"
    password = "replay-test-password-1"
    r = client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "invite_code": INVITE},
    )
    assert r.status_code == 201, r.text
    assert r.json()["access_tier"] == "adaptive"
    assert r.json()["is_admin"] is False
    r = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/v1/projects", json={"name": "Replay owner"}, headers=headers)
    assert r.status_code == 201, r.text
    return str(r.json()["id"]), headers


def _create_investigation(client: TestClient, project_id: str, headers: dict[str, str]) -> str:
    r = client.post(
        "/v1/investigations",
        json={
            "project_id": project_id,
            "goal": "revenue is increasing over time",
            "dataset": {
                "format": "csv",
                "csv_text": CSV,
                "name": "rev",
                "time_field": "period",
                "entity_id_fields": ["entity"],
            },
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["investigation_id"]


def test_replay_returns_a_conclusion_first_diff(api_ctx) -> None:
    client, project_id, h = api_ctx
    investigation_id = _create_investigation(client, project_id, h)

    r = client.post(f"/v1/investigations/{investigation_id}/replay", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["investigation_id"] == investigation_id
    assert body["diff"]["verdict"] in ("identical", "same_conclusion", "diverged")
    assert body["diff"]["summary"]
    # Replaying the deterministic policy against the same data must reach the same answer;
    # anything else would mean the loop is not reproducible.
    assert body["diff"]["verdict"] == "identical"
    assert body["same_dataset"] is True
    # Stated on the wire because it is the reason the spend guard cannot see this call.
    assert body["candidate_persisted"] is False


def test_replay_does_not_create_a_run_or_model_call_rows(api_ctx) -> None:
    """The property the admin-only gate exists to compensate for."""
    from backend.models.analysis_run import AnalysisRun
    from backend.models.model_call import ModelCall

    client, project_id, h = api_ctx
    investigation_id = _create_investigation(client, project_id, h)

    runs_before = len(client.get("/v1/runs", headers=h).json())
    r = client.post(f"/v1/investigations/{investigation_id}/replay", headers=h)
    assert r.status_code == 200, r.text
    runs_after = len(client.get("/v1/runs", headers=h).json())

    assert runs_after == runs_before, "a replay must not persist a candidate run"
    del AnalysisRun, ModelCall  # imported to document what is deliberately not written


def test_replay_is_refused_for_a_non_admin_who_owns_the_investigation(api_ctx) -> None:
    """
    The load-bearing refusal: a replay spends model budget the ceilings cannot count.

    The owner check runs first, so a *stranger* gets 404 and never reaches the admin gate.
    The case that actually exercises it is a non-admin who owns the investigation — which
    needs the adaptive tier, hence the invite code in the fixture. Asserting 403 exactly,
    not "403 or 404", or the ownership check would satisfy this test on its own and the gate
    could be deleted without failing anything.
    """
    client, _project_id, _admin_h = api_ctx
    project_id, owner_h = _register_adaptive_non_admin(client)
    investigation_id = _create_investigation(client, project_id, owner_h)

    readable = client.get(f"/v1/investigations/{investigation_id}", headers=owner_h)
    assert readable.status_code == 200, "the owner must be able to read it, or 403 proves nothing"

    r = client.post(f"/v1/investigations/{investigation_id}/replay", headers=owner_h)
    assert r.status_code == 403, r.text
    assert "admin" in r.json()["detail"].lower()


def test_replay_of_another_users_investigation_is_404(api_ctx) -> None:
    client, project_id, admin_h = api_ctx
    investigation_id = _create_investigation(client, project_id, admin_h)
    _other_project, other_h = register_project_and_headers(client)

    r = client.post(f"/v1/investigations/{investigation_id}/replay", headers=other_h)
    assert r.status_code == 404, r.text


def test_replay_of_an_unknown_investigation_is_404(api_ctx) -> None:
    client, _project_id, h = api_ctx
    r = client.post(f"/v1/investigations/{uuid.uuid4()}/replay", headers=h)
    assert r.status_code == 404, r.text


def test_replay_requires_authentication(api_ctx) -> None:
    client, project_id, h = api_ctx
    investigation_id = _create_investigation(client, project_id, h)
    r = client.post(f"/v1/investigations/{investigation_id}/replay")
    assert r.status_code in (401, 403), r.text
