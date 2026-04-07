"""Manual validation helpers (no SEC network)."""

from __future__ import annotations

import pandas as pd

from src.manual_validation import (
    VALIDATION_COLUMNS,
    companyfacts_url,
    format_candidate_table,
    panel_to_long,
)


def test_validation_columns_stable() -> None:
    assert VALIDATION_COLUMNS == (
        "ticker",
        "cik",
        "period",
        "metric",
        "extracted_value",
        "source_reference",
        "checked_by",
        "checked_date",
        "validation_status",
        "notes",
    )


def test_companyfacts_url_zero_pads_cik() -> None:
    u = companyfacts_url(320193)
    assert "CIK0000320193" in u or "320193" in u.replace("0", "")


def test_panel_to_long_shape() -> None:
    panel = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2023-Q1"],
            "revenue": [100.0],
            "net_income": [10.0],
        }
    )
    long_df = panel_to_long(panel)
    assert len(long_df) == 2
    assert set(long_df["metric"]) == {"revenue", "net_income"}


def test_format_candidate_table_includes_url() -> None:
    long_df = pd.DataFrame(
        {
            "cik": [320193],
            "period": ["2023-Q1"],
            "metric": ["revenue"],
            "extracted_value": [1.0],
        }
    )
    text = format_candidate_table(long_df, max_rows=5)
    assert "320193" in text
    assert "companyfacts" in text
