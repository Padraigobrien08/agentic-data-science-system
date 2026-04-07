"""
Lightweight helpers for manual spot-check validation of extracted metrics vs SEC sources.

See ``validation/README.md`` for workflow. No automated reconciliation or scraping.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

import config

from .normalization import METRIC_COLUMNS

# --- Schema aligned with ``validation/manual_validation.csv`` header row ---
VALIDATION_COLUMNS: tuple[str, ...] = (
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

VALIDATION_CSV_PATH = config.PROJECT_ROOT / "validation" / "manual_validation.csv"


def companyfacts_url(cik: int) -> str:
    """HTTPS URL for SEC XBRL companyfacts JSON (human review in browser or REST client)."""
    cik10 = f"{int(cik):010d}"
    return config.SEC_COMPANYFACTS_URL.format(cik10=cik10)


def panel_to_long(panel: pd.DataFrame, *, metrics: Sequence[str] | None = None) -> pd.DataFrame:
    """
    Wide panel (``cik``, ``period``, metric columns) → long rows for review.

    ``metrics`` defaults to :data:`src.normalization.METRIC_COLUMNS` intersected with panel columns.
    """
    if panel.empty:
        return pd.DataFrame(columns=["cik", "period", "metric", "extracted_value"])
    use = list(metrics) if metrics is not None else [c for c in METRIC_COLUMNS if c in panel.columns]
    if not use:
        return pd.DataFrame(columns=["cik", "period", "metric", "extracted_value"])
    id_vars = [c for c in ("cik", "period") if c in panel.columns]
    long_df = panel.melt(
        id_vars=id_vars,
        value_vars=use,
        var_name="metric",
        value_name="extracted_value",
    )
    return long_df.sort_values(id_vars + ["metric"]).reset_index(drop=True)


def format_candidate_table(
    long_df: pd.DataFrame,
    *,
    max_rows: int = 25,
    drop_na_values: bool = True,
) -> str:
    """Plain-text table plus SEC URL hints (one base URL per distinct CIK)."""
    df = long_df.copy()
    if drop_na_values and "extracted_value" in df.columns:
        df = df[df["extracted_value"].notna()]
    if max_rows > 0:
        df = df.head(max_rows)
    lines: list[str] = []
    if df.empty:
        lines.append("(no candidate rows after filters)")
        return "\n".join(lines)
    lines.append(df.to_string(index=False))
    lines.append("")
    if "cik" in df.columns:
        for cik in sorted(df["cik"].dropna().unique()):
            lines.append(f"# CIK {int(cik)} companyfacts: {companyfacts_url(int(cik))}")
    return "\n".join(lines)


def load_panel(path: Path | None = None) -> pd.DataFrame:
    p = path or (config.DATA_PROCESSED / "panel.csv")
    if not p.is_file():
        raise FileNotFoundError(f"panel not found: {p}")
    return pd.read_csv(p)


def _parse_metrics_arg(s: str | None) -> list[str] | None:
    if not s or not str(s).strip():
        return None
    parts = [x.strip() for x in str(s).split(",") if x.strip()]
    unknown = set(parts) - set(METRIC_COLUMNS)
    if unknown:
        raise ValueError(f"Unknown metric(s): {sorted(unknown)}. Allowed: {METRIC_COLUMNS}")
    return parts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print candidate (cik, period, metric, value) rows for manual SEC validation.",
    )
    parser.add_argument(
        "--panel",
        type=Path,
        default=config.DATA_PROCESSED / "panel.csv",
        help="Wide panel CSV (default: data/processed/panel.csv)",
    )
    parser.add_argument(
        "--metrics",
        type=str,
        default="",
        help=f"Comma-separated metrics to include (default: all panel metrics). One of: {','.join(METRIC_COLUMNS)}",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=25,
        help="Max long-format rows to print after sorting (default: 25). Use 0 for no limit.",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Include rows where extracted_value is null (normally dropped for spot-check prompts).",
    )
    args = parser.parse_args(argv)

    try:
        panel = load_panel(args.panel)
        metrics = _parse_metrics_arg(args.metrics)
        long_df = panel_to_long(panel, metrics=metrics)
        text = format_candidate_table(
            long_df,
            max_rows=args.max_rows,
            drop_na_values=not args.include_empty,
        )
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
