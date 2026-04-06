"""
Deterministic Phase 1 pipeline orchestration.

Used by ``main.py`` and by the MCP layer via thin adapters. All business logic
delegates to existing ``src.*`` modules (``data_fetch``, ``metric_extraction``,
``normalization``, ``features``, ``anomaly``, ``report``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config


def extract_long_frames(tickers: list[str], *, refresh: bool) -> list[pd.DataFrame]:
    """Fetch SEC data and run :func:`src.metric_extraction.extract_metrics` per ticker."""
    from src.data_fetch import get_company_data
    from src.metric_extraction import extract_metrics

    out: list[pd.DataFrame] = []
    for t in tickers:
        data = get_company_data(t, refresh=refresh)
        out.append(
            extract_metrics(data["facts"], int(data["cik"]), years=config.YEARS_LOOKBACK)
        )
    return out


def build_panel_from_tickers(tickers: list[str], *, refresh: bool) -> pd.DataFrame:
    """Long metrics → wide panel via :func:`src.normalization.build_panel`."""
    from src.normalization import build_panel

    return build_panel(extract_long_frames(tickers, refresh=refresh))


def run_pipeline_computation(
    tickers: list[str],
    *,
    refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """
    Full in-memory pipeline: panel → features → anomalies → markdown report.

    Returns
    -------
    panel, features, anomalies, report_markdown
        Same semantics as the sequence in ``main.py`` before file writes.
    """
    from src.anomaly import detect_anomalies
    from src.features import compute_features
    from src.report import generate_report

    long_frames = extract_long_frames(tickers, refresh=refresh)
    from src.normalization import build_panel

    panel = build_panel(long_frames)
    feats = compute_features(panel)
    anom = detect_anomalies(feats)
    md = generate_report(anom, feats, top_n=5)
    return panel, feats, anom, md


def write_panel_csv(panel: pd.DataFrame) -> Path:
    """Write ``data/processed/panel.csv`` (Phase 1 path)."""
    p = config.DATA_PROCESSED / "panel.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(p, index=False)
    return p.resolve()


def write_features_csv(features: pd.DataFrame) -> Path:
    """Write ``data/processed/features.csv``."""
    p = config.DATA_PROCESSED / "features.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(p, index=False)
    return p.resolve()


def write_anomalies_csv(anomalies: pd.DataFrame) -> Path:
    """Write ``data/artifacts/anomalies.csv``."""
    p = config.DATA_ARTIFACTS / "anomalies.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(p, index=False)
    return p.resolve()


def write_report_md(report_md: str) -> Path:
    """Write ``data/artifacts/report.md``."""
    p = config.DATA_ARTIFACTS / "report.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(report_md, encoding="utf-8")
    return p.resolve()


def write_all_phase1_artifacts(
    panel: pd.DataFrame,
    features: pd.DataFrame,
    anomalies: pd.DataFrame,
    report_markdown: str,
) -> dict[str, Path]:
    """Write the four Phase 1 artifacts; return resolved paths keyed by logical name."""
    return {
        "panel": write_panel_csv(panel),
        "features": write_features_csv(features),
        "anomalies": write_anomalies_csv(anomalies),
        "report": write_report_md(report_markdown),
    }


def phase1_paths() -> dict[str, Path]:
    """Expected artifact paths (may or may not exist on disk yet)."""
    return {
        "panel": (config.DATA_PROCESSED / "panel.csv").resolve(),
        "features": (config.DATA_PROCESSED / "features.csv").resolve(),
        "anomalies": (config.DATA_ARTIFACTS / "anomalies.csv").resolve(),
        "report": (config.DATA_ARTIFACTS / "report.md").resolve(),
    }
