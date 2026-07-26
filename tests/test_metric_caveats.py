"""Panel and extraction caveat helpers."""

from pathlib import Path

import pandas as pd

import config
from edgar_project.run_workspace import build_run_workspace
from src.anomaly import MIN_PEER_GROUP
from src.metric_caveats import (
    compute_panel_metric_caveats,
    filter_extraction_caveats_to_panel,
    prior_fiscal_period,
    write_metric_caveats_artifacts,
)


def _wide_row(cik: int, period: str) -> dict:
    """Minimal wide-panel row with all pipeline metric columns."""
    return {
        "cik": cik,
        "period": period,
        "revenue": 1.0,
        "net_income": 0.1,
        "total_assets": 10.0,
        "total_liabilities": 5.0,
        "operating_cash_flow": 0.5,
        "current_assets": 2.0,
        "current_liabilities": 1.0,
    }


def test_prior_fiscal_period() -> None:
    assert prior_fiscal_period("2020-Q2") == "2020-Q1"
    assert prior_fiscal_period("2020-Q1") == "2019-Q4"


def test_panel_caveats_limited_peer_and_sparse() -> None:
    """Three CIKs in one period → no limited_peer; first period → sparse_history."""
    panel = pd.DataFrame(
        {
            "cik": [1, 2, 3],
            "period": ["2021-Q1", "2021-Q1", "2021-Q1"],
            "revenue": [1.0, 2.0, 3.0],
            "net_income": [0.1, 0.2, 0.3],
            "total_assets": [10.0, 20.0, 30.0],
            "total_liabilities": [5.0, 5.0, 5.0],
            "operating_cash_flow": [1.0, 1.0, 1.0],
            "current_assets": [2.0, 2.0, 2.0],
            "current_liabilities": [1.0, 1.0, 1.0],
        }
    )
    pc = compute_panel_metric_caveats(panel)
    assert not pc.empty
    r = pc.iloc[0]
    assert "sparse_history" in r["caveat_codes"]
    assert "limited_peer_coverage" not in r["caveat_codes"]
    assert "low_period_count" in r["caveat_codes"]


def test_filter_extraction_caveats() -> None:
    ext = pd.DataFrame(
        {
            "cik": [1, 1],
            "period": ["2020-Q1", "2020-Q2"],
            "metric": ["revenue", "revenue"],
            "source_tag": ["Revenues", "Revenues"],
            "n_candidates": [1, 1],
            "caveat_codes": ["", ""],
        }
    )
    panel = pd.DataFrame({"cik": [1], "period": ["2020-Q1"], "revenue": [1.0]})
    f = filter_extraction_caveats_to_panel(ext, panel)
    assert len(f) == 1
    assert f.iloc[0]["period"] == "2020-Q1"


def test_low_period_count_threshold() -> None:
    """Exactly CAVEAT_MIN_PERIODS_PER_CIK rows → no low_period_count."""
    n = config.CAVEAT_MIN_PERIODS_PER_CIK
    rows = []
    for i in range(n):
        rows.append(
            {
                "cik": 9,
                "period": f"202{i}-Q1",
                "revenue": 1.0,
                "net_income": 0.1,
                "total_assets": 1.0,
                "total_liabilities": 0.5,
                "operating_cash_flow": 0.1,
                "current_assets": 0.2,
                "current_liabilities": 0.1,
            }
        )
    panel = pd.DataFrame(rows)
    pc = compute_panel_metric_caveats(panel)
    assert "low_period_count" not in pc["caveat_codes"].iloc[0]


def test_missing_prior_period_when_quarter_gap() -> None:
    """``2020-Q2`` without ``2020-Q1`` for the same CIK emits ``missing_prior_period``."""
    panel = pd.DataFrame(
        [
            _wide_row(1, "2019-Q4"),
            _wide_row(1, "2020-Q2"),
        ]
    )
    pc = compute_panel_metric_caveats(panel)
    row = pc[(pc["cik"] == 1) & (pc["period"] == "2020-Q2")].iloc[0]
    assert "missing_prior_period" in row["caveat_codes"]


def test_panel_caveats_period_order_is_fiscal_not_lexical() -> None:
    """Rows are sorted by fiscal quarter order (not string sort of ``period``)."""
    panel = pd.DataFrame(
        [
            _wide_row(1, "2021-Q1"),
            _wide_row(1, "2020-Q4"),
        ]
    )
    pc = compute_panel_metric_caveats(panel)
    sub = pc[pc["cik"] == 1]["period"].tolist()
    assert sub == ["2020-Q4", "2021-Q1"]


def test_write_metric_caveats_artifacts_matches_in_memory_panel_table(tmp_path: Path) -> None:
    """Written ``metric_caveats_panel.csv`` matches :func:`compute_panel_metric_caveats`."""
    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-caveats",
        manual_validation_csv=tmp_path / "validation" / "manual_validation.csv",
    ).ensure_directories()
    panel = pd.DataFrame([_wide_row(1, "2021-Q1"), _wide_row(2, "2021-Q1"), _wide_row(3, "2021-Q1")])
    paths = write_metric_caveats_artifacts(panel, None, workspace=workspace)
    on_disk = pd.read_csv(paths["metric_caveats_panel"])
    direct = compute_panel_metric_caveats(panel)
    pd.testing.assert_frame_equal(
        on_disk.reset_index(drop=True),
        direct.reset_index(drop=True),
        check_dtype=False,
    )


def test_limited_peer_coverage_when_small_cross_section() -> None:
    if MIN_PEER_GROUP <= 2:
        return
    panel = pd.DataFrame(
        {
            "cik": [1, 2],
            "period": ["2022-Q1", "2022-Q1"],
            "revenue": [1.0, 2.0],
            "net_income": [0.1, 0.2],
            "total_assets": [1.0, 2.0],
            "total_liabilities": [0.5, 1.0],
            "operating_cash_flow": [0.1, 0.2],
            "current_assets": [0.2, 0.4],
            "current_liabilities": [0.1, 0.2],
        }
    )
    pc = compute_panel_metric_caveats(panel)
    assert pc["caveat_codes"].str.contains("limited_peer_coverage").any()
