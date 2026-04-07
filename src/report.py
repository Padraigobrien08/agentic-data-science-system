"""
Markdown report: normalized metrics, features, anomaly tables with deterministic explanations.

Credibility sections pull from in-memory pipeline outputs (or optional CSV paths for MCP).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import config
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


def _artifact_paths_footer() -> str:
    return (
        "_Artifact paths: `data/artifacts/data_quality_summary.csv`, "
        "`data/artifacts/exclusions_summary.csv`, `data/artifacts/peer_signals.csv`, "
        "`validation/manual_validation.csv`._\n"
    )


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


def _credibility_manual_validation(path: Path | None) -> str:
    """Status from ``validation/manual_validation.csv`` when the file has data rows."""
    if path is None or not path.is_file():
        return "_Manual validation: file not found at `validation/manual_validation.csv`._ \n\n"
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
    show = [c for c in ("ticker", "cik", "period", "metric", "validation_status", "checked_date") if c in mv.columns]
    if show:
        lines.append(_df_to_md(mv[show].head(8), max_rows=8))
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


def _credibility_section(
    *,
    data_quality: pd.DataFrame | None,
    exclusions: pd.DataFrame | None,
    peer_signals: pd.DataFrame | None,
    anomalies: pd.DataFrame,
    manual_validation_path: Path | None,
) -> str:
    parts: list[str] = ["## Credibility & coverage\n"]
    parts.append("### Data quality summary\n")
    parts.append(_credibility_data_quality_compact(data_quality if data_quality is not None else pd.DataFrame()))
    parts.append("### Exclusions (pipeline)\n")
    parts.append(_credibility_exclusions_compact(exclusions))
    parts.append("### Manual validation status\n")
    parts.append(_credibility_manual_validation(manual_validation_path))
    parts.append("### Peer-relative findings summary\n")
    parts.append(_credibility_peer_summary(peer_signals, anomalies))
    parts.append(_artifact_paths_footer())
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
    top_n: int = 5,
) -> str:
    if manual_validation_path is None:
        from src.manual_validation import VALIDATION_CSV_PATH

        manual_validation_path = VALIDATION_CSV_PATH

    lines: list[str] = []
    lines.append("# EDGAR Anomaly Report (V1)\n")
    lines.append(
        _credibility_section(
            data_quality=data_quality,
            exclusions=exclusions,
            peer_signals=peer_signals,
            anomalies=anomalies,
            manual_validation_path=manual_validation_path,
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

    lines.append("## Anomaly table (unified: self + peer layer)\n")
    lines.append(
        f"_Rows: union of (1) |self z| > {config.ZSCORE_THRESHOLD} vs trailing up to {config.ZSCORE_WINDOW} quarters "
        f"(current excluded) and (2) peer-signal extremes (``peer_cs_alert`` = extreme_high/low). "
        "``anomaly_category`` = `self_relative` | `peer_relative` | `combined`. "
        "`z_score_peer` = LOO cross-section; `peer_cs_*` = full cross-section from peer_signals._ \n\n"
    )
    lines.append(_df_to_md(anomalies, max_rows=50))

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
