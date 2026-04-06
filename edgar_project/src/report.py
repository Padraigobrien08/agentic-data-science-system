"""
Markdown report: normalized metrics, features, anomaly table, top explanations.
"""

from __future__ import annotations

import pandas as pd

import config


def _df_to_md(df: pd.DataFrame, max_rows: int = 30) -> str:
    if df.empty:
        return "_No rows._\n"
    show = df.head(max_rows)
    return show.to_markdown(index=False) + "\n"


def generate_report(
    anomalies: pd.DataFrame,
    features: pd.DataFrame,
    *,
    top_n: int = 5,
) -> str:
    lines: list[str] = []
    lines.append("# EDGAR Anomaly Report (V1)\n")
    lines.append("## Normalized quarterly panel (sample)\n")
    lines.append(_df_to_md(features[["cik", "period", "revenue", "net_income", "total_assets", "total_liabilities"]].head(20)))

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

    lines.append("## Anomaly table (|z| > threshold)\n")
    lines.append(_df_to_md(anomalies, max_rows=50))

    lines.append(f"## Top {top_n} anomalies (by |z|)\n")
    top = anomalies.head(top_n)
    if top.empty:
        lines.append("_No anomalies exceeded the z-score threshold._\n")
    else:
        lines.append(_df_to_md(top, max_rows=top_n))
        lines.append("### Brief notes\n")
        for _, r in top.iterrows():
            hi = "high" if r["zscore"] > 0 else "low"
            lines.append(
                f"- **{r['metric']}** (period {r['period']}, CIK {r['cik']}): z = {r['zscore']:.2f} — "
                f"unusually {hi} vs the prior {config.ZSCORE_WINDOW} quarters (rolling mean/std).\n"
            )

    return "".join(lines)
