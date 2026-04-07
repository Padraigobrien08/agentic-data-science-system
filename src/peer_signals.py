"""
Peer-relative signals: cross-sectional rank and z-score within each fiscal period.

This layer is **additive**: it does not change time-series anomaly detection in ``src.anomaly``.
Uses the same ``features`` table (post-:func:`src.features.compute_features`).

Cross-sectional ``peer_z`` uses the **full** peer set in the period (mean/std include the focal firm).
For leave-one-out peer z on anomalies, see ``z_score_peer`` in ``anomalies.csv``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Initial metric set (subset of engineered features / panel levels).
PEER_SIGNAL_METRICS: tuple[str, ...] = (
    "revenue",
    "net_margin",
    "current_ratio",
    "debt_to_assets",
)

# Minimum distinct firms with non-null values in (period, metric) for:
PEER_MIN_FOR_RANK = 2  # percentile rank (ties averaged)
PEER_MIN_FOR_Z = 3  # cross-sectional z (needs variance)

# Rank-based extremes (percent of peer distribution, 0–100 scale).
PEER_PCT_HIGH = 90.0  # top decile
PEER_PCT_LOW = 10.0  # bottom decile

# |peer_z| threshold for z-based extremes (same scale as typical z flags).
PEER_Z_ALERT_THRESHOLD = 2.0

# Output column order for ``peer_signals.csv``.
PEER_SIGNAL_COLUMNS: tuple[str, ...] = (
    "cik",
    "period",
    "metric",
    "value",
    "peer_group_n",
    "peer_coverage",
    "peer_pct_rank",
    "peer_z",
    "peer_rank_signal",
    "peer_z_signal",
    "peer_alert",
)


def _rank_signal(pr: float, coverage: str) -> str:
    if coverage == "insufficient_peers":
        return "unavailable"
    if not np.isfinite(pr):
        return "unavailable"
    if pr >= PEER_PCT_HIGH:
        return "high"
    if pr <= PEER_PCT_LOW:
        return "low"
    return "none"


def _z_signal(z: float, coverage: str) -> str:
    if coverage in ("insufficient_peers", "rank_only") or not np.isfinite(z):
        return "unavailable"
    if z > PEER_Z_ALERT_THRESHOLD:
        return "high"
    if z < -PEER_Z_ALERT_THRESHOLD:
        return "low"
    return "none"


def _peer_alert(
    rank_sig: str,
    z_sig: str,
    z: float,
    coverage: str,
) -> str:
    """Deterministic OR of rank and z extremes; unavailable only when n < 2."""
    if coverage == "insufficient_peers":
        return "unavailable"
    rh = rank_sig == "high" or z_sig == "high"
    rl = rank_sig == "low" or z_sig == "low"
    if rh and not rl:
        return "extreme_high"
    if rl and not rh:
        return "extreme_low"
    if rh and rl:
        # Rare disagreement: prefer cross-sectional z when defined.
        if coverage == "full" and np.isfinite(z):
            return "extreme_high" if z > 0 else "extreme_low"
        return "none"
    return "none"


def compute_peer_signals(features: pd.DataFrame) -> pd.DataFrame:
    """
    One row per (cik, period, metric) with non-null ``value``, for each metric in
    :data:`PEER_SIGNAL_METRICS` present in ``features``.

    Cross-sectional mean and standard deviation use ``ddof=0`` (population) within each period;
    ranks are percentile with ties averaged (``rank(pct=True, method="average")``).
    """
    rows: list[dict] = []
    if features.empty or "cik" not in features.columns or "period" not in features.columns:
        return pd.DataFrame(columns=list(PEER_SIGNAL_COLUMNS))

    for metric in PEER_SIGNAL_METRICS:
        if metric not in features.columns:
            continue
        base = features[["cik", "period", metric]].copy()
        base = base.dropna(subset=[metric])
        if base.empty:
            continue
        g = base.groupby("period", sort=False)[metric]
        base["peer_group_n"] = g.transform("count")
        base["peer_pct_rank"] = g.transform(lambda s: s.rank(pct=True, method="average") * 100.0)
        mu = g.transform("mean")
        sigma = g.transform(lambda s: s.std(ddof=0))
        base["peer_z"] = (base[metric].astype(float) - mu) / sigma.replace(0, np.nan)
        base.loc[sigma < 1e-15, "peer_z"] = np.nan

        def _coverage(n: int) -> str:
            if n < PEER_MIN_FOR_RANK:
                return "insufficient_peers"
            if n < PEER_MIN_FOR_Z:
                return "rank_only"
            return "full"

        base["peer_coverage"] = base["peer_group_n"].map(_coverage)
        # n==1: rank is degenerate; treat as insufficient for interpretation.
        base.loc[base["peer_group_n"] < PEER_MIN_FOR_RANK, "peer_pct_rank"] = np.nan
        base.loc[base["peer_group_n"] < PEER_MIN_FOR_Z, "peer_z"] = np.nan

        for _, row in base.iterrows():
            cov = str(row["peer_coverage"])
            pr = float(row["peer_pct_rank"]) if pd.notna(row["peer_pct_rank"]) else np.nan
            z = float(row["peer_z"]) if pd.notna(row["peer_z"]) else np.nan
            rs = _rank_signal(pr, cov)
            zs = _z_signal(z, cov)
            pa = _peer_alert(rs, zs, z, cov)
            rows.append(
                {
                    "cik": int(row["cik"]),
                    "period": row["period"],
                    "metric": metric,
                    "value": float(row[metric]),
                    "peer_group_n": int(row["peer_group_n"]),
                    "peer_coverage": cov,
                    "peer_pct_rank": pr if np.isfinite(pr) else np.nan,
                    "peer_z": z if np.isfinite(z) else np.nan,
                    "peer_rank_signal": rs,
                    "peer_z_signal": zs,
                    "peer_alert": pa,
                }
            )

    if not rows:
        return pd.DataFrame(columns=list(PEER_SIGNAL_COLUMNS))

    out = pd.DataFrame(rows)
    return out.reindex(columns=list(PEER_SIGNAL_COLUMNS)).sort_values(
        ["period", "metric", "cik"], kind="mergesort"
    ).reset_index(drop=True)


def summarize_peer_coverage(peer_signals: pd.DataFrame) -> pd.DataFrame:
    """Small table: counts of rows by ``peer_coverage`` (for report / DQ-style use)."""
    if peer_signals.empty or "peer_coverage" not in peer_signals.columns:
        return pd.DataFrame(columns=["peer_coverage", "row_count"])
    s = peer_signals.groupby("peer_coverage").size().reset_index(name="row_count")
    return s.sort_values("peer_coverage")
