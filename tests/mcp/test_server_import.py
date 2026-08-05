"""The stdio server module imports against the installed MCP SDK.

Nothing else in the suite loads ``edgar_project.mcp.server``, so an SDK upgrade that
moves or removes the API it depends on stays invisible: every other test passes while
the server itself is unimportable. That is exactly what happened with mcp 2.0, which
dropped ``mcp.server.fastmcp`` in favour of ``mcp.server.mcpserver`` — 650 tests were
green against an SDK the server could not start on.

This is a deliberately thin guard. It does not start a server or exercise a tool; it
just fails loudly at the point the dependency stops being compatible.
"""

from __future__ import annotations

import importlib


def test_mcp_server_module_imports() -> None:
    module = importlib.import_module("edgar_project.mcp.server")
    # The FastMCP instance the stdio entrypoint is built around.
    assert module.mcp is not None


def test_fastmcp_surface_is_available() -> None:
    """Pin the specific SDK entrypoint the server is written against.

    ``requirements.txt`` constrains ``mcp<2.0`` because of this import. If the server
    is migrated to the 2.x API, update both together.
    """
    from mcp.server.fastmcp import FastMCP

    assert FastMCP is not None
