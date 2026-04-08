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
                    "caveat_codes": "none",
                    "explanation_summary": expl,
                    "provenance_artifacts": "trend_break_signals_csv;features_csv",
                }
            )

    if not rows:
        return pd.DataFrame(columns=list(UNIFIED_FINDINGS_COLUMNS))

    out = pd.DataFrame(rows).reindex(columns=list(UNIFIED_FINDINGS_COLUMNS))
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
