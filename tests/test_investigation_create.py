"""Create-and-run an agentic investigation over a user dataset (service + HTTP)."""

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
from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.domain import InvestigationStatus
from backend.config.settings import Settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus
from backend.models.project import Project
from backend.models.user import User
from backend.services import agentic_investigation_execution_service as exec_mod
from backend.services import investigation_create_service as create_mod
from backend.services.agentic_investigation_execution_service import AgenticInvestigationExecutionService
from backend.services.investigation_create_service import (
    AgenticEngineDisabledError,
    InvalidDatasetError,
    InvestigationCreateService,
    parse_csv_to_records,
)
from tests.api_auth import bootstrap_admin_and_headers, register_project_and_headers

CSV = "entity,period,revenue\n" + "\n".join(f"A,2021-{i},{5 + 6 * i}" for i in range(8))


def _enabled_settings() -> Settings:
    return Settings(agentic_engine_enabled=True)


def _disabled_settings() -> Settings:
    return Settings(agentic_engine_enabled=False)


def _force_fixture_policy(monkeypatch) -> None:
    """Keep runs offline/deterministic regardless of ambient LLM config."""
    monkeypatch.setattr(exec_mod, "build_agent_policy", lambda s, **_: FixtureAgentPolicy())


# --- CSV parsing (unit) -----------------------------------------------------


def test_parse_csv_coerces_types_and_headers() -> None:
    records = parse_csv_to_records("a,b,c\n1,2.5,x\n3,,y")
    assert records == [
        {"a": 1, "b": 2.5, "c": "x"},
        {"a": 3, "b": None, "c": "y"},
    ]


def test_parse_csv_rejects_empty_and_bad_headers() -> None:
    with pytest.raises(InvalidDatasetError):
        parse_csv_to_records("")
    with pytest.raises(InvalidDatasetError):
        parse_csv_to_records("a,b\n")  # header only
    with pytest.raises(InvalidDatasetError):
        parse_csv_to_records("a,,c\n1,2,3")  # empty column name
    with pytest.raises(InvalidDatasetError):
        parse_csv_to_records("a,a\n1,2")  # duplicate column


# --- service ----------------------------------------------------------------


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield s
    finally:
        s.close()


def _seed_project(session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="p")
    session.add(project)
    session.commit()
    return project.id, user.id


def test_service_creates_runs_and_persists(session: Session, monkeypatch) -> None:
    _force_fixture_policy(monkeypatch)
    project_id, user_id = _seed_project(session)
    result = InvestigationCreateService(session, settings=_enabled_settings()).create_and_run(
        project_id=project_id,
        user_id=user_id,
        goal="revenue is increasing over time",
        dataset_format="csv",
        csv_text=CSV,
        records=None,
        name="rev",
        time_field="period",
        entity_id_fields=["entity"],
    )
    assert result.status in (InvestigationStatus.converged.value, InvestigationStatus.exhausted.value)
    assert result.investigation_id is not None
    assert result.analysis_run_id is not None


def test_service_rejects_when_flag_disabled(session: Session) -> None:
    project_id, user_id = _seed_project(session)
    with pytest.raises(AgenticEngineDisabledError):
        InvestigationCreateService(session, settings=Settings(agentic_engine_enabled=False)).create_and_run(
            project_id=project_id, user_id=user_id, goal="g", dataset_format="csv",
            csv_text=CSV, records=None, name="d", time_field=None, entity_id_fields=[],
        )


# --- HTTP -------------------------------------------------------------------


@pytest.fixture
def api_ctx(monkeypatch) -> Iterator[tuple[TestClient, str, dict[str, str], sessionmaker[Session]]]:
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
        project_id, headers = bootstrap_admin_and_headers(client)
        yield client, project_id, headers, factory
    app.dependency_overrides.clear()


def _enable_flag(monkeypatch) -> None:
    monkeypatch.setattr(create_mod, "get_settings", _enabled_settings)


def _disable_flag(monkeypatch) -> None:
    """
    Pin the flag off rather than inheriting it.

    The default is off, but a developer recording demos sets
    ``EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true`` in ``.env``, which Settings reads — so a
    test that leans on the ambient default asserts nothing on that machine and passes only
    by luck on CI.
    """
    monkeypatch.setattr(create_mod, "get_settings", _disabled_settings)


def test_http_create_disabled_returns_409(api_ctx, monkeypatch) -> None:
    client, project_id, h, _factory = api_ctx
    _disable_flag(monkeypatch)
    r = client.post(
        "/v1/investigations",
        json={"project_id": project_id, "goal": "g", "dataset": {"format": "csv", "csv_text": CSV}},
        headers=h,
    )
    assert r.status_code == 409


def test_http_create_runs_and_is_readable(api_ctx, monkeypatch) -> None:
    client, project_id, h, _factory = api_ctx
    _enable_flag(monkeypatch)
    _force_fixture_policy(monkeypatch)
    r = client.post(
        "/v1/investigations",
        json={
            "project_id": project_id,
            "goal": "revenue is increasing over time",
            "dataset": {"format": "csv", "csv_text": CSV, "name": "rev",
                        "time_field": "period", "entity_id_fields": ["entity"]},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] in ("converged", "exhausted")

    detail = client.get(f"/v1/investigations/{body['investigation_id']}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["analysis_run_id"] == body["analysis_run_id"]
    assert len(detail.json()["experiments"]) >= 1


def test_service_enqueue_leaves_run_queued(session: Session, monkeypatch) -> None:
    project_id, user_id = _seed_project(session)
    result = InvestigationCreateService(session, settings=_enabled_settings()).create_and_enqueue(
        project_id=project_id, user_id=user_id, goal="revenue trend", dataset_format="csv",
        csv_text=CSV, records=None, name="rev", time_field="period", entity_id_fields=["entity"],
    )
    assert result.queued is True
    assert result.investigation_id is None
    assert result.status == "queued"
    run = session.get(AnalysisRun, result.analysis_run_id)
    assert run.status == AnalysisRunStatus.queued
    # no investigation exists until the worker runs it
    from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
    assert SqlAlchemyInvestigationRepository(session).get_by_domain_id(str(run.id)) is None


def test_http_async_create_queues_then_resolves(api_ctx, monkeypatch) -> None:
    client, project_id, h, factory = api_ctx
    _enable_flag(monkeypatch)
    _force_fixture_policy(monkeypatch)

    r = client.post(
        "/v1/investigations",
        json={
            "project_id": project_id, "goal": "revenue is increasing over time",
            "async_execution": True,
            "dataset": {"format": "csv", "csv_text": CSV, "name": "rev",
                        "time_field": "period", "entity_id_fields": ["entity"]},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["queued"] is True and body["investigation_id"] is None
    run_id = body["analysis_run_id"]

    # not resolvable yet — the worker has not run it
    pre = client.get("/v1/investigations", params={"analysis_run_id": run_id}, headers=h)
    assert pre.status_code == 200 and pre.json() == []

    # simulate the worker claiming and executing the queued run (shared in-memory DB)
    worker = factory()
    AgenticInvestigationExecutionService(
        worker, policy_factory=lambda s: FixtureAgentPolicy()
    ).execute_analysis_run(uuid.UUID(run_id), from_worker=True)
    worker.close()

    # now the read path resolves the investigation for that run
    resolved = client.get("/v1/investigations", params={"analysis_run_id": run_id}, headers=h)
    assert resolved.status_code == 200
    items = resolved.json()
    assert len(items) == 1 and items[0]["analysis_run_id"] == run_id
    detail = client.get(f"/v1/investigations/{items[0]['id']}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["status"] in ("converged", "exhausted")


def test_http_create_invalid_csv_returns_400(api_ctx, monkeypatch) -> None:
    client, project_id, h, _factory = api_ctx
    _enable_flag(monkeypatch)
    r = client.post(
        "/v1/investigations",
        json={"project_id": project_id, "goal": "g", "dataset": {"format": "csv", "csv_text": "a,b\n"}},
        headers=h,
    )
    assert r.status_code == 400


def test_http_create_other_users_project_is_404(api_ctx, monkeypatch) -> None:
    client, _project_id, _h, _factory = api_ctx
    _enable_flag(monkeypatch)
    other_project, other_headers = register_project_and_headers(client)
    # first user's project id is not owned by the just-registered user
    r = client.post(
        "/v1/investigations",
        json={"project_id": _project_id, "goal": "g", "dataset": {"format": "csv", "csv_text": CSV}},
        headers=other_headers,
    )
    assert r.status_code == 404


# --- dataset source: EDGAR as one adapter among others ----------------------


def test_edgar_source_builds_an_edgar_payload(session: Session, monkeypatch) -> None:
    """
    The route used to hardcode ``adapter: in_memory``, so EDGAR was unreachable through
    /v1/investigations even though the execution layer already supported it. The payload here
    must match the shape the recording path already proved works, or the run resolves to a
    schema-only manifest and every EDGAR experiment degrades.
    """
    _force_fixture_policy(monkeypatch)
    project_id, user_id = _seed_project(session)
    svc = InvestigationCreateService(session, settings=_enabled_settings())
    run = svc._prepare_run(
        project_id=project_id,
        user_id=user_id,
        goal="has margin deteriorated?",
        dataset_format="csv",
        csv_text=None,
        records=None,
        name="edgar",
        time_field=None,
        entity_id_fields=[],
        source="edgar",
        entities=["aapl", " msft "],
        refresh=True,
    )
    payload = run.input_payload_json
    assert payload["engine"] == "agentic"
    # Tickers are normalised and appear in *both* places the execution service reads them.
    assert payload["tickers"] == ["AAPL", "MSFT"]
    assert payload["dataset"] == {"adapter": "edgar", "entities": ["AAPL", "MSFT"]}
    assert payload["refresh"] is True
    assert "records" not in payload["dataset"]


def test_tabular_source_is_unchanged_and_is_the_default(session: Session, monkeypatch) -> None:
    """Callers written before `source` existed must be unaffected."""
    _force_fixture_policy(monkeypatch)
    project_id, user_id = _seed_project(session)
    svc = InvestigationCreateService(session, settings=_enabled_settings())
    run = svc._prepare_run(
        project_id=project_id,
        user_id=user_id,
        goal="is revenue trending up?",
        dataset_format="csv",
        csv_text=CSV,
        records=None,
        name="rev",
        time_field="period",
        entity_id_fields=["entity"],
    )
    dataset = run.input_payload_json["dataset"]
    assert dataset["adapter"] == "in_memory"
    assert dataset["time_field"] == "period"
    assert len(dataset["records"]) == 8
    assert "tickers" not in run.input_payload_json


def test_edgar_source_without_tickers_is_rejected(session: Session) -> None:
    project_id, user_id = _seed_project(session)
    svc = InvestigationCreateService(session, settings=_enabled_settings())
    with pytest.raises(InvalidDatasetError, match="ticker"):
        svc._prepare_run(
            project_id=project_id,
            user_id=user_id,
            goal="anything",
            dataset_format="csv",
            csv_text=None,
            records=None,
            name="x",
            time_field=None,
            entity_id_fields=[],
            source="edgar",
            entities=["  "],
        )


def test_schema_rejects_an_edgar_dataset_with_no_entities() -> None:
    from pydantic import ValidationError

    from backend.schemas.investigation import InvestigationDatasetInput

    with pytest.raises(ValidationError, match="entities"):
        InvestigationDatasetInput(source="edgar", entities=[])


def test_schema_caps_edgar_entities() -> None:
    from pydantic import ValidationError

    from backend.schemas.investigation import MAX_EDGAR_ENTITIES, InvestigationDatasetInput

    ok = InvestigationDatasetInput(source="edgar", entities=["A"] * MAX_EDGAR_ENTITIES)
    assert len(ok.entities) == MAX_EDGAR_ENTITIES
    with pytest.raises(ValidationError, match="Too many tickers"):
        InvestigationDatasetInput(source="edgar", entities=["A"] * (MAX_EDGAR_ENTITIES + 1))


def test_schema_rejects_a_tabular_dataset_with_no_csv() -> None:
    from pydantic import ValidationError

    from backend.schemas.investigation import InvestigationDatasetInput

    with pytest.raises(ValidationError, match="csv_text"):
        InvestigationDatasetInput(source="tabular", format="csv", csv_text="   ")


def test_http_edgar_investigation_queues_with_an_edgar_payload(api_ctx, monkeypatch) -> None:
    """
    The whole HTTP path for the unified entry, without touching the SEC.

    Enqueued rather than executed on purpose: executing would build a panel from live filings.
    What needs proving here is that the route, schema and service produce a run the execution
    layer will resolve to the EDGAR adapter — the payload below is byte-identical to the one
    ``scripts/record_demo.py edgar`` produces, which is the shape already verified end to end
    against real filings.
    """
    client, project_id, h, factory = api_ctx
    _enable_flag(monkeypatch)

    r = client.post(
        "/v1/investigations",
        json={
            "project_id": project_id,
            "goal": "has margin quality deteriorated, or is revenue growth the explanation?",
            "async_execution": True,
            "dataset": {"source": "edgar", "entities": ["aapl", "msft"]},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["queued"] is True

    session = factory()
    try:
        run = session.get(AnalysisRun, uuid.UUID(body["analysis_run_id"]))
        assert run is not None
        assert run.input_payload_json["dataset"] == {
            "adapter": "edgar",
            "entities": ["AAPL", "MSFT"],
        }
        assert run.input_payload_json["tickers"] == ["AAPL", "MSFT"]
        assert run.input_payload_json["engine"] == "agentic"
    finally:
        session.close()


def test_http_edgar_investigation_without_tickers_returns_422(api_ctx, monkeypatch) -> None:
    """Schema-level refusal, before any run row is created."""
    client, project_id, h, _factory = api_ctx
    _enable_flag(monkeypatch)

    r = client.post(
        "/v1/investigations",
        json={
            "project_id": project_id,
            "goal": "anything",
            "dataset": {"source": "edgar", "entities": []},
        },
        headers=h,
    )
    assert r.status_code == 422, r.text
    assert "entities" in r.text
