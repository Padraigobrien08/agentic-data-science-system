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
