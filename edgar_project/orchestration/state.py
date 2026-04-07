"""
Mutable state for a single orchestration run.

Holds the input, plan, step history, and run-level flags. The executor updates
this object as steps complete; it is not persisted unless the caller serializes it.

Serialization: all fields are intended to round-trip via
``model_dump(mode="json")`` / ``model_validate_json`` (plus ISO datetimes on
:class:`StepRecord`). There is no hidden process-local state beyond what is on
this model. Bump :attr:`contract_version` when the public shape changes.
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from edgar_project.orchestration.constants import ORCH_RUN_STATE_CONTRACT_VERSION
from edgar_project.orchestration.params import json_safe_tool_params
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    JsonDict,
    OrchestrationError,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationPlan,
    OrchestrationRunStatus,
    OrchestrationWarning,
    ResolvedCompany,
    StepRecord,
    StepStatusEntry,
    ToolCallStep,
    ToolResultSummary,
)


class OrchestrationRunState(BaseModel):
    """
    In-memory state for one orchestration execution.

    Lifecycle (intended):
      1. Built from :class:`OrchestrationInput`, or from
         :meth:`~edgar_project.orchestration.execution_contract.ExecutionRequest.to_run_state` (executor entry).
      2. ``plan`` / ``interpreted_goal`` are set before MCP steps run.
      3. Executor appends :class:`StepRecord` entries and updates ``current_step_index``.
      4. :meth:`to_output` builds terminal :class:`OrchestrationOutput` (executor); the coordinator does not touch this object after dispatch.

    ``current_step_index`` is always kept equal to ``len(steps_completed)``; after
    deserialization, validation normalizes a mismatched cursor.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=False)

    contract_version: int = Field(
        default=ORCH_RUN_STATE_CONTRACT_VERSION,
        ge=1,
        description="Increment when this model's JSON shape changes (cross-process compatibility).",
    )
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    request: OrchestrationInput
    plan: OrchestrationPlan | None = None
    interpreted_goal: InterpretedGoal | None = None
    steps_completed: list[StepRecord] = Field(default_factory=list)
    current_step_index: int = 0
    aborted: bool = False
    abort_reason: str | None = None
    context: JsonDict = Field(
        default_factory=dict,
        description="Scratch JSON for planner/executor (e.g. resolved CIKs); no opaque objects.",
    )

    @model_validator(mode="after")
    def _sync_step_cursor(self) -> OrchestrationRunState:
        """Keep the step cursor consistent with recorded steps (safe after JSON round-trip)."""
        expected = len(self.steps_completed)
        if self.current_step_index != expected:
            self.current_step_index = expected
        return self

    def record_step(self, record: StepRecord) -> None:
        """Append a finished step and advance the cursor."""
        self.steps_completed.append(record)
        self.current_step_index = len(self.steps_completed)

    def executed_tool_call_sequence(self) -> list[ToolCallStep]:
        """
        Ordered MCP tools actually run (from :attr:`steps_completed` and the plan).

        Skipped steps (e.g. build_panel not dispatched) do not appear.
        """
        if not self.plan:
            return []
        by_order = {s.order: s for s in self.plan.steps}
        out: list[ToolCallStep] = []
        for rec in self.steps_completed:
            ps = by_order.get(rec.order)
            if ps is None:
                continue
            out.append(
                ToolCallStep(
                    order=rec.order,
                    tool_name=rec.tool_name,
                    params=json_safe_tool_params(ps.tool_input),
                )
            )
        return out

    def to_output(
        self,
        *,
        status: OrchestrationRunStatus,
        message: str,
        interpreted_goal: InterpretedGoal,
        resolved_companies: list[ResolvedCompany] | None = None,
        tool_call_sequence: list[ToolCallStep] | None = None,
        tool_results_summary: list[ToolResultSummary] | None = None,
        artifact_paths: dict[str, str] | None = None,
        final_report_path: str | None = None,
        errors: list[OrchestrationError] | None = None,
        warnings: list[OrchestrationWarning] | None = None,
        final_summary: str = "",
        step_statuses: list[StepStatusEntry] | None = None,
    ) -> OrchestrationOutput:
        """Build a terminal :class:`OrchestrationOutput` from current state."""
        return OrchestrationOutput(
            run_id=self.run_id,
            status=status,
            message=message,
            final_summary=final_summary,
            interpreted_goal=interpreted_goal,
            resolved_companies=list(resolved_companies or []),
            tool_call_sequence=list(tool_call_sequence or []),
            tool_results_summary=list(tool_results_summary or []),
            step_statuses=list(step_statuses or []),
            artifact_paths=dict(artifact_paths or {}),
            final_report_path=final_report_path,
            errors=list(errors or []),
            warnings=list(warnings or []),
        )
