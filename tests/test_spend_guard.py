"""
Spend admission control: access tiers, the invite code, and the run/spend ceilings.

These tests exist because the guard's failure mode is silent. A cap that never fires looks
exactly like a cap that is never reached, so each ceiling here is asserted to *bind* (refuse a
run) rather than merely to be configured.
"""

from __future__ import annotations

import uuid
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
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, UserAccessTier
from backend.models.user import User
from backend.services.spend_guard import (
    ENGINE_AGENTIC,
    SpendLimitExceeded,
    account_usage,
    check_run_admission,
    pricing_is_configured,
)
from tests.api_auth import TEST_PASSWORD

INVITE = "let-me-in-please-1234"


@pytest.fixture
def guard_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker]]:
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "true")
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_GUEST_DEMO", "true")
    monkeypatch.setenv("EDGAR_BACKEND_ADAPTIVE_INVITE_CODE", INVITE)
    get_settings.cache_clear()

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
        yield client, factory
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _register(client: TestClient, *, invite_code: str | None = None) -> tuple[str, dict[str, str]]:
    """Register, log in, create a project. Returns ``(project_id, headers)``."""
    email = f"guard-{uuid.uuid4().hex[:12]}@example.com"
    body: dict[str, object] = {"email": email, "password": TEST_PASSWORD}
    if invite_code is not None:
        body["invite_code"] = invite_code
    r = client.post("/v1/auth/register", json=body)
    assert r.status_code == 201, r.text
    r = client.post("/v1/auth/login", json={"email": email, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/v1/projects", json={"name": "Guard project"}, headers=headers)
    assert r.status_code == 201, r.text
    return str(r.json()["id"]), headers


def _me(client: TestClient, headers: dict[str, str]) -> dict:
    r = client.get("/v1/auth/me", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------------------- tiers


def test_registration_without_invite_code_is_standard_tier(guard_client) -> None:
    client, _ = guard_client
    _, headers = _register(client)
    assert _me(client, headers)["access_tier"] == "standard"


def test_correct_invite_code_grants_adaptive_tier(guard_client) -> None:
    client, _ = guard_client
    _, headers = _register(client, invite_code=INVITE)
    assert _me(client, headers)["access_tier"] == "adaptive"


def test_wrong_invite_code_still_registers_but_stays_standard(guard_client) -> None:
    """A bad code must not be an error — it would turn registration into a code oracle."""
    client, _ = guard_client
    _, headers = _register(client, invite_code="not-the-code")
    assert _me(client, headers)["access_tier"] == "standard"


def test_invite_code_ignored_when_none_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no code configured there is no self-serve path to the paid engine at all."""
    monkeypatch.setenv("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "true")
    monkeypatch.delenv("EDGAR_BACKEND_ADAPTIVE_INVITE_CODE", raising=False)
    get_settings.cache_clear()

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
        _, headers = _register(client, invite_code="")
        assert _me(client, headers)["access_tier"] == "standard"
        caps = client.get("/v1/auth/capabilities").json()
        assert caps["invite_code_accepted"] is False
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_capabilities_advertises_invite_without_leaking_it(guard_client) -> None:
    client, _ = guard_client
    body = client.get("/v1/auth/capabilities").json()
    assert body["invite_code_accepted"] is True
    assert INVITE not in str(body)


def test_guest_session_gets_guest_tier(guard_client) -> None:
    client, _ = guard_client
    r = client.post("/v1/auth/guest")
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert _me(client, headers)["access_tier"] == "guest"


def test_guest_can_load_its_own_profile(guard_client) -> None:
    """
    Regression: guest emails once used ``@demo.local``, which ``EmailStr`` rejects as a
    special-use domain when ``UserRead`` validates the *response*. Every guest got a 500 from
    ``GET /auth/me`` — and the frontend layout loads the current user on each render, so the
    guest tier was broken end to end.
    """
    client, _ = guard_client
    r = client.post("/v1/auth/guest")
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["email"].endswith("@guest.example.com")


# ------------------------------------------------------------------- engine gating


def _run_row(db: Session, *, user: User, status: AnalysisRunStatus, engine: str | None) -> AnalysisRun:
    from backend.models.project import Project

    project = db.scalar(select(Project).where(Project.owner_user_id == user.id))
    assert project is not None
    row = AnalysisRun(
        project_id=project.id,
        initiated_by_user_id=user.id,
        status=status,
        input_payload_json={"engine": engine} if engine else {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _user_by_tier(factory: sessionmaker, tier: UserAccessTier) -> User:
    with factory() as db:
        user = db.scalar(select(User).where(User.access_tier == tier))
        assert user is not None, f"no {tier} user registered"
        return user


def test_standard_user_requesting_agentic_gets_deterministic_engine(
    guard_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hole this guard exists to close: asking for the paid engine must not grant it."""
    from backend.services.agentic_investigation_execution_service import select_run_engine

    client, factory = guard_client
    _register(client)
    monkeypatch.setenv("EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED", "true")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.standard)
    with factory() as db:
        row = _run_row(db, user=db.get(User, user.id), status=AnalysisRunStatus.pending, engine="agentic")
        assert select_run_engine(row, get_settings()) == "edgar"


def test_adaptive_user_requesting_agentic_gets_agentic_engine(
    guard_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.services.agentic_investigation_execution_service import select_run_engine

    client, factory = guard_client
    _register(client, invite_code=INVITE)
    monkeypatch.setenv("EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED", "true")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.adaptive)
    with factory() as db:
        row = _run_row(db, user=db.get(User, user.id), status=AnalysisRunStatus.pending, engine="agentic")
        assert select_run_engine(row, get_settings()) == ENGINE_AGENTIC


def test_guest_requesting_agentic_is_silently_downgraded(
    guard_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.services.agentic_investigation_execution_service import select_run_engine

    client, factory = guard_client
    r = client.post("/v1/auth/guest")
    assert r.status_code == 201
    monkeypatch.setenv("EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED", "true")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.guest)
    with factory() as db:
        row = _run_row(db, user=db.get(User, user.id), status=AnalysisRunStatus.pending, engine="agentic")
        assert select_run_engine(row, get_settings()) == "edgar"


def test_standard_user_is_refused_the_investigations_route(guard_client, monkeypatch) -> None:
    client, _ = guard_client
    project_id, headers = _register(client)
    monkeypatch.setenv("EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED", "true")
    get_settings.cache_clear()

    r = client.post(
        "/v1/investigations",
        json={
            "project_id": project_id,
            "goal": "why did margin fall",
            "dataset": {"format": "csv", "csv_text": "a,b\n1,2\n", "name": "d"},
        },
        headers=headers,
    )
    assert r.status_code == 403, r.text
    assert "invite code" in r.json()["detail"].lower()


# ------------------------------------------------------------------------ ceilings


def test_run_count_ceiling_refuses_execution(guard_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, factory = guard_client
    _register(client)
    monkeypatch.setenv("EDGAR_BACKEND_STANDARD_MAX_RUNS_PER_ACCOUNT", "2")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.standard)
    with factory() as db:
        u = db.get(User, user.id)
        for _ in range(2):
            _run_row(db, user=u, status=AnalysisRunStatus.success, engine=None)
        with pytest.raises(SpendLimitExceeded) as exc:
            check_run_admission(db, u, settings=get_settings())
    assert exc.value.scope == "account"
    assert exc.value.limit_name == "max_runs_per_account"


def test_pending_runs_do_not_consume_the_ceiling(guard_client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating rows is free; only runs that entered execution may count."""
    client, factory = guard_client
    _register(client)
    monkeypatch.setenv("EDGAR_BACKEND_STANDARD_MAX_RUNS_PER_ACCOUNT", "2")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.standard)
    with factory() as db:
        u = db.get(User, user.id)
        for _ in range(5):
            _run_row(db, user=u, status=AnalysisRunStatus.pending, engine=None)
        assert account_usage(db, u.id, settings=get_settings()).run_count == 0
        check_run_admission(db, u, settings=get_settings())  # must not raise


def test_global_monthly_run_ceiling_refuses_everyone(guard_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, factory = guard_client
    _register(client)
    monkeypatch.setenv("EDGAR_BACKEND_GLOBAL_MONTHLY_MAX_RUNS", "1")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.standard)
    with factory() as db:
        u = db.get(User, user.id)
        _run_row(db, user=u, status=AnalysisRunStatus.success, engine=None)
        with pytest.raises(SpendLimitExceeded) as exc:
            check_run_admission(db, u, settings=get_settings())
    assert exc.value.scope == "global"


def test_admin_is_exempt_from_ceilings(guard_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, factory = guard_client
    _register(client)
    monkeypatch.setenv("EDGAR_BACKEND_GLOBAL_MONTHLY_MAX_RUNS", "1")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.standard)
    with factory() as db:
        u = db.get(User, user.id)
        _run_row(db, user=u, status=AnalysisRunStatus.success, engine=None)
        u.is_admin = True
        db.commit()
        check_run_admission(db, u, settings=get_settings())  # must not raise


def test_usd_ceiling_is_inert_without_pricing(guard_client, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    The documented trap. Unpriced models estimate at $0.00, so a USD-only guard cannot fire —
    which is exactly why the run-count ceiling is the real backstop.
    """
    client, factory = guard_client
    _register(client, invite_code=INVITE)
    monkeypatch.setenv("EDGAR_BACKEND_LLM_MODEL_PRICES", "")
    monkeypatch.setenv("EDGAR_BACKEND_ADAPTIVE_MAX_SPEND_USD_PER_ACCOUNT", "0.01")
    monkeypatch.setenv("EDGAR_BACKEND_ADAPTIVE_MAX_RUNS_PER_ACCOUNT", "0")
    get_settings.cache_clear()

    assert pricing_is_configured(get_settings()) is False
    user = _user_by_tier(factory, UserAccessTier.adaptive)
    with factory() as db:
        u = db.get(User, user.id)
        snapshot = account_usage(db, u.id, settings=get_settings())
        assert snapshot.cost_priced is False
        # No raise: the USD ceiling cannot bind, and that must be visible in cost_priced
        # rather than mistaken for "this account has spent nothing".
        check_run_admission(db, u, settings=get_settings())


def test_usd_ceiling_binds_when_pricing_is_configured(guard_client, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.models.model_call import ModelCall

    client, factory = guard_client
    _register(client, invite_code=INVITE)
    monkeypatch.setenv(
        "EDGAR_BACKEND_LLM_MODEL_PRICES",
        '{"test-model": {"input_per_1m": 1.0, "output_per_1m": 1.0}}',
    )
    monkeypatch.setenv("EDGAR_BACKEND_ADAPTIVE_MAX_SPEND_USD_PER_ACCOUNT", "0.5")
    monkeypatch.setenv("EDGAR_BACKEND_ADAPTIVE_MAX_RUNS_PER_ACCOUNT", "0")
    get_settings.cache_clear()

    user = _user_by_tier(factory, UserAccessTier.adaptive)
    with factory() as db:
        u = db.get(User, user.id)
        run = _run_row(db, user=u, status=AnalysisRunStatus.success, engine="agentic")
        db.add(
            ModelCall(
                analysis_run_id=run.id,
                provider="test",
                model_name="test-model",
                prompt_tokens=500_000,
                completion_tokens=500_000,
            )
        )
        db.commit()

        snapshot = account_usage(db, u.id, settings=get_settings())
        assert snapshot.cost_priced is True
        assert snapshot.cost_usd == pytest.approx(1.0)

        with pytest.raises(SpendLimitExceeded) as exc:
            check_run_admission(db, u, settings=get_settings())
    assert exc.value.limit_name == "max_spend_usd_per_account"


# --------------------------------------------------- agentic model-call persistence


def test_agentic_policy_completions_are_persisted_as_model_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Regression: the loop's policy called the provider directly and tracked cost only in
    memory, so an agentic run persisted **zero** ``ModelCall`` rows. That left
    ``GET /v1/runs/{id}/llm-usage`` empty for the flagship engine and made the per-account
    USD ceiling read $0.00 forever — a ceiling that cannot bind is worse than none, because
    it looks enforced.
    """
    from sqlalchemy import create_engine as _create_engine
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    from backend.agents.agentic_model_policy import CostTrackingResponder
    from backend.llm.pricing import ModelPrice
    from backend.llm.types import ChatCompletionResult
    from backend.models.model_call import ModelCall
    from backend.models.project import Project
    from backend.services.recorded_chat_completion_service import RecordedChatCompletionService

    class _StubProvider:
        provider_id = "stub"

        def complete(self, request):
            return ChatCompletionResult(
                assistant_text='{"ok": true}',
                model=request.model,
                prompt_tokens=1_000_000,
                completion_tokens=1_000_000,
                latency_ms=12,
            )

    monkeypatch.setenv(
        "EDGAR_BACKEND_LLM_MODEL_PRICES",
        '{"test-model": {"input_per_1m": 1.0, "output_per_1m": 1.0}}',
    )
    get_settings.cache_clear()

    engine = _create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = _sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db:
        user = User(email=f"policy-{uuid.uuid4().hex[:8]}@example.com")
        db.add(user)
        db.flush()
        project = Project(owner_user_id=user.id, name="p")
        db.add(project)
        db.flush()
        run = AnalysisRun(
            project_id=project.id,
            initiated_by_user_id=user.id,
            status=AnalysisRunStatus.running,
        )
        db.add(run)
        db.commit()

        provider = _StubProvider()
        responder = CostTrackingResponder(
            provider,
            model="test-model",
            prices={"test-model": ModelPrice(input_per_1m=1.0, output_per_1m=1.0)},
            recorder=RecordedChatCompletionService(db, provider),
            analysis_run_id=run.id,
        )
        assert responder("sys", "user") == '{"ok": true}'
        db.commit()

        rows = list(db.scalars(select(ModelCall).where(ModelCall.analysis_run_id == run.id)).all())
        assert len(rows) == 1
        assert rows[0].prompt_tokens == 1_000_000
        assert rows[0].completion_tokens == 1_000_000

        # And the guard can now see the spend it is supposed to cap.
        snapshot = account_usage(db, user.id, settings=get_settings())
        assert snapshot.cost_priced is True
        assert snapshot.cost_usd > 0
