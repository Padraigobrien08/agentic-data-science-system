"""Register cross-package hooks (e.g. MCP metrics from orchestration executor)."""

from __future__ import annotations

from backend.observability.metrics import observe_mcp_tool
from edgar_project.orchestration.telemetry_callbacks import register_mcp_tool_callback


def install_edgar_telemetry_hooks() -> None:
    """Idempotent-safe: re-register the same callback."""
    register_mcp_tool_callback(observe_mcp_tool)
