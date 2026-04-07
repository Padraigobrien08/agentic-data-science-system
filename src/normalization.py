"""
Combine per-company metric tables into one panel (wide) aligned by fiscal quarter.
"""

from __future__ import annotations

import logging

import pandas as pd

from . import exclusions as ex
from .metric_extraction import sort_period_key
from .metric_mapping import METRIC_COLUMN_ORDER

_log = logging.getLogger(__name__)

# Panel metric columns — order matches :data:`src.metric_mapping.METRIC_COLUMN_ORDER`.
METRIC_COLUMNS = list(METRIC_COLUMN_ORDER)


def _numeric_coercion_losses(series: pd.Series) -> int:
    """Cells that were non-null before ``pd.to_numeric(..., errors='coerce')`` but null after."""
    if series.empty:
        return 0
    after = pd.to_numeric(series, errors="coerce")
    before_ok = series.notna()
    lost = before_ok & after.isna()
    return int(lost.sum())


def wide_panel_before_revenue_filter(
    long_frames: list[pd.DataFrame],
    *,
    exclusion_counts: dict[str, int] | None = None,
) -> pd.DataFrame:
    """
    Wide panel after pivot and numeric coercion, **before** dropping rows with missing revenue.

    Used for data-quality accounting of rows removed by the revenue requirement.
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

    for c in METRIC_COLUMNS:
        if c not in wide.columns:
            wide[c] = pd.NA

    wide = wide[["cik", "period"] + [c for c in METRIC_COLUMNS if c in wide.columns]]

    wide["_pk"] = sort_period_key(wide["period"].astype(str))
    wide = wide.sort_values(["cik", "_pk"]).drop(columns=["_pk"])

    for c in METRIC_COLUMNS:
        if c in wide.columns:
            n = _numeric_coercion_losses(wide[c])
            ex.bump(exclusion_counts, ex.NON_NUMERIC_COERCION, n)
            wide[c] = pd.to_numeric(wide[c], errors="coerce")

    if exclusion_counts and exclusion_counts.get(ex.NON_NUMERIC_COERCION, 0) > 0:
        _log.info(
            "normalization: non_numeric_coercion losses=%s",
            exclusion_counts.get(ex.NON_NUMERIC_COERCION, 0),
        )

    return wide.reset_index(drop=True)


def build_panel(
    long_frames: list[pd.DataFrame],
    *,
    exclusion_counts: dict[str, int] | None = None,
) -> pd.DataFrame:
    """
    long_frames: list of extract_metrics outputs (each may be one CIK).
    Returns wide DataFrame: cik, period, <metric columns>.
    """
    wide = wide_panel_before_revenue_filter(long_frames, exclusion_counts=exclusion_counts)
    if wide.empty:
        return wide
    pre = len(wide)
    wide = wide.dropna(subset=["revenue"], how="any")
    ex.bump(exclusion_counts, ex.MISSING_REQUIRED_METRIC, max(0, pre - len(wide)))
    if exclusion_counts and exclusion_counts.get(ex.MISSING_REQUIRED_METRIC, 0) > 0:
        _log.info(
            "normalization: rows dropped missing revenue=%s",
            exclusion_counts.get(ex.MISSING_REQUIRED_METRIC, 0),
        )
    return wide.reset_index(drop=True)
