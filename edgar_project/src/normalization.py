"""
Combine per-company metric tables into one panel (wide) aligned by fiscal quarter.
"""

from __future__ import annotations

import pandas as pd

from .metric_extraction import sort_period_key

METRIC_COLUMNS = [
    "revenue",
    "net_income",
    "total_assets",
    "total_liabilities",
    "operating_cash_flow",
    "current_assets",
    "current_liabilities",
]


def build_panel(long_frames: list[pd.DataFrame]) -> pd.DataFrame:
    """
    long_frames: list of extract_metrics outputs (each may be one CIK).
    Returns wide DataFrame: cik, period, <metric columns>.
    """
    if not long_frames:
        return pd.DataFrame(columns=["cik", "period"] + METRIC_COLUMNS)

    long_df = pd.concat(long_frames, ignore_index=True)
    if long_df.empty:
        return pd.DataFrame(columns=["cik", "period"] + METRIC_COLUMNS)

    wide = long_df.pivot_table(
        index=["cik", "period"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).reset_index()

    # Ensure column names
    for c in METRIC_COLUMNS:
        if c not in wide.columns:
            wide[c] = pd.NA

    wide = wide[["cik", "period"] + [c for c in METRIC_COLUMNS if c in wide.columns]]

    # Sort periods chronologically
    wide["_pk"] = sort_period_key(wide["period"].astype(str))
    wide = wide.sort_values(["cik", "_pk"]).drop(columns=["_pk"])

    # Drop rows with missing core fields or non-numeric garbage
    for c in METRIC_COLUMNS:
        if c in wide.columns:
            wide[c] = pd.to_numeric(wide[c], errors="coerce")

    # Require revenue + at least one of assets/liabilities for a minimal valid row
    wide = wide.dropna(subset=["revenue"], how="any")

    wide = wide.reset_index(drop=True)
    return wide
