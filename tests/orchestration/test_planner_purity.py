"""
Guardrails for planner purity: no MCP execution, no SEC/network, no artifact I/O.

The planner only emits :class:`~edgar_project.orchestration.schemas.PlannedStep` data;
see :mod:`edgar_project.orchestration.planner` module docstring.
"""

from __future__ import annotations

import inspect

from edgar_project.orchestration.constants import DEFAULT_TICKERS_WHEN_INPUT_EMPTY, TOOL_RESOLVE_COMPANY
from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.schemas import OrchestrationInput


def test_planner_module_avoids_mcp_and_config_import_paths() -> None:
    """Regression: planner must not pull MCP adapters or ``import config`` (side effects)."""
    import edgar_project.orchestration.planner as planner_mod

    src = inspect.getsource(planner_mod)
    assert "mcp.adapters" not in src
    assert "mcp.tools" not in src
    assert "import config" not in src


def test_empty_tickers_use_orchestration_default_constants() -> None:
    """Empty ticker list resolves via constants (aligned with Phase 1 defaults), no config import."""
    out = Planner().build_plan(
        OrchestrationInput(
            tickers=[],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    assert out.ok and out.plan is not None
    first_ticker = DEFAULT_TICKERS_WHEN_INPUT_EMPTY[0]
    assert out.plan.steps[0].tool_name == TOOL_RESOLVE_COMPANY
    assert out.plan.steps[0].tool_input["ticker"] == first_ticker
