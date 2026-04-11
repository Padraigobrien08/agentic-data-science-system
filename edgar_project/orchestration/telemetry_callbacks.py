"""
Optional callbacks for observability (metrics/tracing) without importing application code.

The API / worker process registers :func:`register_mcp_tool_callback` at startup; the executor
invokes :func:`notify_mcp_tool` after each MCP dispatch. If no callback is registered, calls are
no-ops.
"""

from __future__ import annotations

from collections.abc import Callable

_mcp_tool_callback: Callable[[str, str], None] | None = None


def register_mcp_tool_callback(fn: Callable[[str, str], None] | None) -> None:
    """Set the MCP tool metrics/log hook (``tool_name``, ``status``). Pass ``None`` to clear."""
    global _mcp_tool_callback
    _mcp_tool_callback = fn


def notify_mcp_tool(tool_name: str, status: str) -> None:
    """Executor calls this after each MCP tool attempt (including ``dispatch_exception``)."""
    cb = _mcp_tool_callback
    if cb is not None:
        try:
            cb(tool_name, status)
        except Exception:
            pass
