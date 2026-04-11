"""
Production LLM agents (intent + planning). Prompts live under ``backend/agents/prompts/``.

Execution of MCP tools is **not** performed here — only structured plans and audit records.
"""

from backend.agents.errors import AgentOutputError
from backend.agents.intent_agent import IntentAgent
from backend.agents.planning_agent import PlanningAgent
from backend.agents.prompt_loader import AgentPromptTemplate, list_prompt_versions, load_agent_prompt
from backend.agents.prompt_registry import (
    AGENT_PROMPT_IDS,
    RegisteredAgentPrompt,
    load_registered_prompt,
    registered_prompt_roles,
)
from backend.agents.ai_agents_meta import merge_ai_agents_meta
from backend.agents.runner import IntentPlanningAgentResult, run_intent_planning_agents

__all__ = [
    "AGENT_PROMPT_IDS",
    "AgentOutputError",
    "AgentPromptTemplate",
    "IntentAgent",
    "IntentPlanningAgentResult",
    "RegisteredAgentPrompt",
    "merge_ai_agents_meta",
    "PlanningAgent",
    "list_prompt_versions",
    "load_agent_prompt",
    "load_registered_prompt",
    "registered_prompt_roles",
    "run_intent_planning_agents",
]
