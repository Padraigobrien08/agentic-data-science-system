"""
Manual spot-check validation: durable CSV records + helpers to emit candidate rows from ``panel.csv``.

See ``validation/README.md`` for the workflow. No automated reconciliation or scraping.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

import config
from edgar_project.run_workspace import RunWorkspace

from .normalization import METRIC_COLUMNS

# --- Canonical validation record (one row = one checked cell or reviewed fact) ---
# Stored in ``validation/manual_validation.csv``; append-only over time.
VALIDATION_COLUMNS: tuple[str, ...] = (
    "ticker",
    "cik",
    "period",
    "metric",
    "extracted_value",
    "expected_value",
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


def candidate_records_from_panel(
    panel: pd.DataFrame,
    *,
    metrics: Sequence[str] | None = None,
    ticker_by_cik: dict[int, str] | None = None,
) -> pd.DataFrame:
    """
    Build a dataframe with :data:`VALIDATION_COLUMNS`: only review fields are pre-filled
    (``cik``, ``period``, ``metric``, ``extracted_value``, and optionally ``ticker`` via ``ticker_by_cik``).
    Remaining columns are empty for the reviewer to complete after comparing to SEC sources.
    """
    long_df = panel_to_long(panel, metrics=metrics)
    if long_df.empty:
        return pd.DataFrame(columns=list(VALIDATION_COLUMNS))

    n = len(long_df)
    empty = [pd.NA] * n
    out = pd.DataFrame(
        {
            "ticker": empty,
            "cik": long_df["cik"].astype(int),
            "period": long_df["period"].astype(str),
            "metric": long_df["metric"].astype(str),
            "extracted_value": long_df["extracted_value"],
            "expected_value": empty,
            "source_reference": empty,
            "checked_by": empty,
            "checked_date": empty,
            "validation_status": empty,
            "notes": empty,
        }
    )
    if ticker_by_cik:
        out["ticker"] = out["cik"].map(lambda c: ticker_by_cik.get(int(c), pd.NA))
    return out[list(VALIDATION_COLUMNS)]


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


def _resolve_panel_path(
    path: Path | None = None,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> Path:
    if path is not None:
        return path
    if workspace is not None:
        return workspace.processed_dir / "panel.csv"
    if use_legacy_shared_paths:
        return config.DATA_PROCESSED / "panel.csv"
    raise ValueError("panel path is required unless workspace or use_legacy_shared_paths=True is provided")


def _resolve_validation_path(
    path: Path | None = None,
    *,
    workspace: RunWorkspace | None = None,
) -> Path:
    if path is not None:
        return path
    if workspace is not None:
        return workspace.manual_validation_csv
    return VALIDATION_CSV_PATH


def load_panel(
    path: Path | None = None,
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> pd.DataFrame:
    p = _resolve_panel_path(
        path,
        workspace=workspace,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
    if not p.is_file():
        raise FileNotFoundError(f"panel not found: {p}")
    return pd.read_csv(p)


def ensure_validation_csv(
    path: Path | None = None,
    *,
    workspace: RunWorkspace | None = None,
) -> Path:
    """Ensure ``manual_validation.csv`` exists with the canonical header (no rows)."""
    p = _resolve_validation_path(path, workspace=workspace)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.is_file() or p.stat().st_size == 0:
        pd.DataFrame(columns=list(VALIDATION_COLUMNS)).to_csv(p, index=False)
    return p.resolve()


def load_validation_records(
    path: Path | None = None,
    *,
    workspace: RunWorkspace | None = None,
) -> pd.DataFrame:
    """Load validation CSV; legacy rows missing ``expected_value`` get an empty column."""
    p = _resolve_validation_path(path, workspace=workspace)
    if not p.is_file():
        return pd.DataFrame(columns=list(VALIDATION_COLUMNS))
    df = pd.read_csv(p)
    for c in VALIDATION_COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA
    return df[list(VALIDATION_COLUMNS)]


def _parse_metrics_arg(s: str | None) -> list[str] | None:
    if not s or not str(s).strip():
        return None
    parts = [x.strip() for x in str(s).split(",") if x.strip()]
    unknown = set(parts) - set(METRIC_COLUMNS)
    if unknown:
        raise ValueError(f"Unknown metric(s): {sorted(unknown)}. Allowed: {METRIC_COLUMNS}")
    return parts


def _parse_ticker_cik_pairs(path: Path) -> dict[int, str]:
    """Two-column CSV ``ticker,cik`` (header optional)."""
    df = pd.read_csv(path)
    cols = {str(c).lower().strip(): c for c in df.columns}
    if "ticker" not in cols or "cik" not in cols:
        raise ValueError("ticker map CSV must have ticker and cik columns")
    tcol, ccol = cols["ticker"], cols["cik"]
    out: dict[int, str] = {}
    for _, r in df.iterrows():
        try:
            out[int(r[ccol])] = str(r[tcol]).strip().upper()
        except (ValueError, TypeError):
            continue
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit candidate rows for manual validation from a wide panel CSV.",
    )
    parser.add_argument(
        "--panel",
        type=Path,
        default=None,
        help="Wide panel CSV. Required unless --use-legacy-shared-paths is set.",
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
        help="Max long-format rows after sort (default: 25). Use 0 for no limit.",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Include rows where extracted_value is null (normally dropped for text output).",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Write candidate rows with full validation schema to this path (default: stdout text only).",
    )
    parser.add_argument(
        "--ticker-map",
        type=Path,
        default=None,
        help="Optional CSV with columns ticker,cik to fill ticker on candidate rows.",
    )
    parser.add_argument(
        "--use-legacy-shared-paths",
        action="store_true",
        help="Opt into the shared Phase 1 path fallback for local/manual workflows.",
    )
    args = parser.parse_args(argv)

    try:
        panel = load_panel(
            args.panel,
            use_legacy_shared_paths=args.use_legacy_shared_paths,
        )
        metrics = _parse_metrics_arg(args.metrics)
        ticker_by = _parse_ticker_cik_pairs(args.ticker_map) if args.ticker_map else None
        candidates = candidate_records_from_panel(panel, metrics=metrics, ticker_by_cik=ticker_by)
        if not args.include_empty and "extracted_value" in candidates.columns:
            candidates = candidates[candidates["extracted_value"].notna()].reset_index(drop=True)
        if args.max_rows and args.max_rows > 0:
            candidates = candidates.head(args.max_rows)
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.output_csv is not None:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        candidates.to_csv(args.output_csv, index=False)
        print(f"Wrote {len(candidates)} candidate row(s) to {args.output_csv.resolve()}", file=sys.stderr)
        return 0

    sub = (
        candidates[["cik", "period", "metric", "extracted_value"]]
        if not candidates.empty
        else candidates
    )
    text = format_candidate_table(sub, max_rows=0, drop_na_values=False)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
