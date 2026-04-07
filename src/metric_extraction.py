"""
Map SEC XBRL (us-gaap) company facts to a long tidy table:
cik | period | metric | value
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from . import exclusions as ex

_log = logging.getLogger(__name__)

# Tag priority (first match wins for a given fiscal period).
METRIC_TAGS: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
    ],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
    ],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
}

ALLOWED_FORMS = frozenset({"10-K", "10-Q"})
QUARTER_FPS = frozenset({"Q1", "Q2", "Q3", "Q4"})


def _year_cutoff(years: int) -> int:
    return datetime.now(timezone.utc).year - years


def _gather_tag_rows(
    facts_json: dict[str, Any],
    tag: str,
    *,
    cik: int,
    year_min: int,
    exclusion_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    facts = facts_json.get("facts") or {}
    usgaap = facts.get("us-gaap") or {}
    concept = usgaap.get(tag)
    if not concept:
        return out
    units = concept.get("units") or {}
    for unit_key, entries in units.items():
        if unit_key != "USD":
            # Exclude facts reported in non-USD units (e.g. shares, pure).
            n = len(entries) if isinstance(entries, list) else 1
            ex.bump(exclusion_counts, ex.UNSUPPORTED_UNIT, n)
            continue
        if not isinstance(entries, list):
            ex.bump(exclusion_counts, ex.INVALID_ENTRY_SHAPE, 1)
            continue
        for e in entries:
            if not isinstance(e, dict):
                ex.bump(exclusion_counts, ex.INVALID_ENTRY_SHAPE, 1)
                continue
            form = e.get("form")
            fp = e.get("fp")
            fy = e.get("fy")
            if form not in ALLOWED_FORMS:
                ex.bump(exclusion_counts, ex.INVALID_FORM, 1)
                continue
            if fp not in QUARTER_FPS:
                ex.bump(exclusion_counts, ex.INVALID_PERIOD, 1)
                continue
            if fy is None:
                ex.bump(exclusion_counts, ex.INVALID_FISCAL_YEAR, 1)
                continue
            try:
                fy_int = int(fy)
            except (TypeError, ValueError):
                ex.bump(exclusion_counts, ex.INVALID_FISCAL_YEAR, 1)
                continue
            if fy_int < year_min:
                ex.bump(exclusion_counts, ex.YEAR_OUT_OF_RANGE, 1)
                continue
            val = e.get("val")
            if val is None:
                ex.bump(exclusion_counts, ex.NULL_FACT_VALUE, 1)
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                ex.bump(exclusion_counts, ex.NON_NUMERIC, 1)
                continue
            out.append(
                {
                    "cik": cik,
                    "fy": fy_int,
                    "fp": fp,
                    "period": f"{fy_int}-{fp}",
                    "metric": None,  # set later
                    "tag": tag,
                    "value": v,
                    "filed": e.get("filed") or "",
                    "form": form,
                }
            )
    return out


def _pick_best_per_period(rows: list[dict[str, Any]], tag_order: list[str]) -> dict[tuple[str, int, str], dict[str, Any]]:
    """(metric, fy, fp) -> row; prefer earlier tag in tag_order, then later filed."""
    priority = {t: i for i, t in enumerate(tag_order)}
    best: dict[tuple[str, int, str], dict[str, Any]] = {}
    for r in rows:
        key = (r["metric"], r["fy"], r["fp"])
        tag = r["tag"]
        pr = priority.get(tag, 999)
        cur = best.get(key)
        if cur is None:
            best[key] = r
            continue
        cur_pr = priority.get(cur["tag"], 999)
        if pr < cur_pr:
            best[key] = r
        elif pr == cur_pr:
            if (r.get("filed") or "") > (cur.get("filed") or ""):
                best[key] = r
    return best


def extract_metrics(
    facts_json: dict[str, Any],
    cik: int,
    *,
    years: int = 5,
    exclusion_counts: dict[str, int] | None = None,
) -> pd.DataFrame:
    """
    Parse companyfacts JSON into a long DataFrame.
    Ignores non-USD and non–10-K/10-Q quarterly facts.
    """
    year_min = _year_cutoff(years)
    all_rows: list[dict[str, Any]] = []

    for metric_name, tags in METRIC_TAGS.items():
        tag_order = list(tags)
        for tag in tags:
            got = _gather_tag_rows(
                facts_json, tag, cik=cik, year_min=year_min, exclusion_counts=exclusion_counts
            )
            for r in got:
                r = dict(r)
                r["metric"] = metric_name
                r["tag"] = tag
                all_rows.append(r)

    if not all_rows:
        if exclusion_counts and sum(exclusion_counts.values()) > 0:
            _log.info("metric_extraction cik=%s: no rows after filters; counts=%s", cik, exclusion_counts)
        return pd.DataFrame(columns=["cik", "period", "metric", "value"])

    # Dedupe: per (metric, fy, fp) choose best tag (drops alternate tags / filings).
    by_metric: dict[str, list[str]] = {m: METRIC_TAGS[m] for m in METRIC_TAGS}
    final_keys: list[dict[str, Any]] = []
    for metric_name in METRIC_TAGS:
        mrows = [r for r in all_rows if r["metric"] == metric_name]
        best_map = _pick_best_per_period(mrows, by_metric[metric_name])
        ex.bump(exclusion_counts, ex.DUPLICATE_RESOLVED, max(0, len(mrows) - len(best_map)))
        final_keys.extend(best_map.values())

    df = pd.DataFrame(final_keys)
    if df.empty:
        return pd.DataFrame(columns=["cik", "period", "metric", "value"])

    pre_dedupe = len(df)
    df = df[["cik", "period", "metric", "value"]].drop_duplicates(
        subset=["cik", "period", "metric"], keep="first"
    )
    ex.bump(exclusion_counts, ex.DROP_DUPLICATE_ROW, max(0, pre_dedupe - len(df)))
    df = df.sort_values(["cik", "period", "metric"]).reset_index(drop=True)

    if exclusion_counts and sum(exclusion_counts.values()) > 0:
        _log.info("metric_extraction cik=%s exclusions: %s", cik, dict(sorted(exclusion_counts.items())))

    return df


def sort_period_key(series: pd.Series) -> pd.Categorical:
    """Order fiscal periods Q1..Q4 within year."""

    def key(p: str) -> tuple[int, int]:
        try:
            y, q = p.split("-", 1)
            qi = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}.get(q, 0)
            return (int(y), qi)
        except Exception:
            return (0, 0)

    return series.map(key)
