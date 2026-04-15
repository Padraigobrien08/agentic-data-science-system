"""
Deterministic data-quality summaries for the EDGAR panel pipeline.

Produces a tidy CSV (and optional markdown section) for missingness, stage counts,
and rows dropped by the revenue requirement — no LLM, no heuristics beyond stated rules.

Per-metric coverage slices (by company / period / overall) are emitted separately by
:mod:`src.metric_coverage` as ``metric_coverage_*.csv``; see that module for definitions.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config

from .normalization import METRIC_COLUMNS, wide_panel_before_revenue_filter


def _append_row(
    rows: list[dict[str, str | float | int]],
    *,
    category: str,
    name: str,
    value: float | int,
    unit: str,
    notes: str = "",
) -> None:
    rows.append(
        {
            "category": category,
            "name": name,
            "value": value,
            "unit": unit,
            "notes": notes,
        }
    )


def compute_data_quality_summary(
    long_frames: list[pd.DataFrame],
    panel: pd.DataFrame,
    features: pd.DataFrame,
    anomalies: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a long-format table suitable for ``data_quality_summary.csv``.

    Stages measured: long (concat) → wide pre-revenue filter → final panel → features → anomalies.
    """
    rows: list[dict[str, str | float | int]] = []

    long_df = pd.concat(long_frames, ignore_index=True) if long_frames else pd.DataFrame()
    long_rows = len(long_df)
    n_companies_long = long_df["cik"].nunique() if not long_df.empty and "cik" in long_df.columns else 0

    wide_pre = wide_panel_before_revenue_filter(long_frames)
    pre_rows = len(wide_pre)
    post_rows = len(panel)
    dropped_revenue = max(0, pre_rows - post_rows)

    _append_row(rows, category="stage_count", name="long_metric_rows", value=long_rows, unit="rows")
    _append_row(rows, category="stage_count", name="distinct_cik_long", value=int(n_companies_long), unit="companies")
    _append_row(
        rows, category="stage_count", name="wide_panel_rows_before_revenue_required", value=pre_rows, unit="rows"
    )
    _append_row(rows, category="stage_count", name="panel_rows_after_revenue_required", value=post_rows, unit="rows")
    _append_row(rows, category="stage_count", name="feature_rows", value=len(features), unit="rows")
    _append_row(rows, category="stage_count", name="anomaly_rows", value=len(anomalies), unit="rows")

    _append_row(
        rows,
        category="drop_rule",
        name="rows_removed_missing_revenue",
        value=dropped_revenue,
        unit="rows",
        notes="wide_panel_before_revenue_filter minus panel (revenue required)",
    )

    # Missingness by metric (panel, after revenue filter)
    if not panel.empty:
        for col in METRIC_COLUMNS:
            if col not in panel.columns:
                _append_row(
                    rows,
                    category="missingness_metric",
                    name=col,
                    value=1.0,
                    unit="frac_na",
                    notes="column absent treated as all missing",
                )
                continue
            frac = float(panel[col].isna().mean())
            _append_row(
                rows,
                category="missingness_metric",
                name=col,
                value=round(frac, 6),
                unit="frac_na",
            )

        # Missingness by company (fraction of metric cells NA per CIK)
        mcols = [c for c in METRIC_COLUMNS if c in panel.columns]
        if mcols:
            for cik, g in panel.groupby("cik"):
                cells = len(g) * len(mcols)
                na = int(g[mcols].isna().sum().sum())
                frac = float(na / cells) if cells else 0.0
                _append_row(
                    rows,
                    category="missingness_company",
                    name=str(int(cik)),
                    value=round(frac, 6),
                    unit="frac_na_cells",
                    notes=f"na_cells={na},total_cells={cells}",
                )

    return pd.DataFrame(rows)


def format_data_quality_markdown(
    dq: pd.DataFrame,
    artifact_paths: dict[str, Path] | None = None,
    *,
    use_legacy_shared_paths: bool = True,
) -> str:
    """Short markdown section for embedding in ``report.md`` (deterministic, from summary table)."""
    lines: list[str] = ["## Data quality summary\n", "\n"]
    if dq.empty:
        lines.append("_No data quality statistics (empty pipeline outputs)._\n")
        return "".join(lines)

    stages = dq[dq["category"] == "stage_count"]
    drops = dq[dq["category"] == "drop_rule"]
    mm = dq[dq["category"] == "missingness_metric"]

    if not stages.empty:
        lines.append("### Stage row counts\n\n")
        for _, r in stages.iterrows():
            lines.append(f"- **{r['name']}**: {r['value']} ({r['unit']})\n")
        lines.append("\n")

    if not drops.empty:
        lines.append("### Drops\n\n")
        for _, r in drops.iterrows():
            note = f" — {r['notes']}" if pd.notna(r["notes"]) and str(r["notes"]).strip() else ""
            lines.append(f"- **{r['name']}**: {r['value']} {r['unit']}{note}\n")
        lines.append("\n")

    if not mm.empty:
        lines.append("### Missingness by metric (panel, fraction NA)\n\n")
        for _, r in mm.iterrows():
            lines.append(f"- **{r['name']}**: {r['value']}\n")
        lines.append("\n")

    mc = dq[dq["category"] == "missingness_company"]
    if not mc.empty:
        lines.append("### Missingness by company (fraction of metric cells NA)\n\n")
        for _, r in mc.head(20).iterrows():
            note = f" ({r['notes']})" if pd.notna(r["notes"]) and str(r["notes"]).strip() else ""
            lines.append(f"- CIK **{r['name']}**: {r['value']}{note}\n")
        if len(mc) > 20:
            lines.append(f"\n_…and {len(mc) - 20} more companies (see CSV)._\n")
        lines.append("\n")

    lines.append(
        _data_quality_artifact_footer(
            artifact_paths,
            use_legacy_shared_paths=use_legacy_shared_paths,
        )
    )
    return "".join(lines)


def _repo_rel_path(path: Path) -> str:
    root = Path(config.PROJECT_ROOT).resolve()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _data_quality_artifact_footer(
    artifact_paths: dict[str, Path] | None = None,
    *,
    use_legacy_shared_paths: bool = True,
) -> str:
    if artifact_paths is not None and "data_quality" in artifact_paths:
        return f"_Full machine-readable table: `{_repo_rel_path(artifact_paths['data_quality'])}`._\n"
    if use_legacy_shared_paths:
        return "_Full machine-readable table: `data/artifacts/data_quality_summary.csv`._\n"
    return "_Full machine-readable table path unavailable._\n"
