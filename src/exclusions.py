"""
Stable reason codes and helpers for pipeline exclusion summaries.

Downstream reports should reference these ``reason_code`` values only (not free-form prose).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config

# --- Stable reason_code values (metric_extraction / normalization) ---
# Downstream reporting should use these literals only.
UNSUPPORTED_UNIT = "unsupported_unit"
INVALID_FORM = "invalid_form"
INVALID_PERIOD = "invalid_period"  # fp not a fiscal quarter (Q1–Q4)
INVALID_FISCAL_YEAR = "invalid_fiscal_year"
YEAR_OUT_OF_RANGE = "year_out_of_range"
NULL_FACT_VALUE = "null_fact_value"
NON_NUMERIC = "non_numeric"  # fact value not parseable as float
INVALID_ENTRY_SHAPE = "invalid_entry_shape"
SEGMENTED_CONTEXT_EXCLUDED = "segmented_context_excluded"  # dimensional / non-consolidated fact
DUPLICATE_RESOLVED = "duplicate_resolved"
DROP_DUPLICATE_ROW = "drop_duplicate_row"
NON_NUMERIC_COERCION = "non_numeric_coercion"  # wide cell failed pd.to_numeric
MISSING_REQUIRED_METRIC = "missing_required_metric"  # revenue required after wide pivot

ALL_REASON_CODES: frozenset[str] = frozenset(
    {
        UNSUPPORTED_UNIT,
        INVALID_FORM,
        INVALID_PERIOD,
        INVALID_FISCAL_YEAR,
        YEAR_OUT_OF_RANGE,
        NULL_FACT_VALUE,
        NON_NUMERIC,
        INVALID_ENTRY_SHAPE,
        SEGMENTED_CONTEXT_EXCLUDED,
        DUPLICATE_RESOLVED,
        DROP_DUPLICATE_ROW,
        NON_NUMERIC_COERCION,
        MISSING_REQUIRED_METRIC,
    }
)


def bump(counts: dict[str, int] | None, reason_code: str, n: int = 1) -> None:
    """Increment exclusion count (no-op if counts is None or n < 1)."""
    if counts is None or n < 1:
        return
    counts[reason_code] = counts.get(reason_code, 0) + n


def counts_to_rows(stage: str, counts: dict[str, int], *, detail_prefix: str = "") -> list[dict[str, str | int]]:
    """Turn a reason→count map into rows for ``exclusions_summary.csv``."""
    rows: list[dict[str, str | int]] = []
    for reason_code, n in sorted(counts.items()):
        if n <= 0:
            continue
        rows.append(
            {
                "stage": stage,
                "reason_code": reason_code,
                "count": int(n),
                "cik": "",
                "period": "",
                "metric": "",
                "tag": "",
                "detail": detail_prefix,
            }
        )
    return rows


def build_exclusions_dataframe(
    metric_extraction_counts: dict[str, int],
    normalization_counts: dict[str, int],
) -> pd.DataFrame:
    """Single tidy table for ``exclusions_summary.csv``."""
    rows: list[dict[str, str | int]] = []
    rows.extend(counts_to_rows("metric_extraction", metric_extraction_counts, detail_prefix="SEC companyfacts → long"))
    rows.extend(counts_to_rows("normalization", normalization_counts, detail_prefix="pivot → wide → revenue filter"))
    if not rows:
        return pd.DataFrame(
            columns=["stage", "reason_code", "count", "cik", "period", "metric", "tag", "detail"]
        )
    return pd.DataFrame(rows)


def _repo_rel_path(path: Path) -> str:
    root = Path(config.PROJECT_ROOT).resolve()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def format_exclusions_report_line(
    exclusions: pd.DataFrame,
    artifact_paths: dict[str, Path] | None = None,
    *,
    use_legacy_shared_paths: bool = True,
) -> str:
    """One markdown line for ``report.md`` when the exclusions table has rows."""
    if exclusions is None or exclusions.empty:
        return ""
    if artifact_paths is not None and "exclusions" in artifact_paths:
        return f"\n_Exclusions detail: `{_repo_rel_path(artifact_paths['exclusions'])}`._\n"
    if use_legacy_shared_paths:
        return "\n_Exclusions detail: `data/artifacts/exclusions_summary.csv`._\n"
    return "\n_Exclusions detail path unavailable._\n"
