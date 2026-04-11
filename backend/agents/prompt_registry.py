"""
Stable prompt identifiers + explicit versions for agent LLM calls.

Prompt bodies stay on disk under ``backend/agents/prompts/<role>/<file_version>.md`` (see
:mod:`backend.agents.prompt_loader`). This module maps each **role** to a stable **prompt_id**
and resolves the loaded template so callers persist ``prompt_id`` + ``prompt_version`` on
:class:`~backend.models.model_call.ModelCall` rows.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.agents.prompt_loader import AgentPromptTemplate, load_agent_prompt

# Stable IDs for audit / analytics (do not rename once shipped; add new IDs for new agents).
AGENT_PROMPT_IDS: dict[str, str] = {
    "intent": "edgar.agent.intent",
    "planning": "edgar.agent.planning",
    "critic": "edgar.agent.critic",
    "report": "edgar.agent.report",
}


@dataclass(frozen=True)
class RegisteredAgentPrompt:
    """Resolved in-repo prompt with registry identity."""

    prompt_id: str
    prompt_version: str
    template: AgentPromptTemplate


def registered_prompt_roles() -> frozenset[str]:
    return frozenset(AGENT_PROMPT_IDS)


def load_registered_prompt(role: str, file_version: str) -> RegisteredAgentPrompt:
    """
    Load ``prompts/{role}/{file_version}.md`` and attach stable ``prompt_id``.

    ``prompt_version`` is the explicit version from the template (front matter or filename).
    """
    if role not in AGENT_PROMPT_IDS:
        raise ValueError(f"Unknown agent prompt role: {role!r}; expected one of {sorted(AGENT_PROMPT_IDS)}")
    tmpl = load_agent_prompt(role, file_version)
    return RegisteredAgentPrompt(
        prompt_id=AGENT_PROMPT_IDS[role],
        prompt_version=tmpl.version,
        template=tmpl,
    )
