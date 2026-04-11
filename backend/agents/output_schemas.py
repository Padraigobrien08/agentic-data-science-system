"""Pydantic shapes for LLM JSON (mapped to orchestration schemas — no tool execution)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationIntent,
    PlannedStep,
)

from backend.agents.tool_allowlist import PLANNING_ALLOWED_TOOL_NAMES


class IntentAgentLLMOutput(BaseModel):
    """Strict JSON object expected from the intent model."""

    model_config = ConfigDict(extra="forbid")

    code: str
    intent: str | None = None
    description: str = Field(..., max_length=512)
    user_goal_text: str
    intent_rules_matched: list[str] = Field(default_factory=list)

    def to_interpreted_goal(self) -> InterpretedGoal:
        try:
            code_enum = InterpretedGoalCode(self.code)
        except ValueError as exc:
            raise ValueError(f"Invalid InterpretedGoalCode: {self.code!r}") from exc
        orch_intent: OrchestrationIntent | None = None
        if self.intent:
            try:
                orch_intent = OrchestrationIntent(self.intent)
            except ValueError as exc:
                raise ValueError(f"Invalid OrchestrationIntent: {self.intent!r}") from exc
        rules = list(self.intent_rules_matched) if self.intent_rules_matched else ["llm_intent_agent"]
        return InterpretedGoal(
            code=code_enum,
            intent=orch_intent,
            intent_rules_matched=rules,
            description=self.description[:512],
            user_goal_text=self.user_goal_text,
        )


class PlanningStepLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=0)
    tool_name: str
    tool_input: dict[str, Any] = Field(default_factory=dict)
    label: str = ""

    @model_validator(mode="before")
    @classmethod
    def _params_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "params" in data and "tool_input" not in data:
            data = dict(data)
            data["tool_input"] = data.pop("params")
        return data

    @field_validator("tool_name")
    @classmethod
    def _allowed_tool(cls, v: str) -> str:
        if v not in PLANNING_ALLOWED_TOOL_NAMES:
            raise ValueError(
                f"tool_name {v!r} not in allowed set: {PLANNING_ALLOWED_TOOL_NAMES!r}"
            )
        return v


class PlanningAgentLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[PlanningStepLLM] = Field(default_factory=list)

    def to_planned_steps(self) -> list[PlannedStep]:
        out: list[PlannedStep] = []
        for s in sorted(self.steps, key=lambda x: x.order):
            out.append(
                PlannedStep(
                    order=s.order,
                    tool_name=s.tool_name,
                    tool_input=s.tool_input,
                    label=s.label or f"{s.tool_name}:{s.order}",
                )
            )
        return out
