"""
Canonical EDGAR metric → XBRL (us-gaap) tag mapping for :mod:`src.metric_extraction`.

**Single source of truth** for:
  - tag priority per pipeline metric
  - documentation artifacts under ``docs/`` and ``validation/``

Regenerate those files after editing :data:`METRIC_SPECS`::

    python -m src.metric_mapping
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import config

# SEC companyfacts JSON nests concepts under ``facts["us-gaap"][tag]``.
TAXONOMY_ID = "us-gaap"

# Extraction accepts only these unit keys per fact (see ``metric_extraction._gather_tag_rows``).
DEFAULT_ACCEPTED_UNITS: tuple[str, ...] = ("USD",)

# Shared pipeline constraints (not per-tag), for documentation.
EXTRACTION_CONTEXT = (
    "Facts must use form 10-K or 10-Q, fiscal period fp in {Q1, Q2, Q3, Q4}, and fiscal year fy "
    "within the configured lookback window. "
    "Per (canonical_metric, fy, fp), the first tag in priority order with at least one qualifying "
    "fact wins; if multiple facts remain for the same tag, the row with the latest ``filed`` date wins."
)


@dataclass(frozen=True)
class MetricMappingSpec:
    """One pipeline metric and its preferred us-gaap concept names (highest priority first)."""

    name: str
    tags: tuple[str, ...]
    notes: str = ""


# Order matches wide panel columns in :mod:`src.normalization` (:data:`METRIC_COLUMNS`).
METRIC_SPECS: tuple[MetricMappingSpec, ...] = (
    MetricMappingSpec(
        name="revenue",
        tags=(
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
        ),
        notes=(
            "Common revenue concepts under ASC 606 and legacy labels; "
            "including-assessed-tax variant is lowest priority. "
            "Issuers may report under different tags over time—priority order picks one concept per quarter."
        ),
    ),
    MetricMappingSpec(
        name="net_income",
        tags=("NetIncomeLoss", "ProfitLoss"),
        notes="ProfitLoss is a broader fallback when NetIncomeLoss is absent.",
    ),
    MetricMappingSpec(
        name="total_assets",
        tags=("Assets",),
        notes="Consolidated assets; point-in-time balance sheet fact matched to fiscal quarter metadata.",
    ),
    MetricMappingSpec(
        name="total_liabilities",
        tags=("Liabilities",),
        notes="Consolidated liabilities; point-in-time, same period rules as total_assets.",
    ),
    MetricMappingSpec(
        name="operating_cash_flow",
        tags=("NetCashProvidedByUsedInOperatingActivities",),
        notes=(
            "Operating cash flow line; in filings, cumulative-YTD vs single-quarter presentation varies by issuer—"
            "facts are still keyed by SEC fy/fp in companyfacts."
        ),
    ),
    MetricMappingSpec(
        name="current_assets",
        tags=("AssetsCurrent",),
        notes="Current assets for liquidity ratios.",
    ),
    MetricMappingSpec(
        name="current_liabilities",
        tags=("LiabilitiesCurrent",),
        notes="Current liabilities for liquidity ratios.",
    ),
)

METRIC_TAGS: dict[str, list[str]] = {s.name: list(s.tags) for s in METRIC_SPECS}

METRIC_COLUMN_ORDER: tuple[str, ...] = tuple(s.name for s in METRIC_SPECS)


def metric_mapping_csv_rows() -> list[dict[str, str]]:
    """One row per (metric, tag) for machine-readable review and diffs."""
    rows: list[dict[str, str]] = []
    for spec in METRIC_SPECS:
        for i, tag in enumerate(spec.tags, start=1):
            rows.append(
                {
                    "canonical_metric_name": spec.name,
                    "tag_priority": str(i),
                    "xbrl_tag": tag,
                    "taxonomy": TAXONOMY_ID,
                    "accepted_units": ";".join(DEFAULT_ACCEPTED_UNITS),
                    "metric_notes": spec.notes,
                }
            )
    return rows


def write_metric_mapping_csv(path: Path | None = None) -> Path:
    path = path or (config.PROJECT_ROOT / "validation" / "metric_mapping.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = metric_mapping_csv_rows()
    fieldnames = [
        "canonical_metric_name",
        "tag_priority",
        "xbrl_tag",
        "taxonomy",
        "accepted_units",
        "metric_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path.resolve()


def write_metric_mapping_md(path: Path | None = None) -> Path:
    path = path or (config.PROJECT_ROOT / "docs" / "metric_mapping.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# EDGAR pipeline: metric → XBRL mapping\n",
        "\n",
        "This file is **generated** from `src/metric_mapping.py` — edit that module, then run:\n\n",
        "```bash\npython -m src.metric_mapping\n```\n\n",
        "## Global rules\n\n",
        f"- **Taxonomy**: `{TAXONOMY_ID}` (companyfacts path `facts[\"us-gaap\"][<tag>]`).\n",
        f"- **Accepted units**: {', '.join(repr(u) for u in DEFAULT_ACCEPTED_UNITS)} (other unit keys are skipped).\n",
        f"- **Selection**: {EXTRACTION_CONTEXT}\n\n",
        "## Metrics (tag priority: 1 = highest)\n\n",
    ]
    for spec in METRIC_SPECS:
        lines.append(f"### `{spec.name}`\n\n")
        if spec.notes:
            lines.append(f"{spec.notes}\n\n")
        lines.append("| Priority | XBRL tag (local name) |\n")
        lines.append("|----------|------------------------|\n")
        for i, tag in enumerate(spec.tags, start=1):
            lines.append(f"| {i} | `{tag}` |\n")
        lines.append("\n")
    lines.append("---\n\n_Single source of truth: `src/metric_mapping.py` (`METRIC_SPECS`)._\n")
    path.write_text("".join(lines), encoding="utf-8")
    return path.resolve()


def write_all_metric_mapping_artifacts() -> dict[str, Path]:
    return {
        "csv": write_metric_mapping_csv(),
        "md": write_metric_mapping_md(),
    }


def main() -> None:
    out = write_all_metric_mapping_artifacts()
    print(f"Wrote {out['csv']}")
    print(f"Wrote {out['md']}")


if __name__ == "__main__":
    main()
