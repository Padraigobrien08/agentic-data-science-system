"""Typed request/response contract for deterministic prompt-routing previews."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from backend.schemas.common import OrmSchema
from edgar_project.orchestration.schemas import InterpretedGoalCode, OrchestrationIntent, PlanTemplateId


class PromptRoutingPreviewRequest(OrmSchema):
    """Preview payload for deterministic routing without creating a run row."""

    project_id: UUID
    analysis_goal: str = Field(..., min_length=1)
    tickers: list[str] = Field(default_factory=list)
    refresh: bool = False


class PromptRoutingPreviewResponse(OrmSchema):
    """Deterministic routing preview surface returned to chat and other callers."""

    supported: bool
    routing_source: Literal["deterministic"]
    effective_tickers: list[str] = Field(default_factory=list)
    out_of_scope_tickers: list[str] = Field(default_factory=list)
    rewrite_suggestions: list[str] = Field(default_factory=list)
    reason: str | None = None
    intent: OrchestrationIntent | None = None
    goal_code: InterpretedGoalCode | None = None
    plan_template_id: PlanTemplateId | None = None
