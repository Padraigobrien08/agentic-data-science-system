#!/usr/bin/env python3
"""
EDGAR Anomaly Detector V1 — run full pipeline and write artifacts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from src.pipeline_runner import run_pipeline_computation, write_all_phase1_artifacts


def main() -> None:
    tickers = config.DEFAULT_TICKERS[:5]
    panel, feats, anom, report_md, dq_df, excl_df, peer_df, cave_long = run_pipeline_computation(
        tickers, refresh=False
    )
    write_all_phase1_artifacts(
        panel,
        feats,
        anom,
        report_md,
        data_quality=dq_df,
        exclusions=excl_df,
        peer_signals=peer_df,
        extraction_caveats_long=cave_long,
    )

    print("\n=== Panel (head) ===\n")
    print(panel.head(12).to_string(index=False))
    print("\n=== Features (head) ===\n")
    print(feats.head(12).to_string(index=False))
    print("\n=== Anomalies (head) ===\n")
    print(anom.head(15).to_string(index=False))
    print("\n=== Report (full) ===\n")
    print(report_md)
    print(f"\nWrote: {config.DATA_PROCESSED / 'panel.csv'}")
    print(f"Wrote: {config.DATA_PROCESSED / 'features.csv'}")
    print(f"Wrote: {config.DATA_ARTIFACTS / 'anomalies.csv'}")
    print(f"Wrote: {config.DATA_ARTIFACTS / 'report.md'}")
    print(f"Wrote: {config.DATA_ARTIFACTS / 'data_quality_summary.csv'}")
    print(f"Wrote: {config.DATA_ARTIFACTS / 'exclusions_summary.csv'}")
    print(f"Wrote: {config.DATA_ARTIFACTS / 'peer_signals.csv'}")


if __name__ == "__main__":
    main()
