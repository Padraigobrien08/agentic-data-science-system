"""
Planner ↔ executor boundary (in-process; designed like a future worker RPC payload).

* :class:`ExecutionRequest` — everything the executor needs after planning succeeds.
* :class:`ExecutionResult` — alias of :class:`~edgar_project.orchestration.schemas.OrchestrationOutput`
  (same public response shape; explicit name for the worker return type).

The coordinator builds :class:`ExecutionRequest` from :class:`~edgar_project.orchestration.schemas.PlanningOutcome`
plus ``run_id`` correlation; it does not pass a mutable :class:`~edgar_project.orchestration.state.OrchestrationRunState`
across this boundary (the executor still builds run state in-process).
"""

from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from edgar_project.orchestration.constants import ORCH_RUN_STATE_CONTRACT_VERSION
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    JsonDict,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationPlan,
    PlanningOutcome,
    RunWorkspacePayload,
)

ExecutionResult: TypeAlias = OrchestrationOutput
"""Worker return type; identical schema to :class:`OrchestrationOutput`."""


class ExecutionRequest(BaseModel):
    """
    Serializable input to :class:`~edgar_project.orchestration.executor.Executor`.

    Maps cleanly from a successful :class:`PlanningOutcome` plus ``run_id`` from the coordinator.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="Correlation id for this run (from coordinator).")
    request: OrchestrationInput = Field(..., description="Original validated orchestration input.")
    plan: OrchestrationPlan = Field(..., description="Plan from the planner (MCP tool sequence).")
    interpreted_goal: InterpretedGoal | None = Field(
        default=None,
        description="Structured goal from planning; may be None only if tests construct manually.",
    )
    contract_version: int = Field(
        default=ORCH_RUN_STATE_CONTRACT_VERSION,
        ge=1,
        description="Must match :class:`~edgar_project.orchestration.state.OrchestrationRunState` contract.",
    )
    context: JsonDict = Field(
        default_factory=dict,
        description=(
            "Optional JSON scratch for coordinator ↔ executor data. "
            "Reserved key: ``context['run_workspace']`` stores a serialized "
            ":class:`~edgar_project.orchestration.schemas.RunWorkspacePayload`."
        ),
    )

    def run_workspace_payload(self) -> RunWorkspacePayload | None:
        """Return a validated ``run_workspace`` payload when the coordinator provided one."""
        raw_payload = self.context.get("run_workspace")
        if not isinstance(raw_payload, dict):
            return None
        return RunWorkspacePayload.model_validate(raw_payload)

    @classmethod
    def from_planning(
        cls,
        *,
        run_id: str,
        request: OrchestrationInput,
        outcome: PlanningOutcome,
    ) -> ExecutionRequest:
        """
        Build from a successful planning outcome.

        Raises:
            ValueError: if ``outcome.ok`` is false or ``plan`` is missing.
        """
        if not outcome.ok or outcome.plan is None:
            msg = "PlanningOutcome must be ok with a non-null plan"
            raise ValueError(msg)
        if not outcome.plan.steps:
            msg = (
                "Execution handoff rejected: planner produced an empty plan (no PlannedStep rows). "
                "The deterministic executor must not run without at least one tool step."
            )
            raise ValueError(msg)
        return cls(
            run_id=run_id,
            request=request,
            plan=outcome.plan,
            interpreted_goal=outcome.interpreted_goal,
        )

    def to_run_state(self) -> "OrchestrationRunState":
        """Materialize mutable run state for the in-process executor implementation."""
        from edgar_project.orchestration.state import OrchestrationRunState

        return OrchestrationRunState(
            run_id=self.run_id,
            request=self.request,
            plan=self.plan,
            interpreted_goal=self.interpreted_goal,
            contract_version=self.contract_version,
            context=dict(self.context),
        )
