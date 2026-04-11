"""Request/response for synchronous EDGAR pipeline execution."""

from __future__ import annotations

from uuid import UUID

from backend.models.enums import AnalysisRunStatus
from backend.schemas.common import OrmSchema


class ExecuteRunOverrides(OrmSchema):
    """Optional overrides for this execution only (DB row is unchanged)."""

    tickers: list[str] | None = None
    analysis_goal: str | None = None
    refresh: bool | None = None


class ExecuteRunResponse(OrmSchema):
    """Summary after orchestration (no full ``OrchestrationOutput`` by default)."""

    analysis_run_id: UUID
    orchestration_run_id: str
    orchestration_status: str
    message: str
    final_summary: str = ""
    artifact_count: int = 0
    db_status: AnalysisRunStatus
