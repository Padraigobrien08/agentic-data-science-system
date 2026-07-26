"""Manual validation schema and candidate emission."""

from pathlib import Path

import pandas as pd

from src.manual_validation import (
    VALIDATION_COLUMNS,
    candidate_records_from_panel,
    ensure_validation_csv,
    load_validation_records,
    panel_to_long,
)


def _tiny_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cik": [320193, 320193],
            "period": ["2023-Q1", "2023-Q2"],
            "revenue": [1.0e9, 1.1e9],
            "net_income": [1.0e8, 1.1e8],
            "total_assets": [3.5e11, 3.5e11],
            "total_liabilities": [2.0e11, 2.0e11],
            "operating_cash_flow": [2.0e9, 2.1e9],
            "current_assets": [1.0e10, 1.0e10],
            "current_liabilities": [9.0e9, 9.0e9],
        }
    )


def test_candidate_records_match_schema() -> None:
    df = candidate_records_from_panel(_tiny_panel(), metrics=["revenue"])
    assert list(df.columns) == list(VALIDATION_COLUMNS)
    assert len(df) == 2
    assert df["metric"].tolist() == ["revenue", "revenue"]
    assert df["expected_value"].isna().all()


def test_candidate_records_ticker_map() -> None:
    df = candidate_records_from_panel(
        _tiny_panel(),
        metrics=["revenue"],
        ticker_by_cik={320193: "AAPL"},
    )
    assert (df["ticker"] == "AAPL").all()


def test_ensure_validation_csv_creates_header(tmp_path: Path) -> None:
    p = tmp_path / "mv.csv"
    ensure_validation_csv(p)
    assert p.is_file()
    loaded = load_validation_records(p)
    assert list(loaded.columns) == list(VALIDATION_COLUMNS)
    assert len(loaded) == 0


def test_load_records_migrates_missing_expected_value(tmp_path: Path) -> None:
    legacy = "ticker,cik,period,metric,extracted_value,source_reference,checked_by,checked_date,validation_status,notes\n"
    p = tmp_path / "legacy.csv"
    p.write_text(legacy, encoding="utf-8")
    df = load_validation_records(p)
    assert "expected_value" in df.columns
    assert len(df) == 0


def test_panel_to_long_unchanged_shape() -> None:
    long_df = panel_to_long(_tiny_panel(), metrics=["revenue"])
    assert list(long_df.columns) == ["cik", "period", "metric", "extracted_value"]
