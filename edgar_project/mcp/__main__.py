"""
Package entrypoint for development.

Run from repository root::

    # MCP server (stdio; for Cursor / Claude Desktop / Inspector)
    python -m edgar_project.mcp server

    # Local CLI (JSON to stdout)
    python -m edgar_project.mcp cli resolve-company AAPL

``python -m edgar_project.mcp.server`` and ``python -m edgar_project.mcp.cli`` are equivalent.
"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python -m edgar_project.mcp {server|cli} [...]\n"
            "  server   — stdio MCP server (same as python -m edgar_project.mcp.server)\n"
            "  cli ...  — local tool invocations (same as python -m edgar_project.mcp.cli ...)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    mode = sys.argv[1].lower()
    rest = sys.argv[2:]
    if mode == "server":
        from edgar_project.mcp.server import main as server_main

        server_main()
    elif mode == "cli":
        from edgar_project.mcp.cli import main as cli_main

        raise SystemExit(cli_main(rest))
    else:
        print(f"Unknown mode {mode!r}. Use 'server' or 'cli'.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
