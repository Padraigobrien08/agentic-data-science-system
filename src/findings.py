"""
Unified high-level findings table for downstream consumers.

Combines:
  - anomaly findings (self/peer/combined)
  - trend-break findings (moderate/strong shifts)

Deterministic, compact, and provenance-preserving.
"""

from __future__ import annotations

import pandas as pd

UNIFIED_FINDINGS_COLUMNS: tuple[str, ...] = (
    "finding_id",
    "finding_source",
    "finding_type",
    "cik",
    "period",
    "metric",
    "direction",
    "score_raw",
    "score_adjusted",
    "score_penalty",
    "overlap_count",
    "overlap_sources",
    "caveat_codes",
    "explanation_summary",
    "provenance_artifacts",
)
FINDINGS_SUMMARY_BY_COMPANY_COLUMNS: tuple[str, ...] = (
    "cik",
    "finding_count",
    "high_severity_count",
    "avg_score_adjusted",
    "sum_score_adjusted",
    "sum_score_penalty",
    "top_finding_category",
    "repeated_deterioration_count",
)
FINDINGS_SUMMARY_BY_METRIC_COLUMNS: tuple[str, ...] = (
    "metric",
    "finding_count",
    "high_severity_count",
    "avg_score_adjusted",
    "sum_score_adjusted",
    "sum_score_penalty",
    "top_finding_category",
)
FINDINGS_SUMMARY_BY_PERIOD_COLUMNS: tuple[str, ...] = (
    "period",
    "finding_count",
    "high_severity_count",
    "avg_score_adjusted",
    "sum_score_adjusted",
    "sum_score_penalty",
    "top_finding_category",
)

# Extends unified rows with deterministic deterioration routing metadata (CSV / planner consumers).
DETERIORATION_FOCUS_EXTRA_COLUMNS: tuple[str, ...] = (
    "deterioration_axis",
    "deteriorating_period_count",
    "stress_period_count",
    "multi_period_stress",
    "deterioration_kind",
    "deterioration_priority_score",
    "deterioration_priority_rank",
    "one_off_anomaly_only",
)
DETERIORATION_FOCUS_COLUMNS: tuple[str, ...] = UNIFIED_FINDINGS_COLUMNS + DETERIORATION_FOCUS_EXTRA_COLUMNS

_SOURCE_PRIORITY: dict[str, int] = {"anomaly": 0, "trend_break": 1}
_TREND_KEEP_TYPES = frozenset({"moderate_shift", "strong_shift"})
_HIGH_SEVERITY_THRESHOLD = 2.0


def build_unified_findings(
    anomalies: pd.DataFrame,
    trend_breaks: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    if anomalies is not None and not anomalies.empty:
        for _, r in anomalies.iterrows():
            cik = int(r["cik"])
            period = str(r["period"])
            metric = str(r["metric"])
            ftype = str(r.get("anomaly_category", "anomaly"))
            direction = str(r.get("direction", "none"))
            raw = float(r.get("combined_score_raw", r.get("combined_score", 0.0)) or 0.0)
            adj = float(r.get("combined_score_adjusted", r.get("combined_score", raw)) or raw)
            pen = float(r.get("combined_penalty_total", max(0.0, raw - adj)))
            caveats = str(r.get("caveat_codes", "none") or "none")
            expl = str(r.get("combined_explanation", r.get("explanation", "")))
            rows.append(
                {
                    "finding_id": f"anomaly:{cik}:{period}:{metric}:{ftype}",
                    "finding_source": "anomaly",
                    "finding_type": ftype,
                    "cik": cik,
                    "period": period,
                    "metric": metric,
                    "direction": direction,
                    "score_raw": raw,
                    "score_adjusted": adj,
                    "score_penalty": pen,
                    "overlap_count": 1,
                    "overlap_sources": "anomaly",
                    "caveat_codes": caveats,
                    "explanation_summary": expl,
                    "provenance_artifacts": "anomalies_csv;peer_signals_csv",
                }
            )

    if trend_breaks is not None and not trend_breaks.empty:
        tb = trend_breaks[trend_breaks["trend_signal_type"].isin(_TREND_KEEP_TYPES)].copy()
        for _, r in tb.iterrows():
            cik = int(r["cik"])
            period = str(r["period"])
            metric = str(r["metric"])
            ftype = str(r["trend_signal_type"])
            score = float(r.get("trend_score", 0.0) or 0.0)
            direction = str(r.get("consecutive_direction", "mixed"))
            expl = str(r.get("explanation", ""))
            rows.append(
                {
                    "finding_id": f"trend:{cik}:{period}:{metric}:{ftype}",
                    "finding_source": "trend_break",
                    "finding_type": ftype,
                    "cik": cik,
                    "period": period,
                    "metric": metric,
                    "direction": direction,
                    "score_raw": score,
                    "score_adjusted": score,
                    "score_penalty": 0.0,
                    "overlap_count": 1,
                    "overlap_sources": "trend_break",
                    "caveat_codes": "none",
                    "explanation_summary": expl,
                    "provenance_artifacts": "trend_break_signals_csv;features_csv",
                }
            )

    if not rows:
        return pd.DataFrame(columns=list(UNIFIED_FINDINGS_COLUMNS))

    out = pd.DataFrame(rows).reindex(columns=list(UNIFIED_FINDINGS_COLUMNS))
    key_cols = ["cik", "period", "metric"]
    grp = out.groupby(key_cols, sort=False)["finding_source"]
    out["overlap_count"] = grp.transform("nunique").astype(int)
    out["overlap_sources"] = grp.transform(lambda s: ";".join(sorted(set(str(x) for x in s))))
    out["_src_ord"] = out["finding_source"].map(_SOURCE_PRIORITY).fillna(99)
    out = out.sort_values(
        ["score_adjusted", "score_raw", "_src_ord", "cik", "period", "metric", "finding_type"],
        ascending=[False, False, True, True, True, True, True],
        kind="mergesort",
    ).drop(columns=["_src_ord"]).reset_index(drop=True)
    return out


def _top_category(series: pd.Series) -> str:
    if series.empty:
        return "none"
    vc = series.astype(str).value_counts()
    if vc.empty:
        return "none"
    return str(sorted(vc[vc == vc.max()].index)[0])


def build_findings_summary_by_company(unified_findings: pd.DataFrame) -> pd.DataFrame:
    if unified_findings.empty:
        return pd.DataFrame(columns=list(FINDINGS_SUMMARY_BY_COMPANY_COLUMNS))
    df = unified_findings.copy()
    df["score_adjusted"] = pd.to_numeric(df["score_adjusted"], errors="coerce").fillna(0.0)
    df["score_penalty"] = pd.to_numeric(df["score_penalty"], errors="coerce").fillna(0.0)
    g = df.groupby("cik", sort=True)
    out = g.agg(
        finding_count=("finding_id", "count"),
        high_severity_count=("score_adjusted", lambda s: int((s >= _HIGH_SEVERITY_THRESHOLD).sum())),
        avg_score_adjusted=("score_adjusted", "mean"),
        sum_score_adjusted=("score_adjusted", "sum"),
        sum_score_penalty=("score_penalty", "sum"),
        top_finding_category=("finding_type", _top_category),
    ).reset_index()
    rep = (
        df[df["direction"] == "deteriorating"]
        .groupby(["cik", "metric"])
        .size()
        .reset_index(name="n")
    )
    rep = rep[rep["n"] >= 2]
    rep_count = rep.groupby("cik").size().to_dict()
    out["repeated_deterioration_count"] = out["cik"].map(lambda c: int(rep_count.get(c, 0)))
    out = out.reindex(columns=list(FINDINGS_SUMMARY_BY_COMPANY_COLUMNS))
    return out.sort_values(["sum_score_adjusted", "finding_count", "cik"], ascending=[False, False, True], kind="mergesort").reset_index(drop=True)


def build_findings_summary_by_metric(unified_findings: pd.DataFrame) -> pd.DataFrame:
    if unified_findings.empty:
        return pd.DataFrame(columns=list(FINDINGS_SUMMARY_BY_METRIC_COLUMNS))
    df = unified_findings.copy()
    df["score_adjusted"] = pd.to_numeric(df["score_adjusted"], errors="coerce").fillna(0.0)
    df["score_penalty"] = pd.to_numeric(df["score_penalty"], errors="coerce").fillna(0.0)
    out = (
        df.groupby("metric", sort=True)
        .agg(
            finding_count=("finding_id", "count"),
            high_severity_count=("score_adjusted", lambda s: int((s >= _HIGH_SEVERITY_THRESHOLD).sum())),
            avg_score_adjusted=("score_adjusted", "mean"),
            sum_score_adjusted=("score_adjusted", "sum"),
            sum_score_penalty=("score_penalty", "sum"),
            top_finding_category=("finding_type", _top_category),
        )
        .reset_index()
        .reindex(columns=list(FINDINGS_SUMMARY_BY_METRIC_COLUMNS))
    )
    return out.sort_values(["sum_score_adjusted", "finding_count", "metric"], ascending=[False, False, True], kind="mergesort").reset_index(drop=True)


def build_findings_summary_by_period(unified_findings: pd.DataFrame) -> pd.DataFrame:
    if unified_findings.empty:
        return pd.DataFrame(columns=list(FINDINGS_SUMMARY_BY_PERIOD_COLUMNS))
    df = unified_findings.copy()
    df["score_adjusted"] = pd.to_numeric(df["score_adjusted"], errors="coerce").fillna(0.0)
    df["score_penalty"] = pd.to_numeric(df["score_penalty"], errors="coerce").fillna(0.0)
    out = (
        df.groupby("period", sort=True)
        .agg(
            finding_count=("finding_id", "count"),
            high_severity_count=("score_adjusted", lambda s: int((s >= _HIGH_SEVERITY_THRESHOLD).sum())),
            avg_score_adjusted=("score_adjusted", "mean"),
            sum_score_adjusted=("score_adjusted", "sum"),
            sum_score_penalty=("score_penalty", "sum"),
            top_finding_category=("finding_type", _top_category),
        )
        .reset_index()
        .reindex(columns=list(FINDINGS_SUMMARY_BY_PERIOD_COLUMNS))
    )
    return out.sort_values(["sum_score_adjusted", "finding_count", "period"], ascending=[False, False, True], kind="mergesort").reset_index(drop=True)


def _metric_to_deterioration_axis(metric: str) -> str:
    m = str(metric).lower()
    if "margin" in m:
        return "margins"
    if "revenue" in m or "growth" in m or m.endswith("_qoq") or m.endswith("_yoy"):
        return "revenue_growth"
    if "cash" in m or "fcf" in m or "ocf" in m or "operating_cash" in m:
        return "cash_flow"
    if "debt" in m or "leverage" in m or "liabilities" in m:
        return "leverage"
    if "current_ratio" in m or "liquidity" in m:
        return "liquidity"
    return "other"


def _row_in_deterioration_focus(r: pd.Series) -> bool:
    """Keep stress-oriented rows; drop obvious strength / growth spikes."""
    src = str(r.get("finding_source", ""))
    d = str(r.get("direction", "")).lower()
    if src == "anomaly" and d == "high":
        return False
    if src == "trend_break" and d == "improving":
        return False
    if d in ("deteriorating", "low"):
        return True
    if src == "trend_break":
        return d in ("deteriorating", "mixed", "none", "")
    if src == "anomaly":
        return d not in ("high",)
    return False


def _deterioration_kind(r: pd.Series, *, deteriorating_period_count: int) -> str:
    src = str(r.get("finding_source", ""))
    d = str(r.get("direction", "")).lower()
    if deteriorating_period_count >= 2 and d == "deteriorating":
        return "repeated_deterioration"
    if src == "trend_break":
        return "trend_break_stress"
    if src == "anomaly":
        return "negative_point_anomaly"
    return "other_stress"


def build_deterioration_focus(unified_findings: pd.DataFrame) -> pd.DataFrame:
    """
    Deterioration-prioritized slice of :func:`build_unified_findings`.

    - Reuses unified columns; adds axis, multi-period counts, kind, and a rank.
    - Suppresses one-off positive anomalies (direction ``high``) and improving trends.
    - Up-ranks repeated ``deteriorating`` directions and trend-break stress; down-ranks
      isolated anomalies when there is no multi-period corroboration.
    """
    if unified_findings.empty:
        return pd.DataFrame(columns=list(DETERIORATION_FOCUS_COLUMNS))

    uf = unified_findings.reindex(columns=list(UNIFIED_FINDINGS_COLUMNS)).copy()
    for c in ("cik", "period", "metric", "finding_source", "direction"):
        if c not in uf.columns:
            uf[c] = ""
    uf["score_adjusted"] = pd.to_numeric(uf["score_adjusted"], errors="coerce").fillna(0.0)
    uf["overlap_count"] = pd.to_numeric(uf["overlap_count"], errors="coerce").fillna(1).astype(int)

    mask = uf.apply(_row_in_deterioration_focus, axis=1)
    df = uf.loc[mask].copy()
    if df.empty:
        return pd.DataFrame(columns=list(DETERIORATION_FOCUS_COLUMNS))

    _det = (
        uf[uf["direction"].astype(str).str.lower() == "deteriorating"]
        .groupby(["cik", "metric"], sort=False)["period"]
        .nunique()
        .reset_index(name="deteriorating_period_count")
    )
    df = df.merge(_det, on=["cik", "metric"], how="left")
    df["deteriorating_period_count"] = df["deteriorating_period_count"].fillna(0).astype(int)

    df["stress_period_count"] = df.groupby(["cik", "metric"], sort=False)["period"].transform("nunique")
    df["stress_period_count"] = df["stress_period_count"].astype(int)

    df["deterioration_axis"] = df["metric"].map(_metric_to_deterioration_axis)
    df["multi_period_stress"] = (df["deteriorating_period_count"] >= 2) | (df["stress_period_count"] >= 2)

    df["deterioration_kind"] = df.apply(
        lambda r: _deterioration_kind(
            r,
            deteriorating_period_count=int(r["deteriorating_period_count"]),
        ),
        axis=1,
    )
    df["one_off_anomaly_only"] = (
        (df["finding_source"].astype(str) == "anomaly")
        & (df["stress_period_count"] <= 1)
        & (df["deteriorating_period_count"] <= 1)
    )

    adj = df["score_adjusted"].astype(float)
    occ = df["overlap_count"].clip(lower=1)
    bonus_det = (df["deteriorating_period_count"].clip(lower=0) - 1).clip(lower=0).astype(float)
    bonus_stress = (df["stress_period_count"].clip(lower=0) - 1).clip(lower=0).astype(float)
    tb_bonus = (df["finding_source"].astype(str) == "trend_break").astype(float) * 0.25
    overlap_bonus = (occ - 1).clip(lower=0, upper=2).astype(float) * 0.12
    one_off_penalty = df["one_off_anomaly_only"].astype(float) * 0.4

    df["deterioration_priority_score"] = (
        adj
        + 0.45 * bonus_det.clip(upper=4)
        + 0.22 * bonus_stress.clip(upper=4)
        + tb_bonus
        + overlap_bonus
        - one_off_penalty
    )

    df = df.sort_values(
        ["multi_period_stress", "deterioration_priority_score", "score_adjusted", "cik", "period", "metric"],
        ascending=[False, False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    df["deterioration_priority_rank"] = range(1, len(df) + 1)
    return df.reindex(columns=list(DETERIORATION_FOCUS_COLUMNS))
