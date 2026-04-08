"""Anomaly detection: self z, peer LOO z, explanation fields (deterministic)."""

from __future__ import annotations

import numpy as np
import pandas as pd

import config
from src.anomaly import ANOMALY_OUTPUT_COLUMNS, MIN_PEER_GROUP, detect_anomalies


def _panel_features_monotone_growth() -> pd.DataFrame:
    """One CIK, enough quarters that last revenue is an outlier vs trailing window."""
    periods = [f"2020-Q{i}" for i in range(1, 5)] + [f"2021-Q{i}" for i in range(1, 5)]
    n = len(periods)
    rev = np.linspace(100.0, 118.0, n - 1).tolist() + [500.0]
    df = pd.DataFrame(
        {
            "cik": [1] * n,
            "period": periods,
            "revenue": rev,
            "net_income": (np.array(rev) * 0.1).tolist(),
            "total_assets": [1000.0] * n,
            "total_liabilities": [400.0] * n,
            "current_assets": [100.0] * n,
            "current_liabilities": [50.0] * n,
        }
    )
    return df


def test_detect_anomalies_has_explanation_columns() -> None:
    from src.features import compute_features

    panel = _panel_features_monotone_growth()
    feats = compute_features(panel)
    anom = detect_anomalies(feats)
    assert not anom.empty
    for c in ANOMALY_OUTPUT_COLUMNS:
        assert c in anom.columns
    assert anom.iloc[0]["direction"] in ("high", "low")
    assert anom.iloc[0]["window_max_quarters"] == config.ZSCORE_WINDOW
    assert anom.iloc[0]["anomaly_category"] in ("self_relative", "combined")
    assert anom.iloc[0]["comparison_scope"] in ("self_history", "combined")
    assert bool(anom.iloc[0]["self_anomaly"])
    assert "combined_score" in anom.columns
    assert "combined_signal_type" in anom.columns
    assert "contributing_signals" in anom.columns
    assert "score_components" in anom.columns
    assert "combined_explanation" in anom.columns


def test_peer_loo_z_numeric() -> None:
    """Leave-one-out peer z is defined when ≥ MIN_PEER_GROUP firms share a period."""
    from src.anomaly import _peer_loo_z_and_group_size

    df = pd.DataFrame(
        {
            "cik": [1, 2, 3],
            "period": ["2021-Q1", "2021-Q1", "2021-Q1"],
            "revenue": [1.0, 2.0, 100.0],
        }
    )
    pz, pn = _peer_loo_z_and_group_size(df, "revenue")
    assert int(pn.iloc[0]) == MIN_PEER_GROUP
    assert not np.isnan(pz.iloc[2])


def test_peer_relative_only_no_self_history() -> None:
    """Single shared period, three CIKs — no rolling self z; peer layer can still flag."""
    from src.peer_signals import compute_peer_signals

    feats = pd.DataFrame(
        {
            "cik": [1, 2, 3],
            "period": ["2021-Q1", "2021-Q1", "2021-Q1"],
            "revenue": [1.0, 2.0, 100.0],
            "net_income": [0.1, 0.2, 10.0],
            "total_assets": [1000.0, 1000.0, 1000.0],
            "total_liabilities": [400.0, 400.0, 400.0],
            "current_assets": [100.0, 100.0, 100.0],
            "current_liabilities": [50.0, 50.0, 50.0],
        }
    )
    ps = compute_peer_signals(feats)
    anom = detect_anomalies(feats, peer_signals=ps)
    pr = anom[anom["anomaly_category"] == "peer_relative"]
    assert not pr.empty
    assert not pr["self_anomaly"].any()
    assert pr["peer_anomaly"].all()


def test_empty_features_empty_anomalies() -> None:
    empty = pd.DataFrame(columns=["cik", "period", "revenue"])
    out = detect_anomalies(empty)
    assert out.empty
    assert list(out.columns) == list(ANOMALY_OUTPUT_COLUMNS)


def test_combined_category_when_self_z_and_peer_cs_extreme_align() -> None:
    """Same (cik, period, metric): rolling self flag + cross-section peer_alert extreme → combined."""
    periods = [f"2020-Q{i}" for i in range(1, 5)] + [f"2021-Q{i}" for i in range(1, 5)]
    n = len(periods)
    rev_cik1 = np.linspace(100.0, 118.0, n - 1).tolist() + [500.0]
    rows: list[dict] = []
    for cik, series in [(1, rev_cik1), (2, [100.0] * n), (3, [110.0] * n)]:
        for i, p in enumerate(periods):
            r = float(series[i])
            rows.append(
                {
                    "cik": cik,
                    "period": p,
                    "revenue": r,
                    "net_income": r * 0.1,
                    "total_assets": 1000.0,
                    "total_liabilities": 400.0,
                    "current_assets": 100.0,
                    "current_liabilities": 50.0,
                }
            )
    panel = pd.DataFrame(rows)
    from src.features import compute_features
    from src.peer_signals import compute_peer_signals

    feats = compute_features(panel)
    ps = compute_peer_signals(feats)
    anom = detect_anomalies(feats, peer_signals=ps)
    comb = anom[anom["anomaly_category"] == "combined"]
    assert not comb.empty
    r0 = comb.iloc[0]
    assert bool(r0["self_anomaly"]) and bool(r0["peer_anomaly"])
    expl = str(r0["explanation"])
    assert "category=combined" in expl
    assert "self=True" in expl
    assert "peer_cs=True" in expl
    assert str(r0["comparison_scope"]) == "combined"


def test_explanation_includes_caveat_token_when_sparse_history() -> None:
    """Machine-readable explanation carries caveat_codes into the explanation string."""
    from src.features import compute_features

    panel = _panel_features_monotone_growth()
    feats = compute_features(panel)
    anom = detect_anomalies(feats)
    assert not anom.empty
    expl = str(anom.iloc[0]["explanation"])
    assert "caveats=" in expl


def test_combined_score_has_expected_trace_fields() -> None:
    from src.features import compute_features
    from src.peer_signals import compute_peer_signals

    periods = [f"2020-Q{i}" for i in range(1, 5)] + [f"2021-Q{i}" for i in range(1, 5)]
    n = len(periods)
    rev_cik1 = np.linspace(100.0, 118.0, n - 1).tolist() + [500.0]
    rows: list[dict] = []
    for cik, series in [(1, rev_cik1), (2, [100.0] * n), (3, [110.0] * n)]:
        for i, p in enumerate(periods):
            r = float(series[i])
            rows.append(
                {
                    "cik": cik,
                    "period": p,
                    "revenue": r,
                    "net_income": r * 0.1,
                    "total_assets": 1000.0,
                    "total_liabilities": 400.0,
                    "current_assets": 100.0,
                    "current_liabilities": 50.0,
                }
            )
    feats = compute_features(pd.DataFrame(rows))
    ps = compute_peer_signals(feats)
    anom = detect_anomalies(feats, peer_signals=ps)
    assert not anom.empty
    r0 = anom.iloc[0]
    assert float(r0["combined_score"]) >= 0.0
    assert str(r0["combined_signal_type"]) in ("dual_confirmed", "dual_mixed", "self_only", "peer_only")
    assert "score=" in str(r0["combined_explanation"])
    assert "self=" in str(r0["score_components"])


def test_caveat_penalty_reduces_combined_score() -> None:
    from src.features import compute_features

    panel = _panel_features_monotone_growth()
    feats = compute_features(panel)
    anom = detect_anomalies(feats)
    assert not anom.empty
    r0 = anom.iloc[0]
    comps = str(r0["score_components"])
    assert "penalty=" in comps
    parts = dict(part.split("=", 1) for part in comps.split(";") if "=" in part)
    assert float(parts["score"]) <= float(parts["raw"])
    assert float(r0["combined_score_raw"]) >= float(r0["combined_score_adjusted"])
    assert float(r0["combined_score"]) == float(r0["combined_score_adjusted"])


def test_external_trust_caveats_reduce_adjusted_score() -> None:
    from src.features import compute_features
    from src.peer_signals import compute_peer_signals

    periods = [f"2020-Q{i}" for i in range(1, 5)] + [f"2021-Q{i}" for i in range(1, 5)]
    n = len(periods)
    rev_cik1 = np.linspace(100.0, 118.0, n - 1).tolist() + [500.0]
    rows: list[dict] = []
    for cik, series in [(1, rev_cik1), (2, [100.0] * n), (3, [110.0] * n)]:
        for i, p in enumerate(periods):
            r = float(series[i])
            rows.append(
                {
                    "cik": cik,
                    "period": p,
                    "revenue": r,
                    "net_income": r * 0.1,
                    "total_assets": 1000.0,
                    "total_liabilities": 400.0,
                    "current_assets": 100.0,
                    "current_liabilities": 50.0,
                }
            )
    feats = compute_features(pd.DataFrame(rows))
    ps = compute_peer_signals(feats)
    base = detect_anomalies(feats, peer_signals=ps)
    assert not base.empty
    top = base.iloc[0]
    key = {"cik": int(top["cik"]), "period": str(top["period"]), "metric": str(top["metric"])}
    ext = pd.DataFrame([{**key, "source_tag": "Revenues", "n_candidates": 1, "caveat_codes": "fallback_tag_used"}])
    pan = pd.DataFrame([{"cik": key["cik"], "period": key["period"], "caveat_codes": "low_period_count;missing_prior_period"}])
    penalized = detect_anomalies(
        feats,
        peer_signals=ps,
        extraction_caveats=ext,
        panel_caveats=pan,
    )
    row = penalized[
        (penalized["cik"] == key["cik"])
        & (penalized["period"] == key["period"])
        & (penalized["metric"] == key["metric"])
    ].iloc[0]
    assert "fallback_tag_used" in str(row["caveat_codes"])
    assert "low_period_count" in str(row["caveat_codes"])
    assert "missing_prior_period" in str(row["caveat_codes"])
    assert float(row["combined_score_adjusted"]) < float(row["combined_score_raw"])
