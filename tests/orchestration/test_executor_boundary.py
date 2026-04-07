"""
Executor is the only orchestration module that invokes MCP tools.

Guards are source-level regressions; behavior is covered in ``test_phase3_orchestration``.
"""

from __future__ import annotations

import inspect


def test_executor_module_does_not_import_planner_or_intent() -> None:
    import edgar_project.orchestration.executor as ex

    src = inspect.getsource(ex)
    assert "from edgar_project.orchestration.planner import" not in src
    assert "interpret_goal_intent" not in src
    assert "Planner(" not in src


def test_executor_only_mcp_entry_is_tools_package() -> None:
    """Orchestration must not call Phase 1 directly; MCP tools are the boundary."""
    import edgar_project.orchestration.executor as ex

    src = inspect.getsource(ex)
    assert "from edgar_project.mcp import tools as mcp_tools" in src
    assert "import src." not in src
    assert "from src." not in src
    assert "pipeline_runner" not in src
