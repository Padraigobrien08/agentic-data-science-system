"""
Semantic validation for LLM-produced plans before any future executor handoff.

Production runs use the deterministic planner; this guards :class:`~backend.agents.planning_agent.PlanningAgent`
outputs so prompts cannot emit empty or structurally invalid step lists.
"""

from __future__ import annotations

from edgar_project.orchestration.schemas import PlannedStep

from backend.agents.errors import AgentFailureCode, AgentOutputError
from backend.agents.tool_allowlist import PLANNING_ALLOWED_TOOL_NAMES


def validate_llm_planned_steps_for_handoff(steps: list[PlannedStep]) -> None:
    """
    Ensure the model produced an executable non-empty plan with sane ordering and known tools.

    Raises:
        AgentOutputError: with :attr:`AgentOutputError.code` set for trace classification.
    """
    if not steps:
        raise AgentOutputError(
            "Planning model produced an empty step list (no tools to execute).",
            code=AgentFailureCode.MODEL_SEMANTIC,
        )
    orders = sorted(s.order for s in steps)
    expected = list(range(len(steps)))
    if orders != expected:
        raise AgentOutputError(
            f"Planning model step orders must be contiguous from 0..n-1; got {orders!r}",
            code=AgentFailureCode.MODEL_SEMANTIC,
        )
    for s in steps:
        if s.tool_name not in PLANNING_ALLOWED_TOOL_NAMES:
            raise AgentOutputError(
                f"Planning model referenced disallowed tool {s.tool_name!r} "
                f"(not in executor dispatch set).",
                code=AgentFailureCode.MODEL_SEMANTIC,
            )
