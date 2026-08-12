"""Pytest hooks — set env before ``backend.config.settings`` is first loaded."""

from __future__ import annotations

import os

# Stable secret for JWT in tests (must be ≥32 chars when debug is false).
os.environ.setdefault(
    "EDGAR_BACKEND_JWT_SECRET",
    "pytest-jwt-secret-minimum-32-characters-long-x",
)
os.environ.setdefault("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "true")
os.environ.setdefault("EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN", "pytest-bootstrap-token")
os.environ.setdefault("EDGAR_BACKEND_OPS_API_TOKEN", "pytest-ops-token")

# The MCP limiter is process-wide, so every tool call in the whole session shares one bucket
# and the suite would start failing on volume rather than on behaviour — a flake that appears
# only once enough MCP tests exist, and looks like a broken tool rather than a full budget.
# Tests that exercise the limiter build their own with explicit settings.
os.environ.setdefault("EDGAR_BACKEND_MCP_RATE_LIMIT_ENABLED", "false")


# --- no live model calls from the test suite --------------------------------
#
# Settings read the repo-root ``.env``, so on a developer machine holding a real key the suite
# runs against a live provider by default. Any code path reaching ``get_settings()`` and
# building a policy then calls OpenAI and bills the operator — silently, at whatever
# concurrency the test happens to use.
#
# Not hypothetical: a replay-route test monkeypatched ``build_agent_policy`` on the wrong
# module with ``raising=False``, the patch became a no-op, and the test spent real money while
# appearing to pass. A per-test patch is the wrong place for this control, because forgetting
# it is silent and the cost lands on someone who was not watching.
#
# Assignment rather than ``setdefault``: the point is to override whatever ``.env`` or the
# shell says. Tests that construct ``Settings(llm_provider="openai", openai_api_key=...)``
# explicitly are unaffected — init arguments outrank the environment — so a test that
# deliberately builds a provider still works, and the ``integration``-marked live smoke test
# still opts in through ``OPENAI_API_KEY``.
#
# To run against a real provider on purpose:
#     EDGAR_TESTS_ALLOW_LIVE_LLM=1 OPENAI_API_KEY=sk-... pytest -m integration
LIVE_LLM_OPT_IN = "EDGAR_TESTS_ALLOW_LIVE_LLM"

if os.environ.get(LIVE_LLM_OPT_IN) != "1":
    # ``off`` makes the factory raise LLMProviderConfigurationError, which every caller already
    # handles by degrading to the deterministic FixtureAgentPolicy — the posture CI runs in, so
    # a local run now behaves like CI rather than like production.
    os.environ["EDGAR_BACKEND_LLM_PROVIDER"] = "off"
    # Blanked as well as disabled, so a test that flips the provider back on mid-run finds no
    # credential and still cannot reach the network.
    os.environ["EDGAR_BACKEND_OPENAI_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
