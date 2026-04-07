"""Data-quality summary (deterministic, no SEC)."""

from __future__ import annotations

import pandas as pd

from src.data_quality import compute_data_quality_summary, format_data_quality_markdown
from src.normalization import METRIC_COLUMNS, build_panel, wide_panel_before_revenue_filter


def test_wide_before_revenue_includes_rows_dropped_by_build_panel() -> None:
    long_frames = [
        pd.DataFrame(
            [
                {"cik": 1, "period": "2023-Q1", "metric": "revenue", "value": 100.0},
                {"cik": 1, "period": "2023-Q1", "metric": "net_income", "value": 10.0},
                # Row with no revenue — should be dropped by build_panel
                {"cik": 2, "period": "2023-Q1", "metric": "net_income", "value": 5.0},
            ]
        )
    ]
    pre = wide_panel_before_revenue_filter(long_frames)
    post = build_panel(long_frames)
    assert len(pre) >= len(post)
    dq = compute_data_quality_summary(long_frames, post, post, pd.DataFrame())
    drops = dq[dq["category"] == "drop_rule"]
    assert not drops.empty
    assert int(drops[drops["name"] == "rows_removed_missing_revenue"]["value"].iloc[0]) == len(pre) - len(post)


def test_missingness_by_metric_present() -> None:
    long_frames = [
        pd.DataFrame(
            [
                {"cik": 1, "period": "2023-Q1", "metric": m, "value": 1.0}
                for m in METRIC_COLUMNS
            ]
        )
    ]
    panel = build_panel(long_frames)
    dq = compute_data_quality_summary(long_frames, panel, panel, pd.DataFrame())
    mm = dq[dq["category"] == "missingness_metric"]
    assert not mm.empty
    for m in METRIC_COLUMNS:
        if m in panel.columns:
            assert m in set(mm["name"])


def test_markdown_section_non_empty() -> None:
    dq = pd.DataFrame(
        [
            {
                "category": "stage_count",
                "name": "panel_rows_after_revenue_required",
                "value": 1,
                "unit": "rows",
                "notes": "",
            }
        ]
    )
    md = format_data_quality_markdown(dq)
    assert "Data quality summary" in md
    assert "data_quality_summary.csv" in md
