"""Per-phase completion model resolution (settings fallbacks)."""

from __future__ import annotations

from backend.agents.model_routing import (
    SETTINGS_FIELD_AGENT_COMPLETION_MODEL,
    resolve_agent_completion_model,
)
from backend.config.settings import Settings


def test_resolve_defaults_to_agent_completion_model() -> None:
    s = Settings(
        agent_completion_model="gpt-5.4-mini",
        agent_intent_model="",
        agent_planning_model="",
        agent_critic_model="",
        agent_report_model="",
        agent_intent_preferences_model="",
    )
    m, src = resolve_agent_completion_model(s, "intent")
    assert m == "gpt-5.4-mini"
    assert src == SETTINGS_FIELD_AGENT_COMPLETION_MODEL


def test_resolve_phase_overrides() -> None:
    s = Settings(
        agent_completion_model="expensive",
        agent_intent_model="cheap-intent",
        agent_planning_model="cheap-plan",
        agent_critic_model="cheap-critic",
        agent_report_model="cheap-report",
        agent_intent_preferences_model="",
    )
    assert resolve_agent_completion_model(s, "intent")[0] == "cheap-intent"
    assert resolve_agent_completion_model(s, "planning")[0] == "cheap-plan"
    assert resolve_agent_completion_model(s, "critic")[0] == "cheap-critic"
    assert resolve_agent_completion_model(s, "report")[0] == "cheap-report"


def test_intent_preferences_fallback_chain() -> None:
    s = Settings(
        agent_completion_model="base",
        agent_intent_model="intent-only",
        agent_intent_preferences_model="",
    )
    assert resolve_agent_completion_model(s, "intent_preferences") == (
        "intent-only",
        "agent_intent_model",
    )
    s2 = Settings(
        agent_completion_model="base",
        agent_intent_model="",
        agent_intent_preferences_model="pref-only",
    )
    assert resolve_agent_completion_model(s2, "intent_preferences")[0] == "pref-only"
