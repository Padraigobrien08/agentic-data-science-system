"""
Markdown report: normalized metrics, features, anomaly tables with deterministic explanations.

Credibility sections pull from in-memory pipeline outputs (or optional CSV paths for MCP).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

import config
from edgar_project.run_workspace import RunWorkspace, build_run_workspace
from edgar_project.run_workspace import phase1_paths as workspace_phase1_paths
from src.peer_signals import PEER_SIGNAL_METRICS, summarize_peer_coverage

# Sample columns for the "normalized panel" section (intersection with actual columns is used).
_PANEL_SAMPLE_COLS: tuple[str, ...] = (
    "cik",
    "period",
    "revenue",
    "net_income",
    "total_assets",
    "total_liabilities",
)


def _df_to_md(df: pd.DataFrame, max_rows: int = 30) -> str:
    if df.empty:
        return "_No rows._\n"
    show = df.head(max_rows)
    return show.to_markdown(index=False) + "\n"


def _legacy_workspace() -> RunWorkspace:
    return build_run_workspace(
        workspace_root=config.DATA_RUNS,
        run_scoped_id="_legacy_phase1",
        manual_validation_csv=(config.PROJECT_ROOT / "validation" / "manual_validation.csv"),
        use_legacy_shared_paths=True,
    )


def _resolve_artifact_paths(
    *,
    artifact_paths: Mapping[str, str | Path] | None = None,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> dict[str, Path]:
    if use_legacy_shared_paths:
        return {
            role: path.resolve()
            for role, path in workspace_phase1_paths(_legacy_workspace()).items()
        }
    if artifact_paths is not None:
        return {
            str(role): Path(path).expanduser().resolve()
            for role, path in artifact_paths.items()
        }
    if workspace is not None:
        return {
            role: path.resolve()
            for role, path in workspace_phase1_paths(workspace).items()
        }
    return {}


def _artifact_path_for_basename(
    basename: str,
    *,
    artifact_paths: Mapping[str, Path],
) -> Path | None:
    for path in artifact_paths.values():
        if path.name == basename:
            return path
    return None


def _resolve_manual_validation_path(
    manual_validation_path: Path | None,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path | None:
    if manual_validation_path is not None:
        return manual_validation_path.resolve()
    if workspace is not None:
        return workspace.manual_validation_csv.resolve()
    if use_legacy_shared_paths:
        from src.manual_validation import VALIDATION_CSV_PATH

        return VALIDATION_CSV_PATH.resolve()
    return None


def _try_read_artifact_csv(
    basename: str,
    *,
    artifact_paths: Mapping[str, Path] | None = None,
    use_legacy_shared_paths: bool = False,
) -> pd.DataFrame | None:
    """
    Load an explicit artifact CSV by basename.

    Shared repo-global fallback is available only behind ``use_legacy_shared_paths=True``.
    """
    p = None
    if artifact_paths is not None:
        p = _artifact_path_for_basename(basename, artifact_paths=artifact_paths)
    if p is None and use_legacy_shared_paths:
        p = config.DATA_ARTIFACTS / basename
    if p is None:
        return None
    if not p.is_file():
        return None
    try:
        return pd.read_csv(p)
    except Exception:
        return None


def _repo_rel_for_footer(path: Path, root: Path) -> str:
    """Stable repo-relative path for markdown (falls back if ``path`` is outside ``root``)."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _rollup_caveat_codes(series: pd.Series) -> dict[str, int]:
    """Count semicolon-separated caveat codes across rows (non-empty segments only)."""
    counts: dict[str, int] = {}
    for raw in series.dropna().astype(str):
        s = str(raw).strip()
        if not s or s == "none":
            continue
        for part in s.split(";"):
            code = part.strip()
            if code:
                counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def _format_code_counts_md(counts: dict[str, int], *, max_codes: int = 8) -> str:
    if not counts:
        return "_None in this slice._\n"
    lines: list[str] = []
    for i, (k, v) in enumerate(counts.items()):
        if i >= max_codes:
            lines.append(f"- _…and {len(counts) - max_codes} more (see CSV)._ \n")
            break
        lines.append(f"- `{k}`: **{v}** caveat row(s)\n")
    return "".join(lines)


# Exclusion reason codes that most directly affect interpretation of extracted vs normalized values.
_TRUST_EXCLUSION_REASONS = frozenset(
    {
        "segmented_context_excluded",
        "duplicate_resolved",
        "unsupported_unit",
        "missing_required_metric",
        "non_numeric_coercion",
        "drop_duplicate_row",
    }
)


def _trust_metric_coverage_compact(mc: pd.DataFrame | None) -> str:
    """Compact table: metric, coverage_ratio, n_slots."""
    if mc is None or mc.empty:
        return "_No metric coverage summary (run pipeline or provide `metric_coverage_summary.csv`)._\n\n"
    if "metric_name" not in mc.columns:
        return (
            "_Coverage summary has rows but no `metric_name` column (not the pipeline export schema); "
            "preview below._\n\n" + _df_to_md(mc.head(8), max_rows=8)
        )
    show = mc.rename(
        columns={
            "metric_name": "metric",
            "n_slots": "slots",
            "coverage_ratio": "coverage",
            "available_count": "present",
            "missing_count": "missing",
        }
    )
    cols = [c for c in ("metric", "coverage", "slots", "present", "missing") if c in show.columns]
    if not cols:
        return _df_to_md(mc.head(8), max_rows=8)
    return _df_to_md(show[cols].head(12), max_rows=12)


def _trust_caveat_rollups(
    extraction_caveats: pd.DataFrame | None,
    panel_caveats: pd.DataFrame | None,
) -> str:
    lines: list[str] = []
    lines.append("**Extraction caveat codes** (per metric cell; from tag/unit resolution):\n\n")
    if extraction_caveats is None or extraction_caveats.empty:
        lines.append("_No extraction caveat rows._\n\n")
    elif "caveat_codes" in extraction_caveats.columns:
        rc = _rollup_caveat_codes(extraction_caveats["caveat_codes"])
        lines.append(_format_code_counts_md(rc))
        lines.append("\n")
    else:
        lines.append("_No `caveat_codes` column._\n\n")

    lines.append("**Panel context caveat codes** (per CIK × period):\n\n")
    if panel_caveats is None or panel_caveats.empty:
        lines.append("_No panel caveat rows._\n\n")
    elif "caveat_codes" in panel_caveats.columns:
        rc = _rollup_caveat_codes(panel_caveats["caveat_codes"])
        lines.append(_format_code_counts_md(rc))
        lines.append("\n")
    else:
        lines.append("_No `caveat_codes` column._\n\n")
    return "".join(lines)


def _trust_pipeline_interpretation_notes(excl: pd.DataFrame | None) -> str:
    """Counts from exclusions that matter for trusting extracted/normalized numbers."""
    if excl is None or excl.empty:
        return "_No exclusion summary._\n\n"
    need = {"stage", "reason_code", "count"}
    if not need.issubset(set(excl.columns)):
        return _df_to_md(excl.head(8), max_rows=8)
    sub = excl[excl["reason_code"].isin(_TRUST_EXCLUSION_REASONS)].copy()
    if sub.empty:
        return "_No trust-flagged exclusion reasons in the filtered set (see full exclusions below)._ \n\n"
    sub = sub.sort_values("count", ascending=False)
    lines: list[str] = []
    for _, r in sub.iterrows():
        lines.append(f"- **{r['stage']}** / `{r['reason_code']}`: **{int(r['count'])}**\n")
    lines.append("\n")
    return "".join(lines)


def _artifact_paths_footer(
    *,
    artifact_paths: Mapping[str, str | Path] | None = None,
    manual_validation_path: Path | None = None,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> str:
    root = Path(config.PROJECT_ROOT)
    legacy_mode = use_legacy_shared_paths or (
        artifact_paths is None and workspace is None and manual_validation_path is None
    )
    resolved_artifact_paths = _resolve_artifact_paths(
        artifact_paths=artifact_paths,
        workspace=workspace,
        use_legacy_shared_paths=legacy_mode,
    )
    resolved_manual_validation_path = _resolve_manual_validation_path(
        manual_validation_path,
        workspace=workspace,
        use_legacy_shared_paths=legacy_mode,
    )

    ordered_roles = (
        "data_quality",
        "exclusions",
        "peer_signals",
        "trend_breaks",
        "unified_findings",
        "findings_summary_by_company",
        "findings_summary_by_metric",
        "findings_summary_by_period",
        "metric_coverage_summary",
        "metric_coverage_by_company",
        "metric_coverage_by_period",
        "metric_caveats_extraction",
        "metric_caveats_panel",
    )
    rendered_paths = [
        f"`{_repo_rel_for_footer(resolved_artifact_paths[role], root)}`"
        for role in ordered_roles
        if role in resolved_artifact_paths
    ]
    if resolved_manual_validation_path is not None:
        rendered_paths.append(
            f"`{_repo_rel_for_footer(resolved_manual_validation_path, root)}`"
        )
    if not rendered_paths:
        return "_Artifact paths: unavailable (explicit workspace/artifact paths not provided)._ \n"
    return "_Artifact paths (relative to project root): " + ", ".join(rendered_paths) + "._\n"


def _credibility_data_quality_compact(dq: pd.DataFrame) -> str:
    """Stage counts, key drop rule, and top missingness rows (from ``data_quality_summary`` table)."""
    lines: list[str] = []
    if dq.empty:
        return "_No data quality summary (empty)._ \n\n"
    st = dq[dq["category"] == "stage_count"]
    if not st.empty:
        lines.append(_df_to_md(st[["name", "value", "unit"]].rename(columns={"name": "metric"}), max_rows=12))
    dr = dq[dq["category"] == "drop_rule"]
    if not dr.empty:
        for _, r in dr.iterrows():
            note = f" ({r['notes']})" if pd.notna(r.get("notes")) and str(r["notes"]).strip() else ""
            lines.append(f"- **{r['name']}**: {r['value']} {r['unit']}{note}\n")
    mm = dq[dq["category"] == "missingness_metric"]
    if not mm.empty:
        lines.append("\n_Missingness (panel, sample; see CSV for full)._ \n\n")
        lines.append(_df_to_md(mm[["name", "value"]].rename(columns={"name": "metric", "value": "frac_na"}), max_rows=8))
    return "".join(lines) + "\n"


def _credibility_exclusions_compact(excl: pd.DataFrame) -> str:
    """High-level exclusion counts by stage/reason (``exclusions_summary``)."""
    if excl is None or excl.empty:
        return "_No exclusion counts recorded for this run._ \n\n"
    need = {"stage", "reason_code", "count"}
    if not need.issubset(set(excl.columns)):
        return _df_to_md(excl.head(15), max_rows=15)
    top = excl.sort_values("count", ascending=False).head(12)
    return _df_to_md(top, max_rows=12)


def _credibility_manual_validation(path: Path | None, *, preview_rows: int = 8) -> str:
    """Status from ``validation/manual_validation.csv`` when the file has data rows."""
    shown_path = (
        f"`{_repo_rel_for_footer(path.resolve(), Path(config.PROJECT_ROOT))}`"
        if path is not None
        else "`manual_validation.csv`"
    )
    if path is None or not path.is_file():
        return f"_Manual validation: file not found at {shown_path}._ \n\n"
    try:
        mv = pd.read_csv(path)
    except Exception:
        return "_Manual validation: could not read CSV._ \n\n"
    if mv.empty or len(mv) == 0:
        return "_Manual validation: no records yet (header-only or empty)._ \n\n"
    lines: list[str] = [f"- **Records**: {len(mv)}\n"]
    if "validation_status" in mv.columns and mv["validation_status"].notna().any():
        vc = mv["validation_status"].value_counts().head(6)
        lines.append("- **By status**: " + "; ".join(f"{k}={v}" for k, v in vc.items()) + "\n")
    if "checked_date" in mv.columns:
        d = mv["checked_date"].dropna().astype(str)
        if not d.empty:
            lines.append(f"- **Latest checked_date**: {d.max()}\n")
    lines.append("\n")
    show = [
        c
        for c in (
            "ticker",
            "cik",
            "period",
            "metric",
            "extracted_value",
            "expected_value",
            "validation_status",
            "checked_date",
        )
        if c in mv.columns
    ]
    if show:
        lines.append(_df_to_md(mv[show].head(preview_rows), max_rows=preview_rows))
    return "".join(lines)


def _credibility_peer_summary(peer_signals: pd.DataFrame | None, anomalies: pd.DataFrame) -> str:
    """Counts from peer_signals + anomaly_category breakdown (no duplicate long tables)."""
    lines: list[str] = []
    if peer_signals is not None and not peer_signals.empty:
        cov = summarize_peer_coverage(peer_signals)
        lines.append(_df_to_md(cov, max_rows=10))
        ex = peer_signals["peer_alert"].isin(["extreme_high", "extreme_low"]).sum()
        lines.append(f"- **Peer signal rows with extreme_high / extreme_low**: {int(ex)} (of {len(peer_signals)})\n\n")
    else:
        lines.append("_No peer_signals rows._ \n\n")
    if not anomalies.empty and "anomaly_category" in anomalies.columns:
        ac = anomalies["anomaly_category"].value_counts()
        lines.append("**Unified anomaly rows by category** (self + peer layer):\n\n")
        lines.append("- " + "; ".join(f"`{k}`: {int(v)}" for k, v in ac.items()) + "\n\n")
    elif not anomalies.empty:
        lines.append(f"- **Unified anomaly rows**: {len(anomalies)}\n\n")
    return "".join(lines)


def _trend_breaks_compact(trend_breaks: pd.DataFrame | None) -> str:
    """Compact trend-break summary with explicit short-history handling."""
    if trend_breaks is None or trend_breaks.empty:
        return "_No trend-break rows (run pipeline or provide `trend_break_signals.csv`)._\n\n"
    need = {"trend_signal_type", "trend_score", "metric", "cik", "period"}
    if not need.issubset(set(trend_breaks.columns)):
        return _df_to_md(trend_breaks.head(12), max_rows=12)
    sh = int((trend_breaks["trend_signal_type"] == "short_history").sum())
    lines = [f"- **Short-history rows**: {sh} of {len(trend_breaks)}\n"]
    focused = trend_breaks[trend_breaks["trend_signal_type"].isin(["strong_shift", "moderate_shift"])].copy()
    if focused.empty:
        lines.append("_No moderate/strong trend-break rows at current thresholds._\n\n")
        return "".join(lines)
    show_cols = [
        c
        for c in (
            "cik",
            "period",
            "metric",
            "trend_signal_type",
            "trend_score",
            "mean_shift",
            "slope_shift",
            "consecutive_direction",
            "history_points",
            "window_prior",
            "window_recent",
        )
        if c in focused.columns
    ]
    lines.append("\n")
    lines.append(_df_to_md(focused.sort_values("trend_score", ascending=False)[show_cols].head(12), max_rows=12))
    return "".join(lines)


def _unified_findings_compact(unified_findings: pd.DataFrame | None, *, top_n: int = 12) -> str:
    if unified_findings is None or unified_findings.empty:
        return "_No unified findings rows (run pipeline or provide `unified_findings.csv`)._\n\n"
    need = {"finding_source", "finding_type", "score_adjusted", "cik", "period", "metric"}
    if not need.issubset(set(unified_findings.columns)):
        return _df_to_md(unified_findings.head(top_n), max_rows=top_n)
    show_cols = [
        c
        for c in (
            "finding_source",
            "finding_type",
            "cik",
            "period",
            "metric",
            "direction",
            "score_adjusted",
            "score_raw",
            "score_penalty",
            "overlap_count",
            "overlap_sources",
            "caveat_codes",
        )
        if c in unified_findings.columns
    ]
    top = unified_findings.sort_values("score_adjusted", ascending=False).head(top_n)
    return _df_to_md(top[show_cols], max_rows=top_n)


def _top_combined_findings(unified_findings: pd.DataFrame | None, *, top_n: int = 8) -> str:
    if unified_findings is None or unified_findings.empty:
        return "_No unified findings rows._\n\n"
    need = {"finding_source", "finding_type", "score_adjusted"}
    if not need.issubset(set(unified_findings.columns)):
        return _df_to_md(unified_findings.head(top_n), max_rows=top_n)
    uf = unified_findings.copy()
    uf["_prio"] = (
        ((uf["finding_source"] == "anomaly") & (uf["finding_type"] == "combined"))
        .astype(int)
    )
    show_cols = [
        c
        for c in (
            "finding_source",
            "finding_type",
            "cik",
            "period",
            "metric",
            "direction",
            "score_adjusted",
            "score_raw",
            "score_penalty",
            "overlap_count",
            "overlap_sources",
            "caveat_codes",
        )
        if c in uf.columns
    ]
    top = uf.sort_values(["_prio", "score_adjusted"], ascending=[False, False]).head(top_n)
    return _df_to_md(top[show_cols], max_rows=top_n)


def _company_summary_compact(findings_by_company: pd.DataFrame | None, *, top_n: int = 8) -> str:
    if findings_by_company is None or findings_by_company.empty:
        return "_No company-level findings summary rows._\n\n"
    show_cols = [
        c
        for c in (
            "cik",
            "finding_count",
            "high_severity_count",
            "avg_score_adjusted",
            "sum_score_adjusted",
            "sum_score_penalty",
            "top_finding_category",
            "repeated_deterioration_count",
        )
        if c in findings_by_company.columns
    ]
    top = findings_by_company.sort_values("sum_score_adjusted", ascending=False).head(top_n)
    return _df_to_md(top[show_cols], max_rows=top_n)


def _peer_set_summary_compact(
    findings_by_metric: pd.DataFrame | None,
    findings_by_period: pd.DataFrame | None,
    *,
    top_n: int = 8,
) -> str:
    parts: list[str] = []
    if findings_by_metric is None or findings_by_metric.empty:
        parts.append("_No metric-level summary rows._\n\n")
    else:
        parts.append("**Metrics with highest adjusted severity**\n\n")
        mcols = [
            c
            for c in (
                "metric",
                "finding_count",
                "high_severity_count",
                "avg_score_adjusted",
                "sum_score_adjusted",
                "sum_score_penalty",
                "top_finding_category",
            )
            if c in findings_by_metric.columns
        ]
        parts.append(
            _df_to_md(
                findings_by_metric.sort_values("sum_score_adjusted", ascending=False).head(top_n)[mcols],
                max_rows=top_n,
            )
        )
    if findings_by_period is None or findings_by_period.empty:
        parts.append("_No period-level summary rows._\n\n")
    else:
        parts.append("\n**Periods with broad finding concentration**\n\n")
        pcols = [
            c
            for c in (
                "period",
                "finding_count",
                "high_severity_count",
                "avg_score_adjusted",
                "sum_score_adjusted",
                "sum_score_penalty",
                "top_finding_category",
            )
            if c in findings_by_period.columns
        ]
        parts.append(
            _df_to_md(
                findings_by_period.sort_values("sum_score_adjusted", ascending=False).head(top_n)[pcols],
                max_rows=top_n,
            )
        )
    return "".join(parts)


def _caveat_interpretation_notes(unified_findings: pd.DataFrame | None) -> str:
    if unified_findings is None or unified_findings.empty or "caveat_codes" not in unified_findings.columns:
        return "_No caveat-aware interpretation rows._\n\n"
    uf = unified_findings.copy()
    total = len(uf)
    with_c = uf["caveat_codes"].astype(str).str.strip().ne("none").sum()
    lines = [f"- **Findings with caveats**: {int(with_c)} of {int(total)}\n"]
    if "score_penalty" in uf.columns:
        pen = pd.to_numeric(uf["score_penalty"], errors="coerce").fillna(0.0)
        lines.append(f"- **Total caveat penalty applied**: {float(pen.sum()):.3f}\n")
        lines.append(f"- **Average penalty per finding**: {float(pen.mean()):.3f}\n")
    codes: list[str] = []
    for raw in uf["caveat_codes"].astype(str):
        s = raw.strip()
        if not s or s == "none":
            continue
        codes.extend([p.strip() for p in s.split(";") if p.strip()])
    if codes:
        vc = pd.Series(codes).value_counts().head(8)
        lines.append("- **Most frequent caveat codes**: " + "; ".join(f"`{k}`={int(v)}" for k, v in vc.items()) + "\n")
    lines.append("\n")
    return "".join(lines)


def _trustworthiness_snapshot(
    *,
    metric_coverage_summary: pd.DataFrame | None,
    extraction_caveats: pd.DataFrame | None,
    panel_caveats: pd.DataFrame | None,
    exclusions: pd.DataFrame | None,
    manual_validation_path: Path | None,
) -> str:
    """Single readable block: coverage, caveats, pipeline notes, manual validation preview."""
    parts: list[str] = ["### Trustworthiness snapshot\n"]
    parts.append("#### Metric coverage (panel)\n\n")
    parts.append(_trust_metric_coverage_compact(metric_coverage_summary))
    parts.append("#### Caveat flags (roll-ups)\n\n")
    parts.append(_trust_caveat_rollups(extraction_caveats, panel_caveats))
    parts.append("#### Pipeline effects on interpretation\n\n")
    parts.append(_trust_pipeline_interpretation_notes(exclusions))
    parts.append("#### Manual validation\n\n")
    parts.append(_credibility_manual_validation(manual_validation_path, preview_rows=6))
    return "".join(parts)


def _credibility_section(
    *,
    data_quality: pd.DataFrame | None,
    exclusions: pd.DataFrame | None,
    peer_signals: pd.DataFrame | None,
    anomalies: pd.DataFrame,
    manual_validation_path: Path | None,
    metric_coverage_summary: pd.DataFrame | None,
    extraction_caveats: pd.DataFrame | None,
    panel_caveats: pd.DataFrame | None,
    artifact_paths: Mapping[str, Path] | None = None,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> str:
    parts: list[str] = ["## Credibility & coverage\n"]
    parts.append(
        _trustworthiness_snapshot(
            metric_coverage_summary=metric_coverage_summary,
            extraction_caveats=extraction_caveats,
            panel_caveats=panel_caveats,
            exclusions=exclusions,
            manual_validation_path=manual_validation_path,
        )
    )
    parts.append("### Data quality summary\n")
    parts.append(_credibility_data_quality_compact(data_quality if data_quality is not None else pd.DataFrame()))
    parts.append("### Exclusions (pipeline)\n")
    parts.append(_credibility_exclusions_compact(exclusions))
    parts.append("### Peer-relative findings summary\n")
    parts.append(_credibility_peer_summary(peer_signals, anomalies))
    parts.append(
        _artifact_paths_footer(
            artifact_paths=artifact_paths,
            manual_validation_path=manual_validation_path,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    )
    parts.append("\n---\n\n")
    return "".join(parts)


def _anomaly_compact_columns(anomalies: pd.DataFrame) -> list[str]:
    preferred = [
        "cik",
        "period",
        "metric",
        "anomaly_category",
        "self_anomaly",
        "peer_anomaly",
        "direction",
        "value",
        "zscore",
        "self_baseline_mean",
        "self_baseline_std",
        "self_baseline_n",
        "window_max_quarters",
        "z_score_peer",
        "peer_group_n",
        "peer_deviation_strong",
        "peer_cs_pct_rank",
        "peer_cs_z",
        "peer_cs_coverage",
        "peer_cs_alert",
        "comparison_scope",
        "caveat_codes",
    ]
    return [c for c in preferred if c in anomalies.columns]


def generate_report(
    anomalies: pd.DataFrame,
    features: pd.DataFrame,
    *,
    peer_signals: pd.DataFrame | None = None,
    data_quality: pd.DataFrame | None = None,
    exclusions: pd.DataFrame | None = None,
    manual_validation_path: Path | None = None,
    workspace: RunWorkspace | None = None,
    artifact_paths: Mapping[str, str | Path] | None = None,
    use_legacy_shared_paths: bool = False,
    metric_coverage_summary: pd.DataFrame | None = None,
    extraction_caveats: pd.DataFrame | None = None,
    panel_caveats: pd.DataFrame | None = None,
    trend_breaks: pd.DataFrame | None = None,
    unified_findings: pd.DataFrame | None = None,
    findings_summary_by_company: pd.DataFrame | None = None,
    findings_summary_by_metric: pd.DataFrame | None = None,
    findings_summary_by_period: pd.DataFrame | None = None,
    top_n: int = 5,
) -> str:
    resolved_artifact_paths = _resolve_artifact_paths(
        artifact_paths=artifact_paths,
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    resolved_manual_validation_path = _resolve_manual_validation_path(
        manual_validation_path,
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )

    # Prefer in-memory frames from the caller; else artifacts on disk (e.g. MCP report-only run).
    if metric_coverage_summary is None:
        metric_coverage_summary = _try_read_artifact_csv(
            "metric_coverage_summary.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if extraction_caveats is None:
        extraction_caveats = _try_read_artifact_csv(
            "metric_caveats_extraction.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if panel_caveats is None:
        panel_caveats = _try_read_artifact_csv(
            "metric_caveats_panel.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if trend_breaks is None:
        trend_breaks = _try_read_artifact_csv(
            "trend_break_signals.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if unified_findings is None:
        unified_findings = _try_read_artifact_csv(
            "unified_findings.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if findings_summary_by_company is None:
        findings_summary_by_company = _try_read_artifact_csv(
            "findings_summary_by_company.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if findings_summary_by_metric is None:
        findings_summary_by_metric = _try_read_artifact_csv(
            "findings_summary_by_metric.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    if findings_summary_by_period is None:
        findings_summary_by_period = _try_read_artifact_csv(
            "findings_summary_by_period.csv",
            artifact_paths=resolved_artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )

    lines: list[str] = []
    lines.append("# EDGAR Anomaly Report (V1)\n")
    lines.append(
        _credibility_section(
            data_quality=data_quality,
            exclusions=exclusions,
            peer_signals=peer_signals,
            anomalies=anomalies,
            manual_validation_path=resolved_manual_validation_path,
            metric_coverage_summary=metric_coverage_summary,
            extraction_caveats=extraction_caveats,
            panel_caveats=panel_caveats,
            artifact_paths=resolved_artifact_paths,
            workspace=workspace,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    )
    lines.append("## Normalized quarterly panel (sample)\n")
    panel_cols = [c for c in _PANEL_SAMPLE_COLS if c in features.columns]
    if panel_cols:
        lines.append(_df_to_md(features[panel_cols].head(20)))
    else:
        lines.append("_No overlapping panel columns (expected at least `cik`, `period`)._\n")

    lines.append("## Feature table (sample)\n")
    feat_cols = [
        "cik",
        "period",
        "revenue_growth_qoq",
        "net_margin",
        "current_ratio",
        "debt_to_assets",
    ]
    avail = [c for c in feat_cols if c in features.columns]
    lines.append(_df_to_md(features[avail].head(20)))
    lines.append("## Trend-break signals (window shifts)\n")
    lines.append(
        "_Deterministic window comparison on feature trends: prior-window mean/slope vs recent-window mean/slope; "
        "includes explicit short-history rows._\n\n"
    )
    lines.append(_trend_breaks_compact(trend_breaks))
    lines.append("## Top combined findings\n")
    lines.append(
        "_Highest adjusted findings first; prioritizes rows where self-relative and peer-relative evidence agree._\n\n"
    )
    lines.append(_top_combined_findings(unified_findings, top_n=max(8, top_n)))
    lines.append("## Unified findings (high-level)\n")
    lines.append(
        "_Single machine-friendly table combining anomaly and trend-break findings with caveat-adjusted ranking._\n\n"
    )
    lines.append(_unified_findings_compact(unified_findings))
    lines.append("## Company-level summary\n")
    lines.append(_company_summary_compact(findings_summary_by_company))
    lines.append("## Peer-set summary\n")
    lines.append(_peer_set_summary_compact(findings_summary_by_metric, findings_summary_by_period))
    lines.append("## Caveat-aware interpretation notes\n")
    lines.append(_caveat_interpretation_notes(unified_findings))

    lines.append("## Anomaly table (unified: self + peer layer)\n")
    lines.append(
        f"_Rows: union of (1) |self z| > {config.ZSCORE_THRESHOLD} vs trailing up to {config.ZSCORE_WINDOW} quarters "
        f"(current excluded) and (2) peer-signal extremes (``peer_cs_alert`` = extreme_high/low). "
        "``anomaly_category`` = `self_relative` | `peer_relative` | `combined`. "
        "`z_score_peer` = LOO cross-section; `peer_cs_*` = full cross-section from peer_signals._ \n\n"
    )
    acols = _anomaly_compact_columns(anomalies)
    if acols:
        lines.append(_df_to_md(anomalies[acols], max_rows=25))
    else:
        lines.append(_df_to_md(anomalies, max_rows=25))

    lines.append(f"## Top {top_n} anomalies (numeric detail)\n")
    top = anomalies.head(top_n)
    if top.empty:
        lines.append("_No unified anomaly rows (self and/or peer layer empty for this run)._ \n")
    else:
        cols = _anomaly_compact_columns(top)
        if cols:
            lines.append(_df_to_md(top[cols], max_rows=top_n))
        else:
            lines.append(_df_to_md(top, max_rows=top_n))

    lines.append(f"## Top {top_n} anomaly explanations (machine-readable)\n")
    top2 = anomalies.head(top_n)
    if top2.empty:
        lines.append("_None._\n")
    else:
        if "explanation" in top2.columns:
            for _, r in top2.iterrows():
                line = str(r["explanation"])
                lines.append(f"- `{line}`\n")
        else:
            for _, r in top2.iterrows():
                z = r.get("zscore", np.nan)
                hi = "high" if (isinstance(z, (int, float)) and z > 0) else "low"
                lines.append(
                    f"- **{r['metric']}** CIK {r['cik']} {r['period']}: z={z} ({hi} vs history)\n"
                )

    lines.append("## Peer-relative detail (cross-section by period)\n")
    lines.append(
        "_Metrics: **"
        + ", ".join(PEER_SIGNAL_METRICS)
        + "**. Summary counts appear under *Credibility & coverage*. Sample of peer extremes:_ \n\n"
    )
    if peer_signals is None or peer_signals.empty:
        lines.append("_No peer signal rows._\n")
    else:
        flagged = peer_signals[peer_signals["peer_alert"].isin(["extreme_high", "extreme_low"])]
        if flagged.empty:
            lines.append("_No peer extremes at current thresholds (see `peer_signals.csv`)._\n")
        else:
            show_cols = [
                c
                for c in (
                    "cik",
                    "period",
                    "metric",
                    "peer_group_n",
                    "peer_coverage",
                    "peer_pct_rank",
                    "peer_z",
                    "peer_alert",
                )
                if c in flagged.columns
            ]
            lines.append(_df_to_md(flagged[show_cols].head(20), max_rows=20))

    return "".join(lines)
