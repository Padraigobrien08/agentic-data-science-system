"""Evaluation run schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import EvaluationRunStatus
from backend.schemas.common import OrmSchema, TimestampedRead


class EvaluationRunCreate(OrmSchema):
    suite_id: str = Field(max_length=256)
    suite_manifest_path: str | None = Field(default=None, max_length=1024)
    project_id: UUID | None = None
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
