"""
Shared orchestration constants.

Single source of truth for orchestration-owned string values that are used across
planner / executor / schema layers:
  - MCP tool names emitted by plans and consumed by the executor
  - Orchestration run status values
  - Step-level status semantics (executed MCP status vs orchestration skip)
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Default tickers when :class:`~edgar_project.orchestration.schemas.OrchestrationInput`.tickers is empty.
# Must stay aligned with ``config.DEFAULT_TICKERS`` (Phase 1); planner uses this instead of importing ``config``
# to avoid import-time filesystem side effects and MCP-layer imports.
# ---------------------------------------------------------------------------

DEFAULT_TICKERS_WHEN_INPUT_EMPTY: Final[tuple[str, ...]] = ("AAPL", "MSFT", "NVDA")

# ---------------------------------------------------------------------------
# MCP tool names used by orchestration plans/execution.
# ---------------------------------------------------------------------------

TOOL_RESOLVE_COMPANY = "resolve_company"
TOOL_FETCH_COMPANY_DATA = "fetch_company_data"
TOOL_BUILD_PANEL = "build_panel"
TOOL_COMPUTE_FEATURES = "compute_features"
TOOL_DETECT_ANOMALIES = "detect_anomalies"
TOOL_GENERATE_REPORT = "generate_report"
TOOL_RUN_PIPELINE = "run_pipeline"

# ---------------------------------------------------------------------------
# Orchestration run status values (terminal run state).
# ---------------------------------------------------------------------------

ORCH_STATUS_SUCCESS = "success"
ORCH_STATUS_PARTIAL_SUCCESS = "partial_success"
ORCH_STATUS_NO_DATA = "no_data"
ORCH_STATUS_ERROR = "error"

# ---------------------------------------------------------------------------
# Step-level status semantics.
# ---------------------------------------------------------------------------

# Step ran and returned an MCP envelope status (see mcp.schemas.ToolStatus values).
STEP_STATUS_MCP_SUCCESS = "success"
STEP_STATUS_MCP_NO_DATA = "no_data"
STEP_STATUS_MCP_ERROR = "error"

# Planner step was not executed because orchestration short-circuited/aborted.
STEP_STATUS_SKIPPED = "skipped"

# ---------------------------------------------------------------------------
# Run state contract (bump when OrchestrationRunState public shape changes).
# ---------------------------------------------------------------------------

ORCH_RUN_STATE_CONTRACT_VERSION = 1
