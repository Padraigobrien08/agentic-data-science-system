"""Evaluation run schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import EvaluationRunStatus
from backend.schemas.common import OrmSchema, TimestampedRead
from edgar_project.evaluation.schemas import InputMode


class EvaluationRunCreate(OrmSchema):
    suite_id: str = Field(max_length=256)
    project_id: UUID
    config_json: dict | list | None = None
    notes: str | None = None


class EvaluationRunUpdate(OrmSchema):
    status: EvaluationRunStatus | None = None
    summary_json: dict | list | None = None
    results_json: dict | list | None = None
    config_json: dict | list | None = None
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class EvaluationRunRead(TimestampedRead):
    id: UUID
    project_id: UUID | None
    initiated_by_user_id: UUID | None
    suite_id: str
    suite_manifest_path: str | None
    status: EvaluationRunStatus
    notes: str | None
    summary_json: dict | list | None = None
    results_json: dict | list | None = None
    config_json: dict | list | None = None
    started_at: datetime | None
    finished_at: datetime | None
    case_count: int | None = None


class SupportedEvaluationSuiteRead(OrmSchema):
    suite_id: str
    label: str
    primary_mode: InputMode
    description: str = ""


class EvaluationRunStartRequest(OrmSchema):
    allow_live: bool = False


def evaluation_run_to_read(
    row,
    *,
    case_count: int | None = None,
) -> EvaluationRunRead:
    return EvaluationRunRead(
        id=row.id,
        project_id=row.project_id,
        initiated_by_user_id=row.initiated_by_user_id,
        suite_id=row.suite_id,
        suite_manifest_path=row.suite_manifest_path,
        status=row.status,
        notes=row.notes,
        summary_json=row.summary_json,
        results_json=row.results_json,
        config_json=row.config_json,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        case_count=case_count,
    )
