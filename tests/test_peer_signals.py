"""Peer-relative signals: cross-section by period (deterministic)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features import compute_features
from src.peer_signals import (
    PEER_MIN_FOR_Z,
    PEER_SIGNAL_COLUMNS,
    compute_peer_signals,
    summarize_peer_coverage,
)


def test_columns_and_empty_features() -> None:
    out = compute_peer_signals(pd.DataFrame())
    assert list(out.columns) == list(PEER_SIGNAL_COLUMNS)
    assert out.empty


def test_insufficient_peers_single_firm() -> None:
    """One CIK per period → peer_group_n == 1 → insufficient_peers, peer_alert unavailable."""
    panel = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "revenue": [100.0],
            "net_income": [10.0],
            "total_assets": [1000.0],
            "total_liabilities": [400.0],
            "current_assets": [100.0],
            "current_liabilities": [50.0],
        }
    )
    feats = compute_features(panel)
    ps = compute_peer_signals(feats)
    assert not ps.empty
    assert (ps["peer_group_n"] == 1).all()
    assert (ps["peer_coverage"] == "insufficient_peers").all()
    assert (ps["peer_alert"] == "unavailable").all()


def test_three_firms_peer_z_and_rank() -> None:
    """Same period, three revenues → full coverage, finite peer_z for outlier."""
    rows = []
    for cik, rev in [(10, 100.0), (20, 110.0), (30, 500.0)]:
        rows.append(
            {
                "cik": cik,
                "period": "2021-Q1",
                "revenue": rev,
                "net_income": rev * 0.1,
                "total_assets": 1000.0,
                "total_liabilities": 400.0,
                "current_assets": 100.0,
                "current_liabilities": 50.0,
            }
        )
    feats = compute_features(pd.DataFrame(rows))
    ps = compute_peer_signals(feats)
    r30 = ps[(ps["cik"] == 30) & (ps["metric"] == "revenue")]
    assert len(r30) == 1
    assert r30.iloc[0]["peer_coverage"] == "full"
    assert r30.iloc[0]["peer_group_n"] == PEER_MIN_FOR_Z
    assert np.isfinite(r30.iloc[0]["peer_z"])
    assert r30.iloc[0]["peer_alert"] in ("extreme_high", "extreme_low", "none")


def test_two_firms_rank_only_no_peer_z() -> None:
    """n == 2 → rank_only; peer_z unavailable."""
    rows = []
    for cik, rev in [(1, 100.0), (2, 200.0)]:
        rows.append(
            {
                "cik": cik,
                "period": "2021-Q1",
                "revenue": rev,
                "net_income": 10.0,
                "total_assets": 1000.0,
                "total_liabilities": 400.0,
                "current_assets": 100.0,
                "current_liabilities": 50.0,
            }
        )
    feats = compute_features(pd.DataFrame(rows))
    ps = compute_peer_signals(feats)
    sub = ps[ps["metric"] == "revenue"]
    assert (sub["peer_coverage"] == "rank_only").all()
    assert sub["peer_z_signal"].eq("unavailable").all()


def test_summarize_peer_coverage() -> None:
    df = pd.DataFrame({"peer_coverage": ["full", "full", "insufficient_peers"]})
    s = summarize_peer_coverage(df)
    assert len(s) == 2
    assert s["row_count"].sum() == 3
