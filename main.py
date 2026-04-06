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
from src.anomaly import detect_anomalies
from src.data_fetch import get_company_data
from src.features import compute_features
from src.metric_extraction import extract_metrics
from src.normalization import build_panel
from src.report import generate_report


def main() -> None:
    tickers = config.DEFAULT_TICKERS[:5]
    long_frames = []
    for t in tickers:
        data = get_company_data(t)
        facts = data["facts"]
        cik = int(data["cik"])
        long_frames.append(extract_metrics(facts, cik, years=config.YEARS_LOOKBACK))

    panel = build_panel(long_frames)
    feats = compute_features(panel)
    anomalies = detect_anomalies(feats)
    report_md = generate_report(anomalies, feats, top_n=5)

    panel.to_csv(config.DATA_PROCESSED / "panel.csv", index=False)
    feats.to_csv(config.DATA_PROCESSED / "features.csv", index=False)
    anomalies.to_csv(config.DATA_ARTIFACTS / "anomalies.csv", index=False)
    (config.DATA_ARTIFACTS / "report.md").write_text(report_md, encoding="utf-8")

    print("\n=== Panel (head) ===\n")
    print(panel.head(12).to_string(index=False))
    print("\n=== Features (head) ===\n")
    print(feats.head(12).to_string(index=False))
    print("\n=== Anomalies (head) ===\n")
    print(anomalies.head(15).to_string(index=False))
    print("\n=== Report (full) ===\n")
    print(report_md)
    print(f"\nWrote: {config.DATA_PROCESSED / 'panel.csv'}")
    print(f"Wrote: {config.DATA_PROCESSED / 'features.csv'}")
    print(f"Wrote: {config.DATA_ARTIFACTS / 'anomalies.csv'}")
    print(f"Wrote: {config.DATA_ARTIFACTS / 'report.md'}")


if __name__ == "__main__":
    main()
