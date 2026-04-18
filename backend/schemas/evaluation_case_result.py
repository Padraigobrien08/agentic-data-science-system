"""Case-level stored evaluation result schemas."""

from __future__ import annotations

from uuid import UUID

from edgar_project.evaluation.schemas import (
    EvaluationStatus,
    InputMode,
    ValidationDegradationClass,
)

from backend.schemas.common import TimestampedRead


class EvaluationCaseResultRead(TimestampedRead):
    id: UUID
    evaluation_run_id: UUID
    case_id: str
    input_mode: InputMode
    status: EvaluationStatus
    degradation_class: ValidationDegradationClass
    run_goal: str
    message: str
    policy_json: dict | list | None = None
    observation_json: dict | list | None = None
    checks_json: dict | list | None = None
    metadata_json: dict | list | None = None
    artifacts_json: dict | list | None = None
    latest_analysis_run_id: UUID | None = None
    latest_analysis_run_status: str | None = None
    analysis_run_history_json: dict | list | None = None


def evaluation_case_result_to_read(row) -> EvaluationCaseResultRead:
    return EvaluationCaseResultRead(
        id=row.id,
        evaluation_run_id=row.evaluation_run_id,
        case_id=row.case_id,
        input_mode=row.input_mode,
        status=row.status,
        degradation_class=row.degradation_class,
        run_goal=row.run_goal,
        message=row.message,
        policy_json=row.policy_json,
        observation_json=row.observation_json,
        checks_json=row.checks_json,
        metadata_json=row.metadata_json,
        artifacts_json=row.artifacts_json,
        latest_analysis_run_id=row.latest_analysis_run_id,
        latest_analysis_run_status=row.latest_analysis_run_status,
        analysis_run_history_json=row.analysis_run_history_json,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
