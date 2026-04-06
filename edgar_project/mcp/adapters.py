"""
Small adapters: DataFrame ↔ JSON-safe structures, path helpers.

No pipeline behavior here — only serialization and repo-root discovery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# pandas imported lazily in functions to keep import cost low for MCP startup
import pandas as pd

from .schemas import ArtifactSummary, TabularPreview


def repo_root() -> Path:
    """
    Return the repository root (parent of the ``edgar_project`` package).

    Layout::

        <repo>/edgar_project/mcp/adapters.py  → parents[2] == <repo>
    """
    return Path(__file__).resolve().parents[2]


def ensure_sys_path() -> None:
    """
    Ensure the repository root is on ``sys.path`` so ``import config`` and ``import src`` work.

    TODO: call once at MCP server startup (server.py) before importing pipeline modules.
    """
    import sys

    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def dataframe_to_preview(
    df: pd.DataFrame,
    *,
    max_rows: int = 50,
) -> TabularPreview:
    """
    Convert a DataFrame to JSON-friendly rows; optionally truncate for MCP payload size.

    TODO: used by tools that return ``extract_metrics`` / panel / features / anomalies previews.
    """
    cols = [str(c) for c in df.columns]
    n = len(df)
    part = df.head(max_rows) if n > max_rows else df
    # replace NaN with None for JSON
    records = part.where(part.notna(), None).to_dict(orient="records")
    return TabularPreview(
        columns=cols,
        rows=records,
        row_count=n,
        truncated=n > max_rows,
    )


def summarize_path(path: Path) -> ArtifactSummary:
    """Return existence and size for a single artifact file."""
    exists = path.is_file()
    size = path.stat().st_size if exists else None
    return ArtifactSummary(path=str(path), exists=exists, size_bytes=size)


def read_json_records_from_csv(path: Path, *, max_rows: int = 100) -> TabularPreview:
    """
    Load a CSV artifact into a preview structure.

    TODO: used when tools read ``panel.csv`` / ``features.csv`` / ``anomalies.csv`` from disk.
    """
    if not path.is_file():
        return TabularPreview(columns=[], rows=[], row_count=0, truncated=False)
    df = pd.read_csv(path)
    return dataframe_to_preview(df, max_rows=max_rows)
