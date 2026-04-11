"""Fill ``{{PLACEHOLDER}}`` slots in versioned prompt files."""

from __future__ import annotations

from edgar_project.orchestration.schemas import InterpretedGoalCode, OrchestrationIntent

from backend.agents.tool_allowlist import PLANNING_ALLOWED_TOOL_NAMES


def render_intent_prompt(system_body: str) -> str:
    codes = "\n".join(f"- `{c.value}` — *{c.name}*" for c in InterpretedGoalCode)
    intents = "\n".join(f"- `{i.value}`" for i in OrchestrationIntent)
    return (
        system_body.replace("{{ALLOWED_GOAL_CODES}}", codes).replace(
            "{{ALLOWED_ORCHESTRATION_INTENTS}}", intents
        )
    )


def render_planning_prompt(system_body: str) -> str:
    names = "\n".join(f"- `{n}`" for n in PLANNING_ALLOWED_TOOL_NAMES)
    return system_body.replace("{{ALLOWED_TOOL_NAMES}}", names)
