"""
Metric coverage tables for the normalized wide panel.

**Where this is measured:** immediately **after** :func:`src.normalization.build_panel`
(10-K/10-Q quarterly facts pivoted wide, rows without revenue dropped). Each
``(cik, period)`` row is one *slot* per metric: a value is *available* if the cell is
non-null, *missing* if null or the metric column is absent.

**Why here:** downstream features and anomalies use this panel; coverage at this stage
reflects extractability + mapping + pivot alignment, before derived features fill or
drop additional cells.

Outputs are deterministic (sorted keys, fixed column order) for diffing and tooling.
"""

from __future__ import annotations

import pandas as pd

from .metric_extraction import sort_period_key
from .normalization import METRIC_COLUMNS

# --- Output column schemas (machine-friendly, stable names) ---
SUMMARY_COLUMNS: tuple[str, ...] = (
    "metric_name",
    "n_slots",
    "available_count",
    "missing_count",
    "coverage_ratio",
)

BY_COMPANY_COLUMNS: tuple[str, ...] = (
    "cik",
    "metric_name",
    "n_periods",
    "available_count",
    "missing_count",
    "coverage_ratio",
)

BY_PERIOD_COLUMNS: tuple[str, ...] = (
    "period",
    "metric_name",
    "n_companies",
    "available_count",
    "missing_count",
    "coverage_ratio",
)


def _series_for_metric(panel: pd.DataFrame, metric: str) -> pd.Series:
    if metric not in panel.columns:
        return pd.Series(pd.NA, index=panel.index, dtype="Float64")
    return panel[metric]


def compute_metric_coverage_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per metric: availability across all ``(cik, period)`` panel rows."""
    rows: list[dict[str, str | int | float]] = []
    n_slots = len(panel)
    for m in METRIC_COLUMNS:
        s = _series_for_metric(panel, m)
        avail = int(s.notna().sum()) if n_slots else 0
        miss = int(s.isna().sum()) if n_slots else 0
        ratio = round(avail / n_slots, 6) if n_slots else 0.0
        rows.append(
            {
                "metric_name": m,
                "n_slots": n_slots,
                "available_count": avail,
                "missing_count": miss,
                "coverage_ratio": ratio,
            }
        )
    return pd.DataFrame(rows, columns=list(SUMMARY_COLUMNS))


def compute_metric_coverage_by_company(panel: pd.DataFrame) -> pd.DataFrame:
    """Per CIK and metric: counts over that company's periods in the panel."""
    rows: list[dict[str, str | int | float]] = []
    if panel.empty or "cik" not in panel.columns:
        return pd.DataFrame(columns=list(BY_COMPANY_COLUMNS))

    for cik, g in panel.groupby("cik", sort=True):
        n_periods = len(g)
        for m in METRIC_COLUMNS:
            s = _series_for_metric(g, m)
            avail = int(s.notna().sum())
            miss = int(s.isna().sum())
            ratio = round(avail / n_periods, 6) if n_periods else 0.0
            rows.append(
                {
                    "cik": int(cik),
                    "metric_name": m,
                    "n_periods": n_periods,
                    "available_count": avail,
                    "missing_count": miss,
                    "coverage_ratio": ratio,
                }
            )
    return pd.DataFrame(rows, columns=list(BY_COMPANY_COLUMNS))


def compute_metric_coverage_by_period(panel: pd.DataFrame) -> pd.DataFrame:
    """Per fiscal period and metric: counts over companies present in that period."""
    rows: list[dict[str, str | int | float]] = []
    if panel.empty or "period" not in panel.columns:
        return pd.DataFrame(columns=list(BY_PERIOD_COLUMNS))

    for period, g in panel.groupby("period", sort=False):
        n_companies = len(g)
        for m in METRIC_COLUMNS:
            s = _series_for_metric(g, m)
            avail = int(s.notna().sum())
            miss = int(s.isna().sum())
            ratio = round(avail / n_companies, 6) if n_companies else 0.0
            rows.append(
                {
                    "period": str(period),
                    "metric_name": m,
                    "n_companies": n_companies,
                    "available_count": avail,
                    "missing_count": miss,
                    "coverage_ratio": ratio,
                }
            )

    out = pd.DataFrame(rows, columns=list(BY_PERIOD_COLUMNS))
    if out.empty:
        return out
    out = out.copy()
    out["_pk"] = sort_period_key(out["period"].astype(str))
    out = out.sort_values(["_pk", "metric_name"]).drop(columns=["_pk"]).reset_index(drop=True)
    return out


def compute_metric_coverage_tables(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """All three coverage tables from the wide panel (see module docstring)."""
    return {
        "summary": compute_metric_coverage_summary(panel),
        "by_company": compute_metric_coverage_by_company(panel),
        "by_period": compute_metric_coverage_by_period(panel),
    }
