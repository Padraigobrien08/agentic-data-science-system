"""
Lightweight caveat flags for extracted and normalized metrics.

**Extraction caveats** (see :func:`src.metric_extraction.extract_metrics_with_extraction_caveats`)
are emitted per ``(cik, period, metric)`` from tag resolution and unit axes in companyfacts.

**Panel caveats** are computed on the **final wide panel** (after the revenue requirement) and
describe time-series sparsity, cross-section size, and missing predecessor periods — no scoring,
only deterministic rules aligned with :mod:`config` and :mod:`src.anomaly` peer thresholds.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from .anomaly import MIN_PEER_GROUP
from .metric_extraction import sort_period_key

# Stable codes (subset may appear per row).
CAVEAT_CODE_LOW_PERIOD_COUNT = "low_period_count"
CAVEAT_CODE_MISSING_PRIOR_PERIOD = "missing_prior_period"
CAVEAT_CODE_SPARSE_HISTORY = "sparse_history"
CAVEAT_CODE_LIMITED_PEER_COVERAGE = "limited_peer_coverage"


def prior_fiscal_period(period: str) -> str | None:
    """Immediate predecessor fiscal quarter, e.g. ``2020-Q2`` → ``2020-Q1``; ``2020-Q1`` → ``2019-Q4``."""
    try:
        y_str, q = str(period).split("-", 1)
        y = int(y_str)
    except (ValueError, TypeError):
        return None
    order = ("Q1", "Q2", "Q3", "Q4")
    if q not in order:
        return None
    i = order.index(q)
    if i == 0:
        return f"{y - 1}-Q4"
    return f"{y}-{order[i - 1]}"


def _sorted_periods_for_cik(panel: pd.DataFrame, cik: int) -> list[str]:
    sub = panel.loc[panel["cik"] == cik, "period"].astype(str).unique()
    s = pd.Series(sub)
    order = sort_period_key(s)
    return [str(x) for _, x in sorted(zip(order, sub), key=lambda t: t[0])]


def compute_panel_metric_caveats(panel: pd.DataFrame) -> pd.DataFrame:
    """
    One row per ``(cik, period)`` in the panel with ``caveat_codes`` (semicolon-separated, sorted).

    Flags:

    * ``low_period_count`` — this CIK has fewer than :data:`config.CAVEAT_MIN_PERIODS_PER_CIK`
      rows in the panel (thin history in the lookback window).
    * ``missing_prior_period`` — the immediately preceding fiscal quarter is absent for this CIK
      in the panel (gap or window edge).
    * ``sparse_history`` — fewer than :data:`config.ZSCORE_WINDOW` prior fiscal quarters exist
      for this CIK in the panel before the current period (by fiscal order in this panel;
      rolling self-baseline may be thin; not a statement about filing quality).
    * ``limited_peer_coverage`` — fewer than ``MIN_PEER_GROUP`` distinct CIKs share this period
      (peer cross-section rules may not apply).
    """
    cols = ["cik", "period", "caveat_codes"]
    if panel.empty or "cik" not in panel.columns or "period" not in panel.columns:
        return pd.DataFrame(columns=cols)

    period_n = panel.groupby("period")["cik"].nunique().to_dict()
    rows: list[dict[str, str | int]] = []

    for cik in sorted(panel["cik"].dropna().unique()):
        cik = int(cik)
        sorted_p = _sorted_periods_for_cik(panel, cik)
        n_periods_cik = len(sorted_p)
        pos = {p: i for i, p in enumerate(sorted_p)}

        for period in sorted_p:
            codes: list[str] = []
            if n_periods_cik < config.CAVEAT_MIN_PERIODS_PER_CIK:
                codes.append(CAVEAT_CODE_LOW_PERIOD_COUNT)

            pr = prior_fiscal_period(period)
            if pr is not None and pr not in set(sorted_p):
                codes.append(CAVEAT_CODE_MISSING_PRIOR_PERIOD)

            idx = pos.get(period, 0)
            if idx < config.ZSCORE_WINDOW:
                codes.append(CAVEAT_CODE_SPARSE_HISTORY)

            if period_n.get(period, 0) < MIN_PEER_GROUP:
                codes.append(CAVEAT_CODE_LIMITED_PEER_COVERAGE)

            codes_sorted = ";".join(sorted(set(codes)))
            rows.append({"cik": cik, "period": str(period), "caveat_codes": codes_sorted})

    out = pd.DataFrame(rows, columns=cols)
    out = out.sort_values(["cik", "period"]).reset_index(drop=True)
    return out


def filter_extraction_caveats_to_panel(
    extraction_caveats: pd.DataFrame,
    panel: pd.DataFrame,
) -> pd.DataFrame:
    """Keep extraction caveat rows whose ``(cik, period)`` appears in the final panel."""
    if extraction_caveats.empty or panel.empty:
        return pd.DataFrame(
            columns=["cik", "period", "metric", "source_tag", "n_candidates", "caveat_codes"]
        )
    keys = panel[["cik", "period"]].drop_duplicates()
    merged = extraction_caveats.merge(keys, on=["cik", "period"], how="inner")
    return merged.sort_values(["cik", "period", "metric"]).reset_index(drop=True)


def write_metric_caveats_artifacts(
    panel: pd.DataFrame,
    extraction_caveats_long: pd.DataFrame | None,
) -> dict[str, Path]:
    """Write ``metric_caveats_extraction.csv`` and ``metric_caveats_panel.csv`` under artifacts."""
    art = config.DATA_ARTIFACTS
    art.mkdir(parents=True, exist_ok=True)
    ext = (
        filter_extraction_caveats_to_panel(extraction_caveats_long, panel)
        if extraction_caveats_long is not None
        else pd.DataFrame(
            columns=["cik", "period", "metric", "source_tag", "n_candidates", "caveat_codes"]
        )
    )
    pan = compute_panel_metric_caveats(panel)
    p_ext = art / "metric_caveats_extraction.csv"
    p_pan = art / "metric_caveats_panel.csv"
    ext.to_csv(p_ext, index=False)
    pan.to_csv(p_pan, index=False)
    return {"metric_caveats_extraction": p_ext.resolve(), "metric_caveats_panel": p_pan.resolve()}
