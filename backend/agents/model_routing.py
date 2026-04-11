"""
Resolve chat ``model`` id per agent phase from :class:`~backend.config.settings.Settings`.

Phase-specific env vars (non-empty) override :attr:`Settings.agent_completion_model`.
Used for audit metadata and :class:`~backend.models.model_call.ModelCall` requests; the
provider may still normalize the id in the completion response (persisted on ``ModelCall``).
"""

from __future__ import annotations

from typing import Literal

from backend.config.settings import Settings

AgentCompletionPhase = Literal[
    "intent",
    "intent_preferences",
    "planning",
    "critic",
    "report",
]

# Name of the Settings field that supplied the resolved model (for logs / meta_json).
SETTINGS_FIELD_AGENT_COMPLETION_MODEL = "agent_completion_model"


def resolve_agent_completion_model(settings: Settings, phase: AgentCompletionPhase) -> tuple[str, str]:
    """
    Return ``(model_id, routing_source)`` where ``routing_source`` is the settings attribute
    name that won (for inspectability). Empty phase-specific fields fall through to the next
    rule, ending at :attr:`Settings.agent_completion_model`.
    """
    default = (settings.agent_completion_model or "").strip()
    if not default:
        default = "gpt-5.4-mini"

    if phase == "intent":
        m = (settings.agent_intent_model or "").strip()
        if m:
            return m, "agent_intent_model"
        return default, SETTINGS_FIELD_AGENT_COMPLETION_MODEL

    if phase == "intent_preferences":
        m = (settings.agent_intent_preferences_model or "").strip()
        if m:
            return m, "agent_intent_preferences_model"
        m_intent = (settings.agent_intent_model or "").strip()
        if m_intent:
            return m_intent, "agent_intent_model"
        return default, SETTINGS_FIELD_AGENT_COMPLETION_MODEL

    if phase == "planning":
        m = (settings.agent_planning_model or "").strip()
        if m:
            return m, "agent_planning_model"
        return default, SETTINGS_FIELD_AGENT_COMPLETION_MODEL

    if phase == "critic":
        m = (settings.agent_critic_model or "").strip()
        if m:
            return m, "agent_critic_model"
        return default, SETTINGS_FIELD_AGENT_COMPLETION_MODEL

    if phase == "report":
        m = (settings.agent_report_model or "").strip()
        if m:
            return m, "agent_report_model"
        return default, SETTINGS_FIELD_AGENT_COMPLETION_MODEL

    raise AssertionError(f"unknown phase: {phase!r}")


def completion_model_audit_dict(
    *,
    model_call_model_name: str,
    routing_source: str,
    phase: AgentCompletionPhase,
) -> dict[str, str]:
    """Structured snippet for ``meta_json`` / request_metadata (provider truth + config source)."""
    return {
        "phase": phase,
        "model_name": model_call_model_name,
        "routing_source": routing_source,
    }
