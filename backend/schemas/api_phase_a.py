"""Slim API response models — avoid large JSON blobs unless explicitly requested."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind, ModelCallStatus, RunStepStatus
from backend.models.model_call import ModelCall
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


class ModelCallApiItem(BaseModel):
    """Persisted LLM invocation (request/response JSON omitted unless explicitly requested)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_run_id: UUID | None = None
    evaluation_run_id: UUID | None = None
    tool_call_id: UUID | None = None
    provider: str
    model_name: str
    prompt_id: str | None = None
    prompt_version: str | None = None
    status: ModelCallStatus
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    request_payload_json: dict | list | None = None
    response_payload_json: dict | list | None = None


def model_call_to_api_item(row: ModelCall, *, include_payloads: bool) -> ModelCallApiItem:
    return ModelCallApiItem(
        id=row.id,
        analysis_run_id=row.analysis_run_id,
        evaluation_run_id=row.evaluation_run_id,
        tool_call_id=row.tool_call_id,
        provider=row.provider,
        model_name=row.model_name,
        prompt_id=row.prompt_id,
        prompt_version=row.prompt_version,
        status=row.status,
        prompt_tokens=row.prompt_tokens,
        completion_tokens=row.completion_tokens,
        latency_ms=row.latency_ms,
        error_detail=row.error_detail,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        request_payload_json=row.request_payload_json if include_payloads else None,
        response_payload_json=row.response_payload_json if include_payloads else None,
    )
