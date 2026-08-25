"""
The backend's dependency boundaries, enforced structurally.

``tests/agentic/test_domain_boundary.py`` does this for ``agentic/`` and does it well. The
backend had the same rules written down in ``CLAUDE.md`` and nothing checking them — and the
rule with no check was the one that was broken: exactly one module imported ``src`` directly,
which is precisely how an unenforced boundary decays. One exception is invisible; the second
is normal.

Two rules, and they are not the same rule.

**``src`` is reachable only across the EDGAR seam.** ``backend/`` may use deterministic EDGAR
computation, but only through ``edgar_project.mcp``, so the core stays replaceable without the
API layer knowing what is behind it. A direct import couples HTTP handlers to the internals of
a package they are supposed to reach through an adapter.

**``backend/mcp`` is a client, not a second implementation.** It exposes the platform by
calling ``/v1`` over HTTP, which is what makes it safe to host: auth, ownership and rate
limiting are inherited from the API rather than reimplemented beside it. A repository or
service import there would be a back door around every check the HTTP layer performs.

Parsed with :mod:`ast` rather than grepped, so imports nested inside functions — the form a
boundary leak usually takes, because it looks like a local convenience — are seen too.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"

#: The only module permitted to reach EDGAR computation, and the package it may reach.
_EDGAR_SEAM = "edgar_project.mcp"

#: Modules under ``backend/`` allowed to import ``src`` directly. Deliberately empty: the
#: seam exists, it works, and an allowlist with entries invites a second one.
_SRC_ALLOWLIST: frozenset[str] = frozenset()

#: ``backend/mcp`` talks to the platform over HTTP. These are the layers that would let it
#: skip that and reach the database directly.
_SERVER_INTERNALS = ("backend.repositories", "backend.models", "backend.db", "backend.services")

#: ``backend/mcp/auth.py`` and ``rate_limit.py`` legitimately read settings and reuse the
#: API's own limiter primitive — that is inheriting the platform's rules, not bypassing them.
_MCP_ALLOWED_MODULES = ("backend.config", "backend.api.rate_limit", "backend.mcp")


def _imports(root: Path) -> list[tuple[str, int, str]]:
    """Every absolute import under ``root`` as ``(repo_relative_path, lineno, module)``."""
    found: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.extend((rel, node.lineno, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.append((rel, node.lineno, node.module))
    return found


def test_the_backend_never_imports_the_deterministic_core_directly() -> None:
    offenders = [
        f"{path}:{lineno} imports {module}"
        for path, lineno, module in _imports(_BACKEND)
        if module.split(".")[0] == "src" and path not in _SRC_ALLOWLIST
    ]

    assert not offenders, (
        "backend/ must reach src/ through edgar_project.mcp, never directly — the seam is "
        "what keeps the EDGAR core replaceable without the API layer knowing:\n  "
        + "\n  ".join(offenders)
    )


def test_the_edgar_seam_still_exports_what_the_backend_needs() -> None:
    """
    Guards the fix rather than the rule. Re-exporting through the seam is only an improvement
    if the re-export exists; without this, deleting it would send the next author straight
    back to importing ``src`` and the test above would look like an obstacle rather than a
    boundary.
    """
    from edgar_project.mcp import adapters

    assert callable(adapters.sort_period_key)


def test_the_hosted_mcp_server_reaches_the_platform_only_over_http() -> None:
    offenders = [
        f"{path}:{lineno} imports {module}"
        for path, lineno, module in _imports(_BACKEND / "mcp")
        if module.startswith(_SERVER_INTERNALS)
        and not module.startswith(_MCP_ALLOWED_MODULES)
    ]

    assert not offenders, (
        "backend/mcp is a client of /v1, not a second implementation — importing the "
        "persistence or service layer bypasses the auth and ownership checks the HTTP "
        "boundary applies, which is what makes hosting the MCP server safe:\n  "
        + "\n  ".join(offenders)
    )


def test_the_seam_package_is_named_correctly() -> None:
    """A rename would leave both rules above trivially satisfied and unguarded."""
    assert (_ROOT / _EDGAR_SEAM.replace(".", "/")).is_dir()
