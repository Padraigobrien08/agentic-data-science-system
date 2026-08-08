"""
The investigation domain's dependency boundary, enforced structurally.

Two rules, and they are not the same rule.

**`backend` is forbidden outright.** Nothing under ``agentic/`` may know about persistence,
settings, the API, or the LLM provider wiring. That is what lets the loop be lifted into
another project, run in a test with no database, and benchmarked offline. It is also the rule
most likely to be broken by accident: reaching for ``backend.config.settings`` or a prompt
loader is a one-line convenience that silently costs the whole property.

**`edgar_project` and `src` are allowed, but only from the EDGAR bridge modules.** Those
imports are the adapter pattern working as designed — the domain-specific plug-in reaching
domain-specific computation — and they are deliberately function-local so the generic path
never pays for them. Confined to two files that is a seam; spread across the package it is a
leak, and the allowlist below is what tells the two apart.

The check parses with :mod:`ast` and walks nested nodes rather than scanning lines, because
**every** existing ``edgar_project``/``src`` import is inside a function body and invisible to
a line-anchored grep.
"""

from __future__ import annotations

import ast
from pathlib import Path

_AGENTIC_ROOT = Path(__file__).resolve().parents[2] / "agentic"

#: Never importable from anywhere under ``agentic/``.
_FORBIDDEN_ROOT = "backend"

#: Importable only from the EDGAR bridge modules listed in :data:`_EDGAR_BRIDGE_MODULES`.
_EDGAR_ROOTS = frozenset({"edgar_project", "src"})

#: Repo-relative paths permitted to reach EDGAR computation.
_EDGAR_BRIDGE_MODULES = frozenset(
    {
        "agentic/adapters/edgar.py",
        "agentic/experiments/tools/edgar_tools.py",
    }
)


def _imports() -> list[tuple[str, int, str]]:
    """Every import under ``agentic/`` as ``(repo_relative_path, lineno, module)``.

    Includes imports nested in functions and methods; relative imports are skipped since
    they cannot cross a package boundary.
    """
    repo_root = _AGENTIC_ROOT.parent
    found: list[tuple[str, int, str]] = []
    for path in sorted(_AGENTIC_ROOT.rglob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.append((rel, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    found.append((rel, node.lineno, node.module))
    return found


def test_the_domain_never_imports_the_backend() -> None:
    """The hard invariant: ``agentic/`` knows nothing about the platform layer."""
    offenders = [
        f"{path}:{lineno} imports {module}"
        for path, lineno, module in _imports()
        if module.split(".")[0] == _FORBIDDEN_ROOT
    ]

    assert not offenders, (
        "agentic/ must not import backend — that dependency is what would stop the "
        "investigation domain from being reusable outside this repository:\n  "
        + "\n  ".join(offenders)
    )


def test_edgar_computation_is_reached_only_from_the_bridge_modules() -> None:
    """EDGAR imports are a seam in two files, not a dependency spread through the package."""
    offenders = [
        f"{path}:{lineno} imports {module}"
        for path, lineno, module in _imports()
        if module.split(".")[0] in _EDGAR_ROOTS and path not in _EDGAR_BRIDGE_MODULES
    ]

    assert not offenders, (
        "only the EDGAR bridge modules may import edgar_project/src; a third file reaching "
        "for them means the adapter seam is leaking:\n  " + "\n  ".join(offenders)
    )


def test_the_allowlist_still_refers_to_real_files() -> None:
    """
    A rename would otherwise turn the allowlist into a silent no-op: the entries would match
    nothing, the previous test would trivially pass, and the seam would be unguarded.
    """
    repo_root = _AGENTIC_ROOT.parent
    missing = [rel for rel in sorted(_EDGAR_BRIDGE_MODULES) if not (repo_root / rel).is_file()]

    assert not missing, (
        f"allowlisted EDGAR bridge modules no longer exist: {missing}. "
        "Update _EDGAR_BRIDGE_MODULES to the new paths rather than deleting the entries."
    )


def test_the_bridge_modules_actually_use_their_allowance() -> None:
    """
    Guards the other direction: if EDGAR imports disappear from both bridge modules, the
    allowlist is dead weight and should be removed rather than left as decoration.
    """
    using = {
        path
        for path, _lineno, module in _imports()
        if module.split(".")[0] in _EDGAR_ROOTS and path in _EDGAR_BRIDGE_MODULES
    }

    assert using, (
        "no EDGAR bridge module imports edgar_project/src any more — delete "
        "_EDGAR_BRIDGE_MODULES and tighten the rule instead of keeping an unused allowance."
    )
