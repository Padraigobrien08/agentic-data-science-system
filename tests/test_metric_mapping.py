"""Canonical metric mapping stays aligned with panel columns and extraction."""

from pathlib import Path

from src.metric_mapping import (
    METRIC_COLUMN_ORDER,
    METRIC_SPECS,
    METRIC_TAGS,
    metric_mapping_csv_rows,
    write_metric_mapping_md,
)
from src.normalization import METRIC_COLUMNS


def test_metric_tags_matches_panel_columns() -> None:
    assert list(METRIC_COLUMN_ORDER) == METRIC_COLUMNS
    assert set(METRIC_TAGS.keys()) == set(METRIC_COLUMNS)


def test_metric_specs_cover_all_tags() -> None:
    for spec in METRIC_SPECS:
        assert METRIC_TAGS[spec.name] == list(spec.tags)


def test_csv_rows_roundtrip_count() -> None:
    rows = metric_mapping_csv_rows()
    assert len(rows) == sum(len(s.tags) for s in METRIC_SPECS)
    for r in rows:
        assert r["taxonomy"] == "us-gaap"
        assert "USD" in r["accepted_units"]


def test_generated_metric_mapping_md_lists_each_canonical_metric(tmp_path: Path) -> None:
    """Docs generation stays aligned with METRIC_SPECS / METRIC_COLUMN_ORDER (single source of truth)."""
    md = tmp_path / "metric_mapping.md"
    write_metric_mapping_md(md)
    text = md.read_text(encoding="utf-8")
    for name in METRIC_COLUMN_ORDER:
        assert f"### `{name}`" in text
    assert "Single source of truth: `src/metric_mapping.py`" in text
