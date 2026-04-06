"""
Thin adapters between MCP tools and Phase 1 code.

- Path / sys.path helpers
- Delegation to ``src.pipeline_runner`` and ``src.data_fetch`` (no duplicated business logic)
- CSV I/O for optional artifact inputs
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .schemas import ArtifactSummary, TabularPreview


def repo_root() -> Path:
    """
    Repository root (parent of the ``edgar_project`` package).

    ``<repo>/edgar_project/mcp/adapters.py`` → ``parents[2] == <repo>``.
    """
    return Path(__file__).resolve().parents[2]


def ensure_sys_path() -> None:
    """Ensure repo root is importable as ``config`` + ``src``."""
    import sys

    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def phase1_paths() -> dict[str, Path]:
    """Delegate to :func:`src.pipeline_runner.phase1_paths`."""
    ensure_sys_path()
    from src.pipeline_runner import phase1_paths as _paths

    return _paths()


def cache_paths_from_fetch_result(payload: dict[str, Any]) -> dict[str, str]:
    """
    Stable JSON cache paths for a ``get_company_data`` return dict.

    Must stay aligned with :func:`src.data_fetch.get_company_data` filenames.
    """
    ensure_sys_path()
    import config

    cik10 = payload["cik10"]
    ticker_u = payload["ticker"]
    tdir = config.DATA_RAW / ticker_u
    sub = tdir / f"CIK{cik10}_submissions.json"
    fac = tdir / f"CIK{cik10}_companyfacts.json"
    return {
        "submissions": str(sub.resolve()),
        "companyfacts": str(fac.resolve()),
    }


def resolve_company_dict(ticker: str) -> dict[str, Any]:
    """Delegate to :func:`src.data_fetch.resolve_company`."""
    ensure_sys_path()
    from src.data_fetch import resolve_company

    return resolve_company(ticker.strip())


def fetch_company_data_dict(ticker: str, *, refresh: bool) -> dict[str, Any]:
    """Delegate to :func:`src.data_fetch.get_company_data`."""
    ensure_sys_path()
    from src.data_fetch import get_company_data

    return get_company_data(ticker.strip(), refresh=refresh)


def build_panel_dataframe(tickers: list[str], *, refresh: bool) -> pd.DataFrame:
    """Delegate to :func:`src.pipeline_runner.build_panel_from_tickers`."""
    ensure_sys_path()
    from src.pipeline_runner import build_panel_from_tickers

    return build_panel_from_tickers(tickers, refresh=refresh)


def compute_features_dataframe(panel: pd.DataFrame) -> pd.DataFrame:
    """Delegate to :func:`src.features.compute_features`."""
    ensure_sys_path()
    from src.features import compute_features

    return compute_features(panel)


def detect_anomalies_dataframe(features: pd.DataFrame) -> pd.DataFrame:
    """Delegate to :func:`src.anomaly.detect_anomalies`."""
    ensure_sys_path()
    from src.anomaly import detect_anomalies

    return detect_anomalies(features)


def generate_report_markdown(anomalies: pd.DataFrame, features: pd.DataFrame) -> str:
    """Delegate to :func:`src.report.generate_report`."""
    ensure_sys_path()
    from src.report import generate_report

    return generate_report(anomalies, features, top_n=5)


def run_full_pipeline(
    tickers: list[str],
    *,
    refresh: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Delegate to :func:`src.pipeline_runner.run_pipeline_computation`."""
    ensure_sys_path()
    from src.pipeline_runner import run_pipeline_computation

    return run_pipeline_computation(tickers, refresh=refresh)


def write_panel_csv(panel: pd.DataFrame) -> Path:
    from src.pipeline_runner import write_panel_csv as _w

    return _w(panel)


def write_features_csv(features: pd.DataFrame) -> Path:
    from src.pipeline_runner import write_features_csv as _w

    return _w(features)


def write_anomalies_csv(anomalies: pd.DataFrame) -> Path:
    from src.pipeline_runner import write_anomalies_csv as _w

    return _w(anomalies)


def write_report_md(text: str) -> Path:
    from src.pipeline_runner import write_report_md as _w

    return _w(text)


def write_all_phase1_artifacts(
    panel: pd.DataFrame,
    features: pd.DataFrame,
    anomalies: pd.DataFrame,
    report_markdown: str,
) -> dict[str, Path]:
    from src.pipeline_runner import write_all_phase1_artifacts as _w

    return _w(panel, features, anomalies, report_markdown)


def read_panel_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def read_features_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def read_anomalies_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def dataframe_to_preview(
    df: pd.DataFrame,
    *,
    max_rows: int = 50,
) -> TabularPreview:
    """Convert a DataFrame to JSON-friendly rows (optional truncation)."""
    cols = [str(c) for c in df.columns]
    n = len(df)
    part = df.head(max_rows) if n > max_rows else df
    records = part.where(part.notna(), None).to_dict(orient="records")
    return TabularPreview(
        columns=cols,
        rows=records,
        row_count=n,
        truncated=n > max_rows,
    )


def summarize_path(path: Path) -> ArtifactSummary:
    exists = path.is_file()
    size = path.stat().st_size if exists else None
    return ArtifactSummary(path=str(path), exists=exists, size_bytes=size)


def read_json_records_from_csv(path: Path, *, max_rows: int = 100) -> TabularPreview:
    if not path.is_file():
        return TabularPreview(columns=[], rows=[], row_count=0, truncated=False)
    df = pd.read_csv(path)
    return dataframe_to_preview(df, max_rows=max_rows)
