"""
Settings documented in `.env.example` must actually reach the containers.

A setting that `.env.example` tells an operator to set, but `docker-compose.yml` never forwards,
fails in the worst possible way: silently. The operator sets it, the container never sees it,
the code default applies, and nothing anywhere says so. Commit d350f04 fixed exactly this for
`EDGAR_BACKEND_ALLOW_GUEST_DEMO`; phase 30 hit it again with
`EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED`, where the consequence was agent runs executing on the
wrong engine and a Grafana dashboard that looked like broken instrumentation.

This test locks the current state. :data:`KNOWN_UNFORWARDED` is a **debt list, not an
allowlist** — it records settings documented today that the compose stack does not pass
through. Entries should be deleted as they are forwarded, never added to casually: a new entry
means a newly documented setting that will silently do nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_COMPOSE = _ROOT / "docker-compose.yml"
_ENV_EXAMPLE = _ROOT / ".env.example"

#: Documented settings the compose stack does not forward, as of 2026-08-07.
#:
#: Several are security-relevant — CORS origins, the auth rate limiter, the CSP header, and the
#: SQLite guard — where "operator sets it and it has no effect" means a control they believe is
#: configured is running on its code default. Shrinking this list is worthwhile work; it is not
#: phase 30's work, and it is tracked here rather than nowhere.
KNOWN_UNFORWARDED: frozenset[str] = frozenset(
    {
        # agent tuning
        "EDGAR_BACKEND_AGENT_CONTEXT_MAX_ARTIFACT_SUMMARY_ROLES",
        "EDGAR_BACKEND_AGENT_CONTEXT_MAX_COVERAGE_ROLES",
        "EDGAR_BACKEND_AGENT_CONTEXT_MAX_FINDINGS_SUMMARY_ROWS",
        "EDGAR_BACKEND_AGENT_CRITIC_MODEL",
        "EDGAR_BACKEND_AGENT_INTENT_MODEL",
        "EDGAR_BACKEND_AGENT_INTENT_PREFERENCES_MODEL",
        "EDGAR_BACKEND_AGENT_INTENT_PREFERENCES_PROMPT_VERSION",
        "EDGAR_BACKEND_AGENT_LLM_PRICING_JSON",
        "EDGAR_BACKEND_AGENT_MAX_COST_USD",
        "EDGAR_BACKEND_AGENT_MAX_ELAPSED_SECONDS",
        "EDGAR_BACKEND_AGENT_MAX_EXPERIMENTS",
        "EDGAR_BACKEND_AGENT_MAX_PARALLEL_EXPERIMENTS",
        "EDGAR_BACKEND_AGENT_PLANNING_MODEL",
        "EDGAR_BACKEND_AGENT_REPORT_MODEL",
        "EDGAR_BACKEND_ORCHESTRATION_LLM_INTENT_ASSISTANCE",
        # security-relevant — see the note above
        "EDGAR_BACKEND_ALLOW_SQLITE",
        "EDGAR_BACKEND_AUTH_RATE_LIMIT_ENABLED",
        "EDGAR_BACKEND_AUTH_RATE_LIMIT_MAX_ATTEMPTS",
        "EDGAR_BACKEND_AUTH_RATE_LIMIT_WINDOW_SECONDS",
        "EDGAR_BACKEND_CORS_ALLOW_CREDENTIALS",
        "EDGAR_BACKEND_CORS_ALLOW_ORIGINS",
        "EDGAR_BACKEND_HSTS_MAX_AGE_SECONDS",
        "EDGAR_BACKEND_SECURITY_CONTENT_SECURITY_POLICY",
        # operational
        "EDGAR_BACKEND_RETENTION_INTERVAL_SECONDS",
        "EDGAR_BACKEND_RUN_JOB_LEASE_SECONDS",
        "EDGAR_BACKEND_RUN_JOB_MAX_ATTEMPTS",
    }
)


def _forwarded() -> set[str]:
    """Env keys the shared backend anchor passes to the api and worker containers."""
    text = _COMPOSE.read_text(encoding="utf-8")
    anchor = text[text.index("x-backend-env") : text.index("\nservices:")]
    return set(re.findall(r"^\s{2}([A-Z][A-Z0-9_]*):", anchor, re.M))


def _documented() -> set[str]:
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    return {
        key
        for key in re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=", text, re.M)
        if key.startswith(("EDGAR_BACKEND_", "OPENAI_"))
    }


def test_no_newly_documented_setting_is_silently_dropped() -> None:
    """
    The regression guard. A setting added to `.env.example` without being forwarded will do
    nothing in the deployed stack, and nothing will say so.
    """
    gap = _documented() - _forwarded() - KNOWN_UNFORWARDED

    assert not gap, (
        f"documented in .env.example but not forwarded by docker-compose.yml: {sorted(gap)}. "
        "Add them to the x-backend-env anchor. If a setting genuinely should not reach the "
        "containers, remove it from .env.example rather than adding it to KNOWN_UNFORWARDED — "
        "that list is debt to pay down, not a place to park new gaps."
    )


def test_the_debt_list_does_not_grow_stale() -> None:
    """
    An entry that is now forwarded, or no longer documented, should be deleted. Left in place it
    weakens the guard above by excusing a setting that no longer needs excusing.
    """
    stale = KNOWN_UNFORWARDED & _forwarded()
    assert not stale, f"these are now forwarded — remove them from KNOWN_UNFORWARDED: {sorted(stale)}"

    gone = KNOWN_UNFORWARDED - _documented()
    assert not gone, f"these are no longer documented — remove them from KNOWN_UNFORWARDED: {sorted(gone)}"


def test_the_settings_this_stack_actually_needs_are_forwarded() -> None:
    """
    The specific ones phase 30 depends on, named so a regression is diagnosed rather than
    puzzled over.

    Without the engine flag, agent runs execute on the deterministic EDGAR chain and emit no
    `edgar_agent_*` metrics — on the dashboard that is indistinguishable from an instrumentation
    failure. Without the price table, `edgar_agent_cost_usd_total` reads zero even when real
    model calls are being billed.
    """
    forwarded = _forwarded()

    for required in (
        "EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED",
        "EDGAR_BACKEND_LLM_MODEL_PRICES",
        "EDGAR_BACKEND_OPENAI_API_KEY",
        "EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION",
    ):
        assert required in forwarded, f"{required} is not forwarded to the containers"
