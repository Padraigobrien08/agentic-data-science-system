"""
Repository layout — single source for repo root and cwd for CLI / backend workers.

Phase 1 MCP tools and ``config`` resolve paths relative to the repository root; callers
that invoke the pipeline from another working directory must ``chdir`` here first.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def ensure_repo_root_on_syspath() -> None:
    """Prepend repo root so ``import config`` and ``import src`` work."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def chdir_repo_root() -> None:
    """Make ``os.getcwd()`` the repository root (best-effort)."""
    try:
        os.chdir(REPO_ROOT)
    except OSError:
        pass
