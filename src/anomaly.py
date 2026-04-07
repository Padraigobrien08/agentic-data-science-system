"""
Rolling z-score anomaly flags on numeric feature columns.

Self rule (unchanged): per CIK, |self z-score| > threshold vs trailing history (current excluded).

Peer layer: rows from :func:`src.peer_signals.compute_peer_signals` where ``peer_alert`` is
``extreme_high`` / ``extreme_low`` are merged into the same ``anomalies`` table with
``anomaly_category`` in {``self_relative``, ``peer_relative``, ``combined``} — one row per
(cik, period, metric).

Column semantics (read with :data:`ANOMALY_OUTPUT_COLUMNS`):
  * ``zscore`` — self-history z for the focal metric when ``self_anomaly``; else NaN.
  * ``z_score_peer`` — leave-one-out cross-section z (focal excluded from mean/std).
  * ``peer_cs_*`` — cross-section from ``peer_signals`` (mean/std **include** the focal firm); distinct from LOO.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config

FEATURE_COLS = [
    "revenue",
    "net_income",
    "revenue_growth_qoq",
    "net_margin",
    "current_ratio",
    "debt_to_assets",
]

MIN_PEER_GROUP = 3

# Peer layer extremes (from peer_signals.peer_alert).
_PEER_ALERT_EXTREME = frozenset({"extreme_high", "extreme_low"})

# --- anomalies.csv schema ---
# anomaly_category: how this row was flagged (single source or both).
# self_anomaly / peer_anomaly: boolean provenance for each layer.
# z_score_peer + peer_group_n: LOO cross-section (focal excluded from mean/std).
# peer_cs_*: cross-section peer_signals layer (mean/std include focal); see peer_signals module.
ANOMALY_OUTPUT_COLUMNS: tuple[str, ...] = (
    "cik",
    "period",
    "metric",
    "value",
    "anomaly_category",
    "self_anomaly",
    "peer_anomaly",
    "direction",
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
    "peer_cs_rank_signal",
    "peer_cs_z_signal",
    "peer_cs_alert",
    "comparison_scope",
    "caveat_codes",
    "explanation",
    "abs_z",
)


def _rolling_self_z_and_baselines(s: pd.Series, window: int) -> pd.DataFrame:
    r = s.astype(float)
    prev = r.shift(1)
    m = prev.rolling(window=window, min_periods=2).mean()
    sd = prev.rolling(window=window, min_periods=2).std(ddof=0)
    cnt = prev.rolling(window=window, min_periods=2).count()
    z = (r - m) / sd
    z = z.replace([np.inf, -np.inf], np.nan)
    z = z.mask(sd < 1e-15)
    rel_sd = sd / (np.abs(m) + 1e-12)
    z = z.mask(rel_sd < 0.02)
    return pd.DataFrame(
        {
            "self_z": z,
            "self_baseline_mean": m,
            "self_baseline_std": sd,
            "self_baseline_n": cnt,
        },
        index=s.index,
    )


def _peer_loo_z_and_group_size(features: pd.DataFrame, col: str) -> tuple[pd.Series, pd.Series]:
    peer_z = pd.Series(np.nan, index=features.index, dtype=float)
    peer_n = pd.Series(0, index=features.index, dtype=int)

    if col not in features.columns:
        return peer_z, peer_n

    for _period, g in features.groupby("period", sort=False):
        vals = g[col].astype(float)
        idx = g.index.tolist()
        mask = vals.notna()
        v_idx = [i for i, ok in zip(idx, mask) if ok]
        v_vals = vals[mask].to_numpy(dtype=float)
        n = len(v_vals)
        for i in idx:
            peer_n.loc[i] = n
        if n < MIN_PEER_GROUP:
            continue
        for i in range(n):
            others = np.concatenate([v_vals[:i], v_vals[i + 1 :]])
            lo_std = float(np.std(others, ddof=0)) if len(others) else 0.0
            lo_mean = float(np.mean(others)) if len(others) else np.nan
            if lo_std < 1e-15:
                peer_z.loc[v_idx[i]] = np.nan
                continue
            peer_z.loc[v_idx[i]] = (v_vals[i] - lo_mean) / lo_std

    return peer_z, peer_n


def _loo_for_cell(
    features: pd.DataFrame,
    pz_all: pd.Series,
    pn_all: pd.Series,
    cik: int,
    period: object,
) -> tuple[float, int]:
    m = (features["cik"] == cik) & (features["period"] == period)
    ix = features.index[m]
    if len(ix) != 1:
        return np.nan, 0
    i = ix[0]
    pz = float(pz_all.loc[i]) if i in pz_all.index else np.nan
    pgn = int(pn_all.loc[i]) if i in pn_all.index else 0
    return pz, pgn


def _format_num(x: float | np.floating) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "nan"
    ax = abs(float(x))
    if ax >= 1e9 or (ax > 0 and ax < 1e-4):
        return f"{float(x):.4e}"
    return f"{float(x):.6g}"


def _caveat_codes(
    *,
    self_n: float,
    window_max: int,
    peer_group_n: int,
    peer_z: float,
    self_anomaly: bool,
) -> str:
    codes: list[str] = []
    if self_anomaly:
        if self_n < window_max and self_n >= 2:
            codes.append("sparse_history")
        if peer_group_n < MIN_PEER_GROUP:
            codes.append("insufficient_peer_coverage")
        elif np.isnan(peer_z):
            codes.append("peer_zero_variance")
    else:
        codes.append("no_self_timeseries_flag")
    return ";".join(codes) if codes else "none"


def _comparison_scope_label(category: str) -> str:
    if category == "combined":
        return "combined"
    if category == "peer_relative":
        return "peer_cross_section"
    return "self_history"


def _explanation_line(
    *,
    category: str,
    direction: str,
    value: float,
    z_self: float | None,
    mean_h: float,
    std_h: float,
    n_h: float,
    wmax: int,
    peer_z_loo: float,
    peer_n_loo: int,
    thr: float,
    caveats: str,
    peer_cs_alert: str,
    self_anomaly: bool,
    peer_anomaly: bool,
) -> str:
    parts: list[str] = [
        f"category={category}",
        f"self={self_anomaly}",
        f"peer_cs={peer_anomaly}",
        f"dir={direction}",
        f"obs={_format_num(value)}",
    ]
    if self_anomaly and z_self is not None and np.isfinite(z_self):
        parts.append(f"self_z={float(z_self):.4f}")
        parts.append(
            f"baseline_prior_quarters mean={_format_num(mean_h)} std={_format_num(std_h)} n={int(n_h)}/{wmax}"
        )
    else:
        parts.append("self_z=n/a")
    if not np.isnan(peer_z_loo):
        parts.append(f"peer_LOO_z={float(peer_z_loo):.4f} (period_n={int(peer_n_loo)})")
        if abs(float(peer_z_loo)) > thr:
            parts.append("|peer_LOO|>threshold")
    else:
        parts.append("peer_LOO_z=n/a")
    if peer_cs_alert and peer_cs_alert not in ("none", "unavailable", ""):
        parts.append(f"peer_cs_alert={peer_cs_alert}")
    parts.append(f"caveats={caveats}")
    return "; ".join(parts)


def _abs_z_for_sort(
    self_anomaly: bool,
    peer_anomaly: bool,
    z_self: float,
    peer_cs_z: float,
    peer_loo: float,
) -> float:
    vals: list[float] = []
    if self_anomaly and np.isfinite(z_self):
        vals.append(abs(float(z_self)))
    if peer_anomaly and np.isfinite(peer_cs_z):
        vals.append(abs(float(peer_cs_z)))
    if np.isfinite(peer_loo):
        vals.append(abs(float(peer_loo)) * 0.5)
    return float(max(vals)) if vals else 0.0


def _collect_self_anomalies(features: pd.DataFrame) -> pd.DataFrame:
    """Rows where |self z| > threshold (internal building block)."""
    rows: list[dict] = []
    w = config.ZSCORE_WINDOW
    thr = config.ZSCORE_THRESHOLD

    peer_cache: dict[str, tuple[pd.Series, pd.Series]] = {}
    for col in FEATURE_COLS:
        if col in features.columns:
            peer_cache[col] = _peer_loo_z_and_group_size(features, col)

    for cik, g in features.groupby("cik"):
        g = g.sort_values("period")
        for col in FEATURE_COLS:
            if col not in g.columns:
                continue
            stats = _rolling_self_z_and_baselines(g[col], w)
            pz_all, pn_all = peer_cache[col]
            for idx in g.index:
                zi = stats.loc[idx, "self_z"]
                if zi is None or (isinstance(zi, float) and np.isnan(zi)):
                    continue
                if abs(float(zi)) <= thr:
                    continue

                row = g.loc[idx]
                mean_h = stats.loc[idx, "self_baseline_mean"]
                std_h = stats.loc[idx, "self_baseline_std"]
                n_h = stats.loc[idx, "self_baseline_n"]
                pz = float(pz_all.loc[idx]) if idx in pz_all.index else np.nan
                pgn = int(pn_all.loc[idx]) if idx in pn_all.index else 0

                val = float(row[col]) if pd.notna(row[col]) else np.nan
                direction = "high" if float(zi) > 0 else "low"
                peer_avail = not np.isnan(pz)
                peer_strong = peer_avail and abs(float(pz)) > thr

                rows.append(
                    {
                        "cik": int(cik),
                        "period": row["period"],
                        "metric": col,
                        "value": val,
                        "direction": direction,
                        "zscore": float(zi),
                        "self_baseline_mean": float(mean_h) if pd.notna(mean_h) else np.nan,
                        "self_baseline_std": float(std_h) if pd.notna(std_h) else np.nan,
                        "self_baseline_n": int(n_h) if pd.notna(n_h) else 0,
                        "window_max_quarters": w,
                        "z_score_peer": pz if not np.isnan(pz) else np.nan,
                        "peer_group_n": pgn,
                        "peer_deviation_strong": peer_strong,
                    }
                )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _merge_anomaly_layers(
    features: pd.DataFrame,
    self_df: pd.DataFrame,
    peer_full: pd.DataFrame,
) -> pd.DataFrame:
    """Union self-flagged and peer-layer-flagged keys; one row per (cik, period, metric)."""
    thr = config.ZSCORE_THRESHOLD
    w = config.ZSCORE_WINDOW

    peer_cache = {col: _peer_loo_z_and_group_size(features, col) for col in FEATURE_COLS if col in features.columns}

    peer_idx = (
        peer_full.set_index(["cik", "period", "metric"], drop=False)
        if not peer_full.empty
        else None
    )

    keys_self: set[tuple] = set()
    if not self_df.empty:
        keys_self = set(zip(self_df["cik"], self_df["period"], self_df["metric"]))

    peer_flagged = peer_full[peer_full["peer_alert"].isin(_PEER_ALERT_EXTREME)].copy() if not peer_full.empty else pd.DataFrame()
    keys_peer: set[tuple] = set()
    if not peer_flagged.empty:
        keys_peer = set(zip(peer_flagged["cik"], peer_flagged["period"], peer_flagged["metric"]))

    all_keys = keys_self | keys_peer
    if not all_keys:
        return pd.DataFrame(columns=list(ANOMALY_OUTPUT_COLUMNS))

    self_simple = self_df.copy() if not self_df.empty else pd.DataFrame()
    self_lookup = (
        self_simple.set_index(["cik", "period", "metric"], drop=False)
        if not self_simple.empty
        else None
    )

    rows_out: list[dict] = []

    for key in sorted(all_keys, key=lambda k: (k[0], str(k[1]), str(k[2]))):
        cik, period, metric = int(key[0]), key[1], str(key[2])

        srow = None
        if self_lookup is not None and key in self_lookup.index:
            srow = self_lookup.loc[key]
            if isinstance(srow, pd.DataFrame):
                srow = srow.iloc[0]

        prow = None
        if peer_idx is not None and key in peer_idx.index:
            prow = peer_idx.loc[key]
            if isinstance(prow, pd.DataFrame):
                prow = prow.iloc[0]

        self_ok = srow is not None
        peer_extreme = prow is not None and str(prow["peer_alert"]) in _PEER_ALERT_EXTREME

        if self_ok and peer_extreme:
            category = "combined"
        elif self_ok:
            category = "self_relative"
        elif peer_extreme:
            category = "peer_relative"
        else:
            continue

        # LOO for this cell (always from features for provenance)
        pz_loo, pgn_loo = (np.nan, 0)
        if metric in peer_cache:
            pz_all, pn_all = peer_cache[metric]
            pz_loo, pgn_loo = _loo_for_cell(features, pz_all, pn_all, cik, period)

        peer_avail = not np.isnan(pz_loo)
        peer_strong = peer_avail and abs(float(pz_loo)) > thr

        if self_ok:
            val = float(srow["value"])
            z_self = float(srow["zscore"])
            mean_h = float(srow["self_baseline_mean"]) if pd.notna(srow["self_baseline_mean"]) else np.nan
            std_h = float(srow["self_baseline_std"]) if pd.notna(srow["self_baseline_std"]) else np.nan
            n_h = float(srow["self_baseline_n"])
            direction = str(srow["direction"])
        else:
            val = float(prow["value"]) if prow is not None and pd.notna(prow["value"]) else np.nan
            z_self = np.nan
            mean_h = std_h = np.nan
            n_h = 0.0
            direction = "high" if str(prow["peer_alert"]) == "extreme_high" else "low"

        z_score_peer = float(pz_loo) if np.isfinite(pz_loo) else (
            float(srow["z_score_peer"]) if self_ok and pd.notna(srow["z_score_peer"]) else np.nan
        )
        peer_group_n = int(pgn_loo) if pgn_loo > 0 else (int(srow["peer_group_n"]) if self_ok else 0)

        peer_cs_pct = float(prow["peer_pct_rank"]) if prow is not None and pd.notna(prow["peer_pct_rank"]) else np.nan
        peer_cs_z = float(prow["peer_z"]) if prow is not None and pd.notna(prow["peer_z"]) else np.nan
        peer_cs_cov = str(prow["peer_coverage"]) if prow is not None else ""
        peer_cs_rsig = str(prow["peer_rank_signal"]) if prow is not None else ""
        peer_cs_zsig = str(prow["peer_z_signal"]) if prow is not None else ""
        peer_cs_alert = str(prow["peer_alert"]) if prow is not None else "unavailable"

        caveats = _caveat_codes(
            self_n=float(n_h),
            window_max=w,
            peer_group_n=int(peer_group_n),
            peer_z=float(pz_loo),
            self_anomaly=self_ok,
        )
        expl = _explanation_line(
            category=category,
            direction=direction,
            value=val,
            z_self=z_self if self_ok else None,
            mean_h=mean_h,
            std_h=std_h,
            n_h=float(n_h),
            wmax=w,
            peer_z_loo=float(pz_loo),
            peer_n_loo=int(peer_group_n),
            thr=thr,
            caveats=caveats,
            peer_cs_alert=peer_cs_alert,
            self_anomaly=self_ok,
            peer_anomaly=peer_extreme,
        )
        abs_z = _abs_z_for_sort(self_ok, peer_extreme, z_self if self_ok else np.nan, peer_cs_z, float(pz_loo))

        rows_out.append(
            {
                "cik": cik,
                "period": period,
                "metric": metric,
                "value": val,
                "anomaly_category": category,
                "self_anomaly": self_ok,
                "peer_anomaly": peer_extreme,
                "direction": direction,
                "zscore": z_self if self_ok else np.nan,
                "self_baseline_mean": mean_h if self_ok else np.nan,
                "self_baseline_std": std_h if self_ok else np.nan,
                "self_baseline_n": int(n_h) if self_ok else 0,
                "window_max_quarters": w,
                "z_score_peer": z_score_peer if np.isfinite(z_score_peer) else np.nan,
                "peer_group_n": int(peer_group_n),
                "peer_deviation_strong": peer_strong,
                "peer_cs_pct_rank": peer_cs_pct if prow is not None else np.nan,
                "peer_cs_z": peer_cs_z if prow is not None else np.nan,
                "peer_cs_coverage": peer_cs_cov if prow is not None else "unavailable",
                "peer_cs_rank_signal": peer_cs_rsig if prow is not None else "unavailable",
                "peer_cs_z_signal": peer_cs_zsig if prow is not None else "unavailable",
                "peer_cs_alert": peer_cs_alert if prow is not None else "unavailable",
                "comparison_scope": _comparison_scope_label(category),
                "caveat_codes": caveats,
                "explanation": expl,
                "abs_z": abs_z,
            }
        )

    out = pd.DataFrame(rows_out)
    out = out.sort_values("abs_z", ascending=False).reset_index(drop=True)
    return out.reindex(columns=list(ANOMALY_OUTPUT_COLUMNS))


def detect_anomalies(
    features: pd.DataFrame,
    *,
    peer_signals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Self-relative anomalies merged with peer-layer extremes from ``peer_signals``.

    Pass ``peer_signals`` from the pipeline to avoid recomputing; if omitted, it is computed here.
    """
    from src.peer_signals import compute_peer_signals

    self_df = _collect_self_anomalies(features)
    peer_full = peer_signals if peer_signals is not None else compute_peer_signals(features)

    if self_df.empty and (peer_full.empty or peer_full["peer_alert"].isin(_PEER_ALERT_EXTREME).sum() == 0):
        return pd.DataFrame(columns=list(ANOMALY_OUTPUT_COLUMNS))

    return _merge_anomaly_layers(features, self_df, peer_full)
