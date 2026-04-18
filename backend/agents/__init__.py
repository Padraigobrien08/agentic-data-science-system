"""
Production LLM agents (intent + planning). Prompts live under ``backend/agents/prompts/``.

Execution of MCP tools is **not** performed here — only structured plans and audit records.
"""

from __future__ import annotations

from importlib import import_module

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


def __getattr__(name: str):
    if name == "AgentOutputError":
        return import_module("backend.agents.errors").AgentOutputError
    if name == "IntentAgent":
        return import_module("backend.agents.intent_agent").IntentAgent
    if name == "PlanningAgent":
        return import_module("backend.agents.planning_agent").PlanningAgent
    if name in {"AgentPromptTemplate", "list_prompt_versions", "load_agent_prompt"}:
        loader = import_module("backend.agents.prompt_loader")
        return getattr(loader, name)
    if name in {
        "AGENT_PROMPT_IDS",
        "RegisteredAgentPrompt",
        "load_registered_prompt",
        "registered_prompt_roles",
    }:
        registry = import_module("backend.agents.prompt_registry")
        return getattr(registry, name)
    if name == "merge_ai_agents_meta":
        return import_module("backend.agents.ai_agents_meta").merge_ai_agents_meta
    if name in {"IntentPlanningAgentResult", "run_intent_planning_agents"}:
        runner = import_module("backend.agents.runner")
        return getattr(runner, name)
    raise AttributeError(name)
