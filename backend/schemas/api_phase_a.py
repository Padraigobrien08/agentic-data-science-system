"""Slim API response models — avoid large JSON blobs unless explicitly requested."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind, RunStepStatus
from backend.models.run_step import RunStep


class AnalysisRunSummary(BaseModel):
    """Run listing and default single-run view (no payload JSON)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    initiated_by_user_id: UUID | None = None
    correlation_id: str | None = None
    status: AnalysisRunStatus
    orchestration_goal_text: str | None = None
    error_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisRunDetailResponse(AnalysisRunSummary):
    """Single run with optional large JSON fields (gated by query param in the route)."""

    input_payload_json: dict | list | None = None
    output_payload_json: dict | list | None = None
    meta_json: dict | list | None = None


def analysis_run_to_summary(row: AnalysisRun) -> AnalysisRunSummary:
    return AnalysisRunSummary.model_validate(row)


def analysis_run_to_detail(row: AnalysisRun, *, include_payloads: bool) -> AnalysisRunDetailResponse:
    base = analysis_run_to_summary(row)
    if not include_payloads:
        return AnalysisRunDetailResponse(
            **base.model_dump(),
            input_payload_json=None,
            output_payload_json=None,
            meta_json=None,
        )
    return AnalysisRunDetailResponse(
        **base.model_dump(),
        input_payload_json=row.input_payload_json,
        output_payload_json=row.output_payload_json,
        meta_json=row.meta_json,
    )


class RunStepListItem(BaseModel):
    """Step row without planner tool input / meta JSON."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_run_id: UUID
    step_index: int
    status: RunStepStatus
    label: str | None = None
    planned_tool_name: str | None = None
    detail: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RunStepDetailItem(RunStepListItem):
    planner_tool_input_json: dict | list | None = None
    meta_json: dict | list | None = None


def run_step_to_list_item(row: RunStep) -> RunStepListItem:
    return RunStepListItem.model_validate(row)


def run_step_to_detail(row: RunStep, *, include_payloads: bool) -> RunStepDetailItem:
    item = run_step_to_list_item(row)
    if not include_payloads:
        return RunStepDetailItem(**item.model_dump(), planner_tool_input_json=None, meta_json=None)
    return RunStepDetailItem(
        **item.model_dump(),
        planner_tool_input_json=row.planner_tool_input_json,
        meta_json=row.meta_json,
    )


class ArtifactMetadata(BaseModel):
    """Artifact row without file bytes (``storage_uri`` is a locator, not content)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_run_id: UUID | None = None
    evaluation_run_id: UUID | None = None
    run_step_id: UUID | None = None
    role_key: str
    kind: ArtifactKind
    mime_type: str | None = None
    byte_size: int | None = None
    content_sha256: str | None = None
    storage_uri: str = Field(description="Backend-specific object locator (e.g. local:…)")
    created_at: datetime
    updated_at: datetime


class ArtifactDetailResponse(ArtifactMetadata):
    """Single-artifact view; ``meta_json`` only when requested."""

    meta_json: dict | list | None = None


def artifact_to_metadata(row: Artifact) -> ArtifactMetadata:
    return ArtifactMetadata.model_validate(row)


def artifact_to_detail(row: Artifact, *, include_meta: bool) -> ArtifactDetailResponse:
    base = artifact_to_metadata(row)
    return ArtifactDetailResponse(
        **base.model_dump(),
        meta_json=row.meta_json if include_meta else None,
    )
