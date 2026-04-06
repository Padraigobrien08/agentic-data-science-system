"""
Rolling z-score anomaly flags on numeric feature columns.
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


def _rolling_zscore(s: pd.Series, window: int) -> pd.Series:
    """
    Compare each point to the trailing window *excluding* the current point
    (mean/std of prior `window` values). Matches "is this quarter unusual vs recent history".
    """
    r = s.astype(float)
    prev = r.shift(1)
    m = prev.rolling(window=window, min_periods=2).mean()
    sd = prev.rolling(window=window, min_periods=2).std(ddof=0)
    z = (r - m) / sd
    z = z.replace([np.inf, -np.inf], np.nan)
    # Undefined when the prior window has zero variance (or numerically ~0).
    z = z.mask(sd < 1e-15)
    # Suppress unstable z when the trailing window is almost constant (repeat values / rounding).
    rel_sd = sd / (np.abs(m) + 1e-12)
    z = z.mask(rel_sd < 0.02)
    return z


def detect_anomalies(features: pd.DataFrame) -> pd.DataFrame:
    """
    Per CIK, rolling z-score (window=config.ZSCORE_WINDOW) on selected columns.
    Returns long table of flags where |z| > threshold.
    """
    rows: list[dict] = []
    w = config.ZSCORE_WINDOW
    thr = config.ZSCORE_THRESHOLD

    for cik, g in features.groupby("cik"):
        g = g.sort_values("period")
        for col in FEATURE_COLS:
            if col not in g.columns:
                continue
            z = _rolling_zscore(g[col], w)
            for idx in g.index:
                zi = z.loc[idx]
                if zi is None or (isinstance(zi, float) and np.isnan(zi)):
                    continue
                if abs(float(zi)) > thr:
                    row = g.loc[idx]
                    rows.append(
                        {
                            "cik": int(cik),
                            "period": row["period"],
                            "metric": col,
                            "value": float(row[col]) if pd.notna(row[col]) else np.nan,
                            "zscore": float(zi),
                        }
                    )

    if not rows:
        return pd.DataFrame(
            columns=["cik", "period", "metric", "value", "zscore"]
        )

    out = pd.DataFrame(rows)
    out["abs_z"] = out["zscore"].abs()
    out = out.sort_values("abs_z", ascending=False).reset_index(drop=True)
    return out
