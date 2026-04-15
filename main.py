#!/usr/bin/env python3
"""
EDGAR Anomaly Detector V1 — run full pipeline and write artifacts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from edgar_project.run_workspace import build_run_workspace
from src.pipeline_runner import run_pipeline_computation, write_all_phase1_artifacts


def main() -> None:
    tickers = config.DEFAULT_TICKERS[:5]
    workspace = build_run_workspace(
        workspace_root=config.DATA_RUNS,
        run_scoped_id=f"main-{uuid4().hex[:12]}",
        manual_validation_csv=(config.PROJECT_ROOT / "validation" / "manual_validation.csv"),
    )
    panel, feats, anom, report_md, dq_df, excl_df, peer_df, cave_long = run_pipeline_computation(
        tickers,
        refresh=False,
        workspace=workspace,
    )
    paths = write_all_phase1_artifacts(
        panel,
        feats,
        anom,
        report_md,
        workspace=workspace,
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
    print(f"\nRun workspace: {workspace.root}")
    print(f"Wrote: {paths['panel']}")
    print(f"Wrote: {paths['features']}")
    print(f"Wrote: {paths['anomalies']}")
    print(f"Wrote: {paths['report']}")
    print(f"Wrote: {paths['data_quality']}")
    print(f"Wrote: {paths['exclusions']}")
    print(f"Wrote: {paths['peer_signals']}")


if __name__ == "__main__":
    main()
