"""Exclusion summaries and stable reason_code values (no live SEC)."""

from __future__ import annotations

import pandas as pd

from src.exclusions import (
    DUPLICATE_RESOLVED,
    MISSING_REQUIRED_METRIC,
    NON_NUMERIC_COERCION,
    SEGMENTED_CONTEXT_EXCLUDED,
    UNSUPPORTED_UNIT,
    build_exclusions_dataframe,
)
from src.metric_extraction import extract_metrics
from src.normalization import METRIC_COLUMNS, build_panel, wide_panel_before_revenue_filter


def _minimal_us_gaap(tag: str, units: dict) -> dict:
    return {"facts": {"us-gaap": {tag: {"units": units}}}}


def test_unsupported_unit_counted() -> None:
    facts = _minimal_us_gaap(
        "Revenues",
        {
            "EUR": [
                {"form": "10-K", "fp": "Q1", "fy": 2023, "val": 1.0, "filed": "2023-03-01"},
            ]
        },
    )
    counts: dict[str, int] = {}
    df = extract_metrics(facts, cik=1, years=5, exclusion_counts=counts)
    assert df.empty
    assert counts.get(UNSUPPORTED_UNIT, 0) >= 1


def test_duplicate_tag_resolution_counted() -> None:
    """Two revenue tags for the same (fy, fp): one row kept, one duplicate_resolved."""
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "fp": "Q1",
                                "fy": 2023,
                                "val": 100.0,
                                "filed": "2023-03-15",
                            },
                        ]
                    }
                },
                "SalesRevenueNet": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "fp": "Q1",
                                "fy": 2023,
                                "val": 99.0,
                                "filed": "2022-03-01",
                            },
                        ]
                    }
                },
            }
        }
    }
    counts: dict[str, int] = {}
    df = extract_metrics(facts, cik=1, years=5, exclusion_counts=counts)
    assert len(df) == 1
    assert counts.get(DUPLICATE_RESOLVED, 0) >= 1


def test_missing_revenue_bump_matches_row_drop() -> None:
    long_frames = [
        pd.DataFrame(
            [
                {"cik": 1, "period": "2023-Q1", "metric": "revenue", "value": 100.0},
                {"cik": 1, "period": "2023-Q1", "metric": "net_income", "value": 10.0},
                {"cik": 2, "period": "2023-Q1", "metric": "net_income", "value": 5.0},
            ]
        )
    ]
    pre = wide_panel_before_revenue_filter(long_frames)
    counts: dict[str, int] = {}
    post = build_panel(long_frames, exclusion_counts=counts)
    assert len(pre) - len(post) == counts.get(MISSING_REQUIRED_METRIC, 0)


def test_non_numeric_coercion_in_wide() -> None:
    long_frames = [
        pd.DataFrame(
            [
                {"cik": 1, "period": "2023-Q1", "metric": "revenue", "value": 1.0},
                {"cik": 1, "period": "2023-Q1", "metric": "net_income", "value": "not-a-number"},
            ]
        )
    ]
    counts: dict[str, int] = {}
    wide_panel_before_revenue_filter(long_frames, exclusion_counts=counts)
    assert counts.get(NON_NUMERIC_COERCION, 0) >= 1


def test_exclusions_partitioned_by_pipeline_stage() -> None:
    """Rows are tagged ``metric_extraction`` vs ``normalization`` for downstream classification."""
    df = build_exclusions_dataframe({"unsupported_unit": 1, "duplicate_resolved": 1}, {MISSING_REQUIRED_METRIC: 2})
    assert not df.empty
    assert set(df["stage"]) == {"metric_extraction", "normalization"}
    assert (df["stage"] == "metric_extraction").sum() == 2
    assert (df["stage"] == "normalization").sum() == 1


def test_exclusions_summary_columns_stable() -> None:
    df = build_exclusions_dataframe({"unsupported_unit": 2}, {MISSING_REQUIRED_METRIC: 1})
    assert list(df.columns) == [
        "stage",
        "reason_code",
        "count",
        "cik",
        "period",
        "metric",
        "tag",
        "detail",
    ]
    assert set(df["reason_code"]) <= set(
        [
            "unsupported_unit",
            MISSING_REQUIRED_METRIC,
        ]
    )


def test_all_metric_columns_present_after_pivot() -> None:
    """Wide frame includes every METRIC_COLUMNS field (NA-filled) for coercion accounting."""
    long_frames = [
        pd.DataFrame(
            [{"cik": 1, "period": "2023-Q1", "metric": "revenue", "value": 1.0}],
        )
    ]
    wide = wide_panel_before_revenue_filter(long_frames)
    for c in METRIC_COLUMNS:
        assert c in wide.columns


def test_segmented_fact_excluded_from_extraction() -> None:
    """Facts with non-empty ``segments`` are consolidated-line only — skip dimensional rows."""
    facts = _minimal_us_gaap(
        "Revenues",
        {
            "USD": [
                {
                    "form": "10-K",
                    "fp": "Q1",
                    "fy": 2023,
                    "val": 100.0,
                    "filed": "2023-03-15",
                    "segments": [{"explicitMember": "foo"}],
                },
            ]
        },
    )
    counts: dict[str, int] = {}
    df = extract_metrics(facts, cik=1, years=5, exclusion_counts=counts)
    assert df.empty
    assert counts.get(SEGMENTED_CONTEXT_EXCLUDED, 0) >= 1


def test_same_tag_same_filed_prefers_higher_accn() -> None:
    """When tag and ``filed`` tie, later accession string wins (amendment / restatement ordering)."""
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "fp": "Q1",
                                "fy": 2023,
                                "val": 100.0,
                                "filed": "2023-03-15",
                                "accn": "0000320193-23-000010",
                            },
                            {
                                "form": "10-K",
                                "fp": "Q1",
                                "fy": 2023,
                                "val": 200.0,
                                "filed": "2023-03-15",
                                "accn": "0000320193-23-000099",
                            },
                        ]
                    }
                }
            }
        }
    }
    df = extract_metrics(facts, cik=1, years=5)
    assert len(df) == 1
    assert float(df["value"].iloc[0]) == 200.0


def test_wide_pivot_first_follows_concat_order_after_sort() -> None:
    """Duplicate (cik, period, metric): ``aggfunc=first`` uses first row after stable sort (concat order)."""
    long_frames = [
        pd.DataFrame([{"cik": 1, "period": "2020-Q1", "metric": "revenue", "value": 2.0}]),
        pd.DataFrame([{"cik": 1, "period": "2020-Q1", "metric": "revenue", "value": 1.0}]),
    ]
    wide = wide_panel_before_revenue_filter(long_frames)
    assert float(wide["revenue"].iloc[0]) == 2.0
