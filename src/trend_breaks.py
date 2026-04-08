"""
Deterministic trend-break / regime-shift signals from engineered features.

This layer is additive and does not replace point-anomaly logic. It uses simple
windowed comparisons plus short streak checks to surface shifts that are
interesting even when a single-point z-score is not extreme.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metric_extraction import sort_period_key

TREND_METRICS: tuple[str, ...] = (
    "revenue_growth_qoq",
    "net_margin",
    "current_ratio",
    "debt_to_assets",
)

TREND_BREAK_COLUMNS: tuple[str, ...] = (
    "cik",
    "period",
    "metric",
    "value",
    "history_points",
    "window_prior",
    "window_recent",
    "prior_mean",
    "recent_mean",
    "mean_shift",
    "prior_slope",
    "recent_slope",
    "slope_shift",
    "consecutive_direction",
    "consecutive_len",
    "short_history_flag",
    "trend_score",
    "trend_signal_type",
    "explanation",
)


def _linear_slope(values: list[float]) -> float:
    if len(values) < 2:
        return np.nan
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    if np.isnan(y).any():
        return np.nan
    # Simple OLS slope on index axis; deterministic and lightweight.
    return float(np.polyfit(x, y, 1)[0])


def _streak_direction(recent_values: list[float]) -> tuple[str, int]:
    if len(recent_values) < 3:
        return "none", 0
    arr = np.array(recent_values, dtype=float)
    if np.isnan(arr).any():
        return "none", 0
    diffs = np.diff(arr)
    if len(diffs) == 0:
        return "none", 0
    if np.all(diffs > 0):
        return "improving", len(diffs)
    if np.all(diffs < 0):
        return "deteriorating", len(diffs)
    return "mixed", len(diffs)


def _signal_type(score: float, short_history: bool) -> str:
    if short_history:
        return "short_history"
    if score >= 2.0:
        return "strong_shift"
    if score >= 1.0:
        return "moderate_shift"
    return "watch"


def compute_trend_break_signals(
    features: pd.DataFrame,
    *,
    prior_window: int = 3,
    recent_window: int = 2,
) -> pd.DataFrame:
    """
    Windowed trend-break signals per ``(cik, period, metric)``.

    For each metric/CIK and period with enough trailing points:
      - Compare recent mean (last ``recent_window``) vs prior mean (previous ``prior_window``)
      - Compare recent slope vs prior slope (simple linear slope over each window)
      - Detect consecutive up/down behavior in the recent window+1 points
    """
    cols = list(TREND_BREAK_COLUMNS)
    if features.empty or "cik" not in features.columns or "period" not in features.columns:
        return pd.DataFrame(columns=cols)

    rows: list[dict[str, object]] = []
    need = prior_window + recent_window

    for metric in TREND_METRICS:
        if metric not in features.columns:
            continue
        for cik, g in features.groupby("cik", sort=True):
            gg = g.copy()
            gg["_pk"] = sort_period_key(gg["period"].astype(str))
            gg = gg.sort_values("_pk").drop(columns="_pk").reset_index(drop=True)

            for i in range(len(gg)):
                hist = gg.loc[:i, ["period", metric]].dropna()
                hp = int(len(hist))
                period = str(gg.loc[i, "period"])
                value = float(gg.loc[i, metric]) if pd.notna(gg.loc[i, metric]) else np.nan

                short = hp < need
                if short:
                    rows.append(
                        {
                            "cik": int(cik),
                            "period": period,
                            "metric": metric,
                            "value": value,
                            "history_points": hp,
                            "window_prior": int(prior_window),
                            "window_recent": int(recent_window),
                            "prior_mean": np.nan,
                            "recent_mean": np.nan,
                            "mean_shift": np.nan,
                            "prior_slope": np.nan,
                            "recent_slope": np.nan,
                            "slope_shift": np.nan,
                            "consecutive_direction": "none",
                            "consecutive_len": 0,
                            "short_history_flag": True,
                            "trend_score": 0.0,
                            "trend_signal_type": "short_history",
                            "explanation": (
                                f"metric={metric}; history_points={hp}; required={need}; "
                                "short_history=True; trend_score=0.000"
                            ),
                        }
                    )
                    continue

                series = hist[metric].astype(float).tolist()
                prior_vals = series[-need:-recent_window]
                recent_vals = series[-recent_window:]
                recent_for_streak = series[-(recent_window + 1) :]

                prior_mean = float(np.mean(prior_vals))
                recent_mean = float(np.mean(recent_vals))
                mean_shift = recent_mean - prior_mean

                prior_slope = _linear_slope(prior_vals)
                recent_slope = _linear_slope(recent_vals) if len(recent_vals) >= 2 else np.nan
                slope_shift = (
                    float(recent_slope - prior_slope)
                    if np.isfinite(recent_slope) and np.isfinite(prior_slope)
                    else np.nan
                )

                prior_std = float(np.std(prior_vals, ddof=0))
                mean_norm = abs(mean_shift) / max(prior_std, 1e-9)
                mean_component = min(mean_norm, 3.0)
                slope_component = (
                    min(abs(slope_shift), 1.5) if np.isfinite(slope_shift) else 0.0
                )
                streak_dir, streak_len = _streak_direction(recent_for_streak)
                streak_component = 0.5 if streak_dir in ("improving", "deteriorating") else 0.0
                score = float(mean_component + slope_component + streak_component)
                sig_type = _signal_type(score, short_history=False)

                rows.append(
                    {
                        "cik": int(cik),
                        "period": period,
                        "metric": metric,
                        "value": value,
                        "history_points": hp,
                        "window_prior": int(prior_window),
                        "window_recent": int(recent_window),
                        "prior_mean": prior_mean,
                        "recent_mean": recent_mean,
                        "mean_shift": mean_shift,
                        "prior_slope": prior_slope,
                        "recent_slope": recent_slope,
                        "slope_shift": slope_shift,
                        "consecutive_direction": streak_dir,
                        "consecutive_len": int(streak_len),
                        "short_history_flag": False,
                        "trend_score": score,
                        "trend_signal_type": sig_type,
                        "explanation": (
                            f"metric={metric}; prior_window={prior_window}; recent_window={recent_window}; "
                            f"mean_shift={mean_shift:.6g}; slope_shift={slope_shift:.6g}; "
                            f"streak={streak_dir}:{streak_len}; score={score:.3f}; type={sig_type}"
                        ),
                    }
                )

    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows).reindex(columns=cols)
    return out.sort_values(["trend_score", "cik", "period", "metric"], ascending=[False, True, True, True]).reset_index(drop=True)
