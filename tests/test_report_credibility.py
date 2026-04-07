"""Report markdown: credibility sections when analytical artifacts are present (no SEC)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.report import generate_report


def _minimal_features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "revenue": [100.0],
            "net_income": [10.0],
            "total_assets": [1000.0],
            "total_liabilities": [400.0],
            "current_assets": [100.0],
            "current_liabilities": [50.0],
            "revenue_growth_qoq": [0.0],
            "net_margin": [0.1],
            "current_ratio": [2.0],
            "debt_to_assets": [0.4],
        }
    )


def test_report_includes_credibility_blocks_when_inputs_non_empty(tmp_path: Path) -> None:
    dq = pd.DataFrame(
        [
            {
                "category": "stage_count",
                "name": "feature_rows",
                "value": 1,
                "unit": "rows",
                "notes": "",
            },
            {
                "category": "drop_rule",
                "name": "rows_removed_missing_revenue",
                "value": 0,
                "unit": "rows",
                "notes": "test note",
            },
            {
                "category": "missingness_metric",
                "name": "revenue",
                "value": 0.0,
                "unit": "frac_na",
                "notes": "",
            },
        ]
    )
    excl = pd.DataFrame(
        [
            {
                "stage": "normalization",
                "reason_code": "missing_required_metric",
                "count": 2,
                "cik": "",
                "period": "",
                "metric": "",
                "tag": "",
                "detail": "",
            }
        ]
    )
    peer = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "value": [100.0],
            "peer_group_n": [3],
            "peer_coverage": ["full"],
            "peer_pct_rank": [50.0],
            "peer_z": [0.0],
            "peer_rank_signal": ["none"],
            "peer_z_signal": ["none"],
            "peer_alert": ["extreme_high"],
        }
    )
    anomalies = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "anomaly_category": ["peer_relative"],
            "self_anomaly": [False],
            "peer_anomaly": [True],
            "direction": ["high"],
            "value": [100.0],
            "zscore": [float("nan")],
            "explanation": ["category=peer_relative; self=False; ..."],
        }
    )
    mv = tmp_path / "manual_validation.csv"
    mv.write_text("ticker,cik,period,metric,validation_status,checked_date\nX,1,2021-Q1,revenue,ok,2026-01-01\n", encoding="utf-8")

    feats = _minimal_features()
    md = generate_report(
        anomalies,
        feats,
        peer_signals=peer,
        data_quality=dq,
        exclusions=excl,
        manual_validation_path=mv,
        top_n=1,
    )

    assert "# EDGAR Anomaly Report" in md
    assert "## Credibility & coverage" in md
    assert "### Data quality summary" in md
    assert "feature_rows" in md
    assert "rows_removed_missing_revenue" in md
    assert "### Exclusions (pipeline)" in md
    assert "normalization" in md
    assert "### Manual validation status" in md
    assert "### Peer-relative findings summary" in md
    assert "Unified anomaly rows by category" in md
    assert "data_quality_summary.csv" in md
    assert "## Peer-relative detail (cross-section by period)" in md
    assert "## Top 1 anomaly explanations (machine-readable)" in md


def test_report_normalized_panel_section_tolerates_missing_balance_sheet_columns() -> None:
    """Avoid KeyError when features omit panel columns (e.g. partial CSV from MCP)."""
    feats = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "revenue": [100.0],
            "net_income": [10.0],
            "revenue_growth_qoq": [0.0],
            "net_margin": [0.1],
        }
    )
    md = generate_report(pd.DataFrame(), feats, peer_signals=None, data_quality=None, exclusions=None)
    assert "## Normalized quarterly panel (sample)" in md
    assert "100.0" in md or "100" in md


def test_credibility_section_emits_all_drop_rule_rows() -> None:
    dq = pd.DataFrame(
        [
            {
                "category": "drop_rule",
                "name": "rows_removed_missing_revenue",
                "value": 2,
                "unit": "rows",
                "notes": "note-a",
            },
            {
                "category": "drop_rule",
                "name": "hypothetical_second_rule",
                "value": 1,
                "unit": "rows",
                "notes": "note-b",
            },
        ]
    )
    md = generate_report(
        pd.DataFrame(),
        _minimal_features(),
        peer_signals=None,
        data_quality=dq,
        exclusions=None,
    )
    assert "hypothetical_second_rule" in md
    assert "note-b" in md
