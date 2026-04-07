"""
Deterministic Phase 1 pipeline orchestration.

Used by ``main.py`` and by the MCP layer via thin adapters. All business logic
delegates to existing ``src.*`` modules (``data_fetch``, ``metric_extraction``,
``normalization``, ``features``, ``anomaly``, ``report``).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

import config
from src.exclusions import build_exclusions_dataframe

_log = logging.getLogger(__name__)


def extract_long_frames(tickers: list[str], *, refresh: bool) -> tuple[list[pd.DataFrame], dict[str, int]]:
    """Fetch SEC data and run :func:`src.metric_extraction.extract_metrics` per ticker."""
    from src.data_fetch import get_company_data
    from src.metric_extraction import extract_metrics

    agg: dict[str, int] = {}
    out: list[pd.DataFrame] = []
    for t in tickers:
        data = get_company_data(t, refresh=refresh)
        per: dict[str, int] = {}
        out.append(
            extract_metrics(
                data["facts"],
                int(data["cik"]),
                years=config.YEARS_LOOKBACK,
                exclusion_counts=per,
            )
        )
        for k, v in per.items():
            agg[k] = agg.get(k, 0) + v
    if agg:
        _log.info("metric_extraction totals (all tickers): %s", dict(sorted(agg.items())))
    return out, agg


def build_panel_from_tickers(tickers: list[str], *, refresh: bool) -> pd.DataFrame:
    """Long metrics → wide panel via :func:`src.normalization.build_panel`."""
    from src.normalization import build_panel

    long_frames, _ = extract_long_frames(tickers, refresh=refresh)
    return build_panel(long_frames)


def run_pipeline_computation(
    tickers: list[str],
    *,
    refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Full in-memory pipeline: panel → features → anomalies → peer signals → markdown report + summaries.

    Returns
    -------
    panel, features, anomalies, report_markdown, data_quality_summary, exclusions_summary, peer_signals
        ``peer_signals`` → ``peer_signals.csv`` (cross-sectional rank/z by period; additive layer).
    """
    from src.anomaly import detect_anomalies
    from src.data_quality import compute_data_quality_summary
    from src.features import compute_features
    from src.normalization import build_panel
    from src.peer_signals import compute_peer_signals
    from src.report import generate_report

    long_frames, extraction_counts = extract_long_frames(tickers, refresh=refresh)
    normalization_counts: dict[str, int] = {}
    panel = build_panel(long_frames, exclusion_counts=normalization_counts)
    exclusions_df = build_exclusions_dataframe(extraction_counts, normalization_counts)
    if not exclusions_df.empty:
        _log.info(
            "exclusions_summary rows=%s; sample=%s",
            len(exclusions_df),
            exclusions_df.head(5).to_dict(orient="records"),
        )

    feats = compute_features(panel)
    peer_signals_df = compute_peer_signals(feats)
    anom = detect_anomalies(feats, peer_signals=peer_signals_df)
    dq_df = compute_data_quality_summary(long_frames, panel, feats, anom)
    md = generate_report(
        anom,
        feats,
        peer_signals=peer_signals_df,
        data_quality=dq_df,
        exclusions=exclusions_df,
        top_n=5,
    )
    return panel, feats, anom, md, dq_df, exclusions_df, peer_signals_df


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


def write_data_quality_csv(data_quality: pd.DataFrame) -> Path:
    """Write ``data/artifacts/data_quality_summary.csv``."""
    p = config.DATA_ARTIFACTS / "data_quality_summary.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    data_quality.to_csv(p, index=False)
    return p.resolve()


def write_exclusions_csv(exclusions: pd.DataFrame) -> Path:
    """Write ``data/artifacts/exclusions_summary.csv``."""
    p = config.DATA_ARTIFACTS / "exclusions_summary.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    exclusions.to_csv(p, index=False)
    return p.resolve()


def write_peer_signals_csv(peer_signals: pd.DataFrame) -> Path:
    """Write ``data/artifacts/peer_signals.csv``."""
    p = config.DATA_ARTIFACTS / "peer_signals.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    peer_signals.to_csv(p, index=False)
    return p.resolve()


def write_all_phase1_artifacts(
    panel: pd.DataFrame,
    features: pd.DataFrame,
    anomalies: pd.DataFrame,
    report_markdown: str,
    *,
    data_quality: pd.DataFrame | None = None,
    exclusions: pd.DataFrame | None = None,
    peer_signals: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Write Phase 1 artifacts (panel, features, anomalies, report, optional CSV summaries)."""
    out: dict[str, Path] = {
        "panel": write_panel_csv(panel),
        "features": write_features_csv(features),
        "anomalies": write_anomalies_csv(anomalies),
        "report": write_report_md(report_markdown),
    }
    if data_quality is not None:
        out["data_quality"] = write_data_quality_csv(data_quality)
    if exclusions is not None:
        out["exclusions"] = write_exclusions_csv(exclusions)
    if peer_signals is not None:
        out["peer_signals"] = write_peer_signals_csv(peer_signals)
    return out


def phase1_paths() -> dict[str, Path]:
    """Expected artifact paths (may or may not exist on disk yet)."""
    return {
        "panel": (config.DATA_PROCESSED / "panel.csv").resolve(),
        "features": (config.DATA_PROCESSED / "features.csv").resolve(),
        "anomalies": (config.DATA_ARTIFACTS / "anomalies.csv").resolve(),
        "report": (config.DATA_ARTIFACTS / "report.md").resolve(),
        "data_quality": (config.DATA_ARTIFACTS / "data_quality_summary.csv").resolve(),
        "exclusions": (config.DATA_ARTIFACTS / "exclusions_summary.csv").resolve(),
        "peer_signals": (config.DATA_ARTIFACTS / "peer_signals.csv").resolve(),
        "manual_validation": (config.PROJECT_ROOT / "validation" / "manual_validation.csv").resolve(),
    }
