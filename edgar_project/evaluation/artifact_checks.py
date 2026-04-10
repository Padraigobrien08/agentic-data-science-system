"""
Lightweight CSV header checks for evaluation benchmarks.

Column lists are sourced from ``src.*`` so they track production schemas without a
parallel contract engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from src.anomaly import ANOMALY_OUTPUT_COLUMNS, FEATURE_COLS
from src.findings import (
    FINDINGS_SUMMARY_BY_COMPANY_COLUMNS,
    FINDINGS_SUMMARY_BY_METRIC_COLUMNS,
    FINDINGS_SUMMARY_BY_PERIOD_COLUMNS,
    UNIFIED_FINDINGS_COLUMNS,
)
from src.manual_validation import VALIDATION_COLUMNS
from src.metric_coverage import SUMMARY_COLUMNS as METRIC_COVERAGE_SUMMARY_COLUMNS
from src.normalization import METRIC_COLUMNS
from src.peer_signals import PEER_SIGNAL_COLUMNS
# Trend-break CSV may be full pipeline output (see ``TREND_BREAK_COLUMNS`` in :mod:`src.trend_breaks`) or a thin fixture.
# Require only columns that must exist for consumers and unified findings.
TREND_BREAK_REQUIRED_COLUMNS_MINIMAL: tuple[str, ...] = (
    "cik",
    "period",
    "metric",
    "trend_signal_type",
    "trend_score",
    "explanation",
)

# Wide panel: identity + normalized metric slots (see :mod:`src.normalization`).
PANEL_REQUIRED_COLUMNS: tuple[str, ...] = ("cik", "period", *tuple(METRIC_COLUMNS))

# Feature table after :func:`src.features.compute_features` (engineered columns + base metrics).
FEATURES_REQUIRED_COLUMNS: tuple[str, ...] = ("cik", "period", *tuple(FEATURE_COLS))

# Long-format data quality summary (see :func:`src.data_quality.compute_data_quality_summary`).
DATA_QUALITY_REQUIRED_COLUMNS: tuple[str, ...] = ("category", "name", "value", "unit", "notes")

# Logical artifact key (as used by evaluation runner / MCP) -> required CSV columns in order-agnostic set.
REQUIRED_COLUMNS_BY_ARTIFACT_KEY: dict[str, tuple[str, ...]] = {
    "panel_csv": PANEL_REQUIRED_COLUMNS,
    "features_csv": FEATURES_REQUIRED_COLUMNS,
    "anomalies_csv": tuple(ANOMALY_OUTPUT_COLUMNS),
    "peer_signals_csv": tuple(PEER_SIGNAL_COLUMNS),
    "trend_break_signals_csv": TREND_BREAK_REQUIRED_COLUMNS_MINIMAL,
    "unified_findings_csv": tuple(UNIFIED_FINDINGS_COLUMNS),
    "data_quality_csv": DATA_QUALITY_REQUIRED_COLUMNS,
    "metric_coverage_summary_csv": tuple(METRIC_COVERAGE_SUMMARY_COLUMNS),
    "metric_coverage_by_company_csv": (
        "cik",
        "metric_name",
        "n_periods",
        "available_count",
        "missing_count",
        "coverage_ratio",
    ),
    "metric_coverage_by_period_csv": (
        "period",
        "metric_name",
        "n_companies",
        "available_count",
        "missing_count",
        "coverage_ratio",
    ),
    "manual_validation_csv": tuple(VALIDATION_COLUMNS),
    "findings_summary_by_company_csv": tuple(FINDINGS_SUMMARY_BY_COMPANY_COLUMNS),
    "findings_summary_by_metric_csv": tuple(FINDINGS_SUMMARY_BY_METRIC_COLUMNS),
    "findings_summary_by_period_csv": tuple(FINDINGS_SUMMARY_BY_PERIOD_COLUMNS),
}


def known_schema_keys() -> frozenset[str]:
    return frozenset(REQUIRED_COLUMNS_BY_ARTIFACT_KEY.keys())


def missing_columns(actual: Iterable[str], required: Iterable[str]) -> list[str]:
    present = set(actual)
    return [c for c in required if c not in present]


def read_csv_columns(path: Path) -> list[str]:
    """Header only — deterministic and cheap."""
    return list(pd.read_csv(path, nrows=0).columns)


def check_csv_schema(path: Path, logical_key: str) -> str | None:
    """
    Validate that ``path`` has required columns for ``logical_key``.

    Returns ``None`` if ok, or a human-readable error line otherwise.
    """
    required = REQUIRED_COLUMNS_BY_ARTIFACT_KEY.get(logical_key)
    if required is None:
        return None
    if not path.is_file():
        return f"{logical_key}: file missing for schema check ({path})"
    try:
        cols = read_csv_columns(path)
    except Exception as exc:
        return f"{logical_key}: cannot read CSV header from {path}: {type(exc).__name__}: {exc}"
    missing = missing_columns(cols, required)
    if missing:
        sample = cols[:25]
        more = f" (+{len(cols) - len(sample)} more)" if len(cols) > len(sample) else ""
        return (
            f"{logical_key}: missing columns {missing!r} "
            f"(found {len(cols)} columns, first {len(sample)}: {sample}{more})"
        )
    return None


def validate_produced_artifact_schemas(
    artifacts: dict[str, str],
    *,
    enforce_schema: bool,
    exempt_keys: frozenset[str] | set[str] | None = None,
) -> tuple[list[str], dict[str, bool]]:
    """
    Run schema checks on all produced artifacts that have a known profile.

    Returns ``(failure_messages, checks)`` where ``checks`` maps
    ``artifact_schema::<logical_key>`` → passed.
    """
    if not enforce_schema:
        return [], {}
    skip = exempt_keys or set()
    failures: list[str] = []
    checks: dict[str, bool] = {}
    for key in sorted(artifacts.keys()):
        if key in skip:
            continue
        if key not in REQUIRED_COLUMNS_BY_ARTIFACT_KEY:
            continue
        path = Path(artifacts[key])
        msg = check_csv_schema(path, key)
        ok = msg is None
        checks[f"artifact_schema::{key}"] = ok
        if msg is not None:
            failures.append(msg)
    return failures, checks
