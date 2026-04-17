"""Retention maintenance regressions for schema surfacing and operator workflows."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, ModelCallStatus
from backend.models.model_call import ModelCall
from backend.models.project import Project
from backend.models.user import User
from backend.repositories.analysis_run_repository import AnalysisRunRepository
from backend.repositories.model_call_repository import ModelCallRepository
from backend.schemas.api_phase_a import (
    AnalysisRunDetailResponse,
    ModelCallApiItem,
    analysis_run_to_detail,
    model_call_to_api_item,
)

SECURE_JWT_SECRET = "secure-jwt-secret-minimum-32-characters-long"
BOOTSTRAP_TOKEN = "pytest-bootstrap-token"
OPS_TOKEN = "pytest-ops-token"


def _retention_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "jwt_secret": SecretStr(SECURE_JWT_SECRET),
        "bootstrap_admin_token": SecretStr(BOOTSTRAP_TOKEN),
        "ops_api_token": SecretStr(OPS_TOKEN),
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
def retention_session() -> tuple[Session, Settings]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    settings = _retention_settings(
        retention_run_payload_days=30,
        retention_model_payload_days=30,
        retention_batch_size=100,
    )
    try:
        yield session, settings
    finally:
        session.close()


def _seed_retention_history(session: Session) -> dict[str, uuid.UUID]:
    user = User(email=f"retention-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="Retention")
    session.add(project)
    session.flush()

    old_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    fresh_timestamp = datetime(2026, 4, 10, tzinfo=timezone.utc)

    eligible_run = AnalysisRun(
        project_id=project.id,
        status=AnalysisRunStatus.success,
        input_payload_json={"goal": "eligible"},
        output_payload_json={"answer": "eligible"},
        finished_at=old_timestamp,
        created_at=old_timestamp,
        updated_at=old_timestamp,
    )
    fresh_run = AnalysisRun(
        project_id=project.id,
        status=AnalysisRunStatus.success,
        input_payload_json={"goal": "fresh"},
        output_payload_json={"answer": "fresh"},
        finished_at=fresh_timestamp,
        created_at=fresh_timestamp,
        updated_at=fresh_timestamp,
    )
    active_run = AnalysisRun(
        project_id=project.id,
        status=AnalysisRunStatus.running,
        input_payload_json={"goal": "active"},
        output_payload_json={"answer": "active"},
        created_at=old_timestamp,
        updated_at=old_timestamp,
    )
    session.add_all([eligible_run, fresh_run, active_run])
    session.flush()

    eligible_model_call = ModelCall(
        analysis_run_id=eligible_run.id,
        provider="openai",
        model_name="gpt-test",
        status=ModelCallStatus.success,
        request_payload_json={"messages": ["eligible"]},
        response_payload_json={"output": "eligible"},
        created_at=old_timestamp,
        updated_at=old_timestamp,
    )
    fresh_model_call = ModelCall(
        analysis_run_id=eligible_run.id,
        provider="openai",
        model_name="gpt-test",
        status=ModelCallStatus.success,
        request_payload_json={"messages": ["fresh"]},
        response_payload_json={"output": "fresh"},
        created_at=fresh_timestamp,
        updated_at=fresh_timestamp,
    )
    unscoped_model_call = ModelCall(
        provider="openai",
        model_name="gpt-test",
        status=ModelCallStatus.success,
        request_payload_json={"messages": ["skip"]},
        response_payload_json={"output": "skip"},
        created_at=old_timestamp,
        updated_at=old_timestamp,
    )
    session.add_all([eligible_model_call, fresh_model_call, unscoped_model_call])
    session.commit()

    return {
        "eligible_run_id": eligible_run.id,
        "fresh_run_id": fresh_run.id,
        "active_run_id": active_run.id,
        "eligible_model_call_id": eligible_model_call.id,
        "fresh_model_call_id": fresh_model_call.id,
        "unscoped_model_call_id": unscoped_model_call.id,
    }


def test_retention_settings_fields_exist() -> None:
    settings = _retention_settings()

    assert settings.retention_run_payload_days == 0
    assert settings.retention_model_payload_days == 0
    assert settings.retention_artifact_blob_days == 0
    assert settings.retention_batch_size > 0


def test_retention_schema_columns_exist() -> None:
    assert "compacted_at" in AnalysisRun.__table__.columns.keys()
    assert "payloads_redacted_at" in ModelCall.__table__.columns.keys()


def test_retention_serializer_surfaces_run_and_model_timestamps() -> None:
    timestamp = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc)

    run = AnalysisRun(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=AnalysisRunStatus.success,
        input_payload_json={"goal": "trim later"},
        output_payload_json={"answer": "still here"},
        compacted_at=timestamp,
        finished_at=created_at,
        created_at=created_at,
        updated_at=created_at,
    )
    run_validated = AnalysisRunDetailResponse.model_validate(run)
    run_hidden_payloads = analysis_run_to_detail(run, include_payloads=False)

    assert run_validated.compacted_at == timestamp
    assert run_hidden_payloads.compacted_at == timestamp
    assert run_hidden_payloads.input_payload_json is None
    assert run_hidden_payloads.output_payload_json is None

    model_call = ModelCall(
        id=uuid.uuid4(),
        analysis_run_id=run.id,
        provider="openai",
        model_name="gpt-test",
        status=ModelCallStatus.success,
        request_payload_json={"messages": ["sensitive"]},
        response_payload_json={"output": "sensitive"},
        payloads_redacted_at=timestamp,
        created_at=created_at,
        updated_at=created_at,
    )
    call_validated = ModelCallApiItem.model_validate(model_call)
    call_hidden_payloads = model_call_to_api_item(model_call, include_payloads=False)

    assert call_validated.payloads_redacted_at == timestamp
    assert call_hidden_payloads.payloads_redacted_at == timestamp
    assert call_hidden_payloads.request_payload_json is None
    assert call_hidden_payloads.response_payload_json is None


def test_retention_dry_run_reports_candidates_without_mutation(
    retention_session: tuple[Session, Settings],
) -> None:
    from backend.maintenance.retention import format_retention_report, run_retention_maintenance

    session, settings = retention_session
    seeded = _seed_retention_history(session)

    report = run_retention_maintenance(
        session,
        settings=settings,
        dry_run=True,
        now=datetime(2026, 4, 17, tzinfo=timezone.utc),
    )

    assert list(report.keys()) == [
        "dry_run",
        "run_candidates",
        "model_call_candidates",
        "runs_compacted",
        "model_calls_redacted",
        "errors",
    ]
    assert report["dry_run"] is True
    assert report["run_candidates"] == 1
    assert report["model_call_candidates"] == 1
    assert report["runs_compacted"] == 0
    assert report["model_calls_redacted"] == 0
    assert report["errors"] == []

    eligible_run = session.get(AnalysisRun, seeded["eligible_run_id"])
    eligible_model_call = session.get(ModelCall, seeded["eligible_model_call_id"])
    assert eligible_run is not None
    assert eligible_run.input_payload_json == {"goal": "eligible"}
    assert eligible_run.output_payload_json == {"answer": "eligible"}
    assert eligible_run.compacted_at is None
    assert eligible_model_call is not None
    assert eligible_model_call.request_payload_json == {"messages": ["eligible"]}
    assert eligible_model_call.response_payload_json == {"output": "eligible"}
    assert eligible_model_call.payloads_redacted_at is None

    report_json = format_retention_report(report, json_output=True)
    assert json.loads(report_json) == report


def test_retention_apply_mode_compacts_runs_and_redacts_model_payloads(
    retention_session: tuple[Session, Settings],
) -> None:
    from backend.maintenance.retention import run_retention_maintenance

    session, settings = retention_session
    seeded = _seed_retention_history(session)
    runs = AnalysisRunRepository(session)
    model_calls = ModelCallRepository(session)
    cutoff = datetime(2026, 3, 18, tzinfo=timezone.utc)

    assert [row.id for row in runs.list_compaction_candidates(finished_before=cutoff, limit=10)] == [
        seeded["eligible_run_id"]
    ]
    assert [
        row.id for row in model_calls.list_payload_redaction_candidates(created_before=cutoff, limit=10)
    ] == [seeded["eligible_model_call_id"]]

    report = run_retention_maintenance(
        session,
        settings=settings,
        dry_run=False,
        now=datetime(2026, 4, 17, tzinfo=timezone.utc),
    )

    assert report["dry_run"] is False
    assert report["run_candidates"] == 1
    assert report["model_call_candidates"] == 1
    assert report["runs_compacted"] == 1
    assert report["model_calls_redacted"] == 1
    assert report["errors"] == []

    eligible_run = session.get(AnalysisRun, seeded["eligible_run_id"])
    fresh_run = session.get(AnalysisRun, seeded["fresh_run_id"])
    active_run = session.get(AnalysisRun, seeded["active_run_id"])
    eligible_model_call = session.get(ModelCall, seeded["eligible_model_call_id"])
    fresh_model_call = session.get(ModelCall, seeded["fresh_model_call_id"])
    unscoped_model_call = session.get(ModelCall, seeded["unscoped_model_call_id"])

    assert eligible_run is not None
    assert eligible_run.input_payload_json is None
    assert eligible_run.output_payload_json is None
    assert eligible_run.compacted_at == datetime(2026, 4, 17, tzinfo=timezone.utc)
    assert fresh_run is not None
    assert fresh_run.input_payload_json == {"goal": "fresh"}
    assert fresh_run.compacted_at is None
    assert active_run is not None
    assert active_run.input_payload_json == {"goal": "active"}
    assert active_run.compacted_at is None

    assert eligible_model_call is not None
    assert eligible_model_call.request_payload_json is None
    assert eligible_model_call.response_payload_json is None
    assert eligible_model_call.payloads_redacted_at == datetime(2026, 4, 17, tzinfo=timezone.utc)
    assert fresh_model_call is not None
    assert fresh_model_call.request_payload_json == {"messages": ["fresh"]}
    assert fresh_model_call.payloads_redacted_at is None
    assert unscoped_model_call is not None
    assert unscoped_model_call.request_payload_json == {"messages": ["skip"]}
    assert unscoped_model_call.payloads_redacted_at is None


def test_retention_apply_mode_is_idempotent_on_second_run(
    retention_session: tuple[Session, Settings],
) -> None:
    from backend.maintenance.retention import run_retention_maintenance

    session, settings = retention_session
    _seed_retention_history(session)

    first_report = run_retention_maintenance(
        session,
        settings=settings,
        dry_run=False,
        now=datetime(2026, 4, 17, tzinfo=timezone.utc),
    )
    second_report = run_retention_maintenance(
        session,
        settings=settings,
        dry_run=False,
        now=datetime(2026, 4, 18, tzinfo=timezone.utc),
    )

    assert first_report["runs_compacted"] == 1
    assert first_report["model_calls_redacted"] == 1
    assert second_report["run_candidates"] == 0
    assert second_report["model_call_candidates"] == 0
    assert second_report["runs_compacted"] == 0
    assert second_report["model_calls_redacted"] == 0
    assert second_report["errors"] == []


def test_retention_cli_parser_accepts_dry_run_apply_limit_and_json() -> None:
    from backend.maintenance.retention import build_parser

    parser = build_parser()

    defaults = parser.parse_args([])
    applied = parser.parse_args(["--apply", "--limit", "7", "--json"])
    dry_run = parser.parse_args(["--dry-run"])

    assert defaults.dry_run is True
    assert defaults.limit is None
    assert defaults.json_output is False
    assert applied.dry_run is False
    assert applied.limit == 7
    assert applied.json_output is True
    assert dry_run.dry_run is True
