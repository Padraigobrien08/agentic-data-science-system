"""MCP tool names the planning agent may emit (inspectable; executor still validates)."""

from __future__ import annotations

from edgar_project.orchestration.constants import (
    TOOL_BUILD_PANEL,
    TOOL_COMPUTE_FEATURES,
    TOOL_DETECT_ANOMALIES,
    TOOL_FETCH_COMPANY_DATA,
    TOOL_GENERATE_REPORT,
    TOOL_RESOLVE_COMPANY,
    TOOL_RUN_PIPELINE,
)

PLANNING_ALLOWED_TOOL_NAMES: tuple[str, ...] = (
    TOOL_RESOLVE_COMPANY,
    TOOL_FETCH_COMPANY_DATA,
    TOOL_BUILD_PANEL,
    TOOL_COMPUTE_FEATURES,
    TOOL_DETECT_ANOMALIES,
    TOOL_GENERATE_REPORT,
    TOOL_RUN_PIPELINE,
)
