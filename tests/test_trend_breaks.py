"""Deterministic trend-break signals from engineered features."""

from __future__ import annotations

import pandas as pd

from src.features import compute_features
from src.trend_breaks import TREND_BREAK_COLUMNS, compute_trend_break_signals


def _panel_with_shift() -> pd.DataFrame:
    periods = [f"2020-Q{i}" for i in range(1, 5)] + [f"2021-Q{i}" for i in range(1, 5)]
    # Last periods have stronger revenue growth / margin behavior.
    rev = [100.0, 103.0, 106.0, 109.0, 114.0, 122.0, 133.0, 147.0]
    ni = [8.0, 8.2, 8.5, 8.7, 9.5, 11.2, 13.4, 16.5]
    rows = []
    for i, p in enumerate(periods):
        rows.append(
            {
                "cik": 1,
                "period": p,
                "revenue": rev[i],
                "net_income": ni[i],
                "total_assets": 1000.0,
                "total_liabilities": 450.0,
                "current_assets": 120.0,
                "current_liabilities": 60.0,
            }
        )
    return pd.DataFrame(rows)


def test_trend_break_columns_and_signal_types() -> None:
    feats = compute_features(_panel_with_shift())
    out = compute_trend_break_signals(feats)
    for c in TREND_BREAK_COLUMNS:
        assert c in out.columns
    assert out["trend_signal_type"].isin({"short_history", "watch", "moderate_shift", "strong_shift"}).all()


def test_short_history_rows_explicitly_emitted() -> None:
    panel = _panel_with_shift().head(3)
    feats = compute_features(panel)
    out = compute_trend_break_signals(feats)
    assert not out.empty
    assert (out["short_history_flag"] == True).any()  # noqa: E712
    sh = out[out["short_history_flag"] == True].iloc[0]  # noqa: E712
    assert sh["trend_signal_type"] == "short_history"
    assert float(sh["trend_score"]) == 0.0


def test_trend_break_explanation_has_window_and_shift_trace() -> None:
    feats = compute_features(_panel_with_shift())
    out = compute_trend_break_signals(feats)
    row = out.iloc[0]
    expl = str(row["explanation"])
    assert "prior_window=" in expl
    assert "recent_window=" in expl
    assert "mean_shift=" in expl
    assert "slope_shift=" in expl


def test_trend_break_detection_is_deterministic_for_same_inputs() -> None:
    feats = compute_features(_panel_with_shift())
    t1 = compute_trend_break_signals(feats)
    t2 = compute_trend_break_signals(feats)
    cols = [
        "cik",
        "period",
        "metric",
        "trend_score",
        "trend_signal_type",
        "mean_shift",
        "slope_shift",
        "consecutive_direction",
        "short_history_flag",
        "explanation",
    ]
    pd.testing.assert_frame_equal(t1[cols].reset_index(drop=True), t2[cols].reset_index(drop=True))
