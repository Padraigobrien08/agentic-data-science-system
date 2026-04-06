"""
MCP stdio server entrypoint (scaffolding).

This module does **not** import pipeline code at load time beyond path setup; full wiring
happens in ``tools.py`` once handlers are implemented.
"""

from __future__ import annotations

import logging

from .adapters import ensure_sys_path

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Start the MCP server (stdio).

    Steps (TODO — implementation):
        #. Call :func:`ensure_sys_path` so ``import config`` and ``import src`` resolve.
        #. ``from mcp.server.fastmcp import FastMCP`` (or the project's chosen SDK API).
        #. ``app = FastMCP("edgar-anomaly-detector")``
        #. ``from edgar_project.mcp.tools import register_all_tools`` → ``register_all_tools(app)``
        #. ``app.run()`` or equivalent stdio transport.

    Raises
    ------
    NotImplementedError
        Until the MCP SDK is integrated.
    """
    ensure_sys_path()
    logger.info("EDGAR MCP server scaffold ready; import pipeline in tools.handle_*")
    raise NotImplementedError(
        "TODO: integrate MCP Python SDK (stdio), call register_all_tools(app), then run"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
