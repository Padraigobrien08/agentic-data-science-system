"""Retention maintenance regressions for schema surfacing and operator workflows."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import SecretStr

from backend.config.settings import Settings
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, ModelCallStatus
from backend.models.model_call import ModelCall
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
