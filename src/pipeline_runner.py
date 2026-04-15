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
from edgar_project.run_workspace import RunWorkspace, build_run_workspace, phase1_paths as workspace_phase1_paths
from src.exclusions import build_exclusions_dataframe

_log = logging.getLogger(__name__)


def _legacy_phase1_workspace() -> RunWorkspace:
    return build_run_workspace(
        workspace_root=config.DATA_RUNS,
        run_scoped_id="_legacy_phase1",
        manual_validation_csv=(config.PROJECT_ROOT / "validation" / "manual_validation.csv"),
        use_legacy_shared_paths=True,
    )


def _resolve_workspace(
    workspace: RunWorkspace | None,
    *,
    use_legacy_shared_paths: bool = False,
) -> RunWorkspace:
    if workspace is not None:
        return workspace.ensure_directories()
    if use_legacy_shared_paths:
        return _legacy_phase1_workspace().ensure_directories()
    raise ValueError("workspace is required unless use_legacy_shared_paths=True")


def _resolve_phase1_output_path(
    role: str,
    *,
    workspace: RunWorkspace | None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    resolved_workspace = _resolve_workspace(workspace, use_legacy_shared_paths=use_legacy_shared_paths)
    return phase1_paths(resolved_workspace)[role]


def extract_long_frames(
    tickers: list[str], *, refresh: bool
) -> tuple[list[pd.DataFrame], pd.DataFrame, dict[str, int]]:
    """Fetch SEC data and run extraction per ticker.

    Returns long metric frames, concatenated **extraction caveat** rows (tag/unit resolution), and
    aggregated exclusion counts. Caveats are filtered to the final panel when writing artifacts
    (see :mod:`src.metric_caveats`).
    """
    from src.data_fetch import get_company_data
    from src.metric_extraction import extract_metrics_with_extraction_caveats

    agg: dict[str, int] = {}
    out: list[pd.DataFrame] = []
    caveat_parts: list[pd.DataFrame] = []
    for t in tickers:
        data = get_company_data(t, refresh=refresh)
        per: dict[str, int] = {}
        vals, cave = extract_metrics_with_extraction_caveats(
            data["facts"],
            int(data["cik"]),
            years=config.YEARS_LOOKBACK,
            exclusion_counts=per,
        )
        out.append(vals)
        caveat_parts.append(cave)
        for k, v in per.items():
            agg[k] = agg.get(k, 0) + v
    if agg:
        _log.info("metric_extraction totals (all tickers): %s", dict(sorted(agg.items())))
    cave_long = pd.concat(caveat_parts, ignore_index=True) if caveat_parts else pd.DataFrame()
    return out, cave_long, agg


def build_panel_from_tickers(tickers: list[str], *, refresh: bool) -> pd.DataFrame:
    """Long metrics → wide panel via :func:`src.normalization.build_panel`."""
    from src.normalization import build_panel

    long_frames, _cave, _ = extract_long_frames(tickers, refresh=refresh)
    return build_panel(long_frames)


def run_pipeline_computation(
    tickers: list[str],
    *,
    refresh: bool = False,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    str,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Full in-memory pipeline: panel → features → anomalies → peer signals → markdown report + summaries.

    Returns
    -------
    panel, features, anomalies, report_markdown, data_quality_summary, exclusions_summary, peer_signals, extraction_caveats_long
        ``peer_signals`` → ``peer_signals.csv`` (cross-sectional rank/z by period; additive layer).
        ``extraction_caveats_long`` → per-(cik, period, metric) extraction caveat rows (see :mod:`src.metric_caveats`).
    """
    from src.anomaly import detect_anomalies
    from src.data_quality import compute_data_quality_summary
    from src.features import compute_features
    from src.normalization import build_panel
    from src.peer_signals import compute_peer_signals
    from src.trend_breaks import compute_trend_break_signals
    from src.findings import (
        build_findings_summary_by_company,
        build_findings_summary_by_metric,
        build_findings_summary_by_period,
        build_unified_findings,
    )
    from src.metric_caveats import compute_panel_metric_caveats, filter_extraction_caveats_to_panel
    from src.metric_coverage import compute_metric_coverage_summary
    from src.report import generate_report

    long_frames, extraction_caveats_long, extraction_counts = extract_long_frames(tickers, refresh=refresh)
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
    trend_breaks_df = compute_trend_break_signals(feats)
    peer_signals_df = compute_peer_signals(feats)
    extraction_caveats_for_report = filter_extraction_caveats_to_panel(extraction_caveats_long, panel)
    panel_caveats_df = compute_panel_metric_caveats(panel)
    anom = detect_anomalies(
        feats,
        peer_signals=peer_signals_df,
        extraction_caveats=extraction_caveats_for_report,
        panel_caveats=panel_caveats_df,
    )
    unified_findings_df = build_unified_findings(anom, trend_breaks=trend_breaks_df)
    findings_by_company_df = build_findings_summary_by_company(unified_findings_df)
    findings_by_metric_df = build_findings_summary_by_metric(unified_findings_df)
    findings_by_period_df = build_findings_summary_by_period(unified_findings_df)
    dq_df = compute_data_quality_summary(long_frames, panel, feats, anom)
    metric_cov_summary = compute_metric_coverage_summary(panel)
    report_workspace = workspace
    report_artifact_paths = phase1_paths(workspace) if workspace is not None else None
    md = generate_report(
        anom,
        feats,
        peer_signals=peer_signals_df,
        data_quality=dq_df,
        exclusions=exclusions_df,
        workspace=report_workspace,
        artifact_paths=report_artifact_paths,
        use_legacy_shared_paths=use_legacy_shared_paths,
        metric_coverage_summary=metric_cov_summary,
        extraction_caveats=extraction_caveats_for_report,
        panel_caveats=panel_caveats_df,
        trend_breaks=trend_breaks_df,
        unified_findings=unified_findings_df,
        findings_summary_by_company=findings_by_company_df,
        findings_summary_by_metric=findings_by_metric_df,
        findings_summary_by_period=findings_by_period_df,
        top_n=5,
    )
    return panel, feats, anom, md, dq_df, exclusions_df, peer_signals_df, extraction_caveats_long


def write_panel_csv(
    panel: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``panel.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "panel",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(p, index=False)
    return p.resolve()


def write_features_csv(
    features: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``features.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "features",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(p, index=False)
    return p.resolve()


def write_anomalies_csv(
    anomalies: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``anomalies.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "anomalies",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(p, index=False)
    return p.resolve()


def write_report_md(
    report_md: str,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``report.md`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "report",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(report_md, encoding="utf-8")
    return p.resolve()


def write_data_quality_csv(
    data_quality: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``data_quality_summary.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "data_quality",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    data_quality.to_csv(p, index=False)
    return p.resolve()


def write_exclusions_csv(
    exclusions: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``exclusions_summary.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "exclusions",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    exclusions.to_csv(p, index=False)
    return p.resolve()


def write_peer_signals_csv(
    peer_signals: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``peer_signals.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "peer_signals",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    peer_signals.to_csv(p, index=False)
    return p.resolve()


def write_trend_breaks_csv(
    trend_breaks: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``trend_break_signals.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "trend_breaks",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    trend_breaks.to_csv(p, index=False)
    return p.resolve()


def write_unified_findings_csv(
    unified_findings: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``unified_findings.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "unified_findings",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    unified_findings.to_csv(p, index=False)
    return p.resolve()


def write_deterioration_focus_csv(
    deterioration_focus: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    """Write ``deterioration_focus.csv`` under the explicit run workspace."""
    p = _resolve_phase1_output_path(
        "deterioration_focus",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    deterioration_focus.to_csv(p, index=False)
    return p.resolve()


def write_findings_summary_by_company_csv(
    df: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    p = _resolve_phase1_output_path(
        "findings_summary_by_company",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p.resolve()


def write_findings_summary_by_metric_csv(
    df: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    p = _resolve_phase1_output_path(
        "findings_summary_by_metric",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p.resolve()


def write_findings_summary_by_period_csv(
    df: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    p = _resolve_phase1_output_path(
        "findings_summary_by_period",
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p.resolve()


def write_metric_coverage_artifacts(
    panel: pd.DataFrame,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> dict[str, Path]:
    """
    Write metric coverage CSVs derived from the **final wide panel** (post revenue filter).

    See :mod:`src.metric_coverage` for definitions. Called alongside other Phase 1 artifacts
    so coverage stays aligned with ``panel.csv``.
    """
    from src.metric_coverage import compute_metric_coverage_tables

    resolved_workspace = _resolve_workspace(workspace, use_legacy_shared_paths=use_legacy_shared_paths)
    resolved_paths = phase1_paths(resolved_workspace)
    resolved_workspace.artifacts_dir.mkdir(parents=True, exist_ok=True)
    tables = compute_metric_coverage_tables(panel)
    paths = {
        "metric_coverage_summary": resolved_paths["metric_coverage_summary"],
        "metric_coverage_by_company": resolved_paths["metric_coverage_by_company"],
        "metric_coverage_by_period": resolved_paths["metric_coverage_by_period"],
    }
    tables["summary"].to_csv(paths["metric_coverage_summary"], index=False)
    tables["by_company"].to_csv(paths["metric_coverage_by_company"], index=False)
    tables["by_period"].to_csv(paths["metric_coverage_by_period"], index=False)
    return {k: v.resolve() for k, v in paths.items()}


def write_all_phase1_artifacts(
    panel: pd.DataFrame,
    features: pd.DataFrame,
    anomalies: pd.DataFrame,
    report_markdown: str,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
    data_quality: pd.DataFrame | None = None,
    exclusions: pd.DataFrame | None = None,
    peer_signals: pd.DataFrame | None = None,
    extraction_caveats_long: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Write Phase 1 artifacts (panel, features, anomalies, report, optional CSV summaries)."""
    from src.metric_caveats import write_metric_caveats_artifacts

    out: dict[str, Path] = {
        "panel": write_panel_csv(
            panel,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        ),
        "features": write_features_csv(
            features,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        ),
        "anomalies": write_anomalies_csv(
            anomalies,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        ),
        "report": write_report_md(
            report_markdown,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        ),
    }
    out.update(
        write_metric_caveats_artifacts(
            panel,
            extraction_caveats_long,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    )
    out.update(
        write_metric_coverage_artifacts(
            panel,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    )
    if data_quality is not None:
        out["data_quality"] = write_data_quality_csv(
            data_quality,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if exclusions is not None:
        out["exclusions"] = write_exclusions_csv(
            exclusions,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if peer_signals is not None:
        out["peer_signals"] = write_peer_signals_csv(
            peer_signals,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    from src.trend_breaks import compute_trend_break_signals
    from src.findings import (
        build_deterioration_focus,
        build_findings_summary_by_company,
        build_findings_summary_by_metric,
        build_findings_summary_by_period,
        build_unified_findings,
    )

    trend_breaks_df = compute_trend_break_signals(features)
    out["trend_breaks"] = write_trend_breaks_csv(
        trend_breaks_df,
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    uf = build_unified_findings(anomalies, trend_breaks=trend_breaks_df)
    out["unified_findings"] = write_unified_findings_csv(
        uf,
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    out["deterioration_focus"] = write_deterioration_focus_csv(
        build_deterioration_focus(uf),
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    out["findings_summary_by_company"] = write_findings_summary_by_company_csv(
        build_findings_summary_by_company(uf),
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    out["findings_summary_by_metric"] = write_findings_summary_by_metric_csv(
        build_findings_summary_by_metric(uf),
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    out["findings_summary_by_period"] = write_findings_summary_by_period_csv(
        build_findings_summary_by_period(uf),
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    return out


def legacy_phase1_paths() -> dict[str, Path]:
    """Compatibility registry for explicit legacy/dev workflows that still use shared Phase 1 roots."""
    workspace = _legacy_phase1_workspace()
    return phase1_paths(workspace)


def phase1_paths(workspace: RunWorkspace) -> dict[str, Path]:
    """Expected run-scoped artifact paths for ``workspace`` (may or may not exist on disk yet)."""
    return {role: path.resolve() for role, path in workspace_phase1_paths(workspace).items()}
