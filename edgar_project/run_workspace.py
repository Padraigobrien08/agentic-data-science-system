"""Shared run-scoped workspace contract for deterministic Phase 1 outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import config

_PHASE1_OUTPUT_LAYOUT: dict[str, tuple[str, str]] = {
    "panel": ("processed", "panel.csv"),
    "features": ("processed", "features.csv"),
    "anomalies": ("artifacts", "anomalies.csv"),
    "report": ("artifacts", "report.md"),
    "data_quality": ("artifacts", "data_quality_summary.csv"),
    "exclusions": ("artifacts", "exclusions_summary.csv"),
    "peer_signals": ("artifacts", "peer_signals.csv"),
    "trend_breaks": ("artifacts", "trend_break_signals.csv"),
    "unified_findings": ("artifacts", "unified_findings.csv"),
    "deterioration_focus": ("artifacts", "deterioration_focus.csv"),
    "findings_summary_by_company": ("artifacts", "findings_summary_by_company.csv"),
    "findings_summary_by_metric": ("artifacts", "findings_summary_by_metric.csv"),
    "findings_summary_by_period": ("artifacts", "findings_summary_by_period.csv"),
    "metric_coverage_summary": ("artifacts", "metric_coverage_summary.csv"),
    "metric_coverage_by_company": ("artifacts", "metric_coverage_by_company.csv"),
    "metric_coverage_by_period": ("artifacts", "metric_coverage_by_period.csv"),
    "metric_caveats_extraction": ("artifacts", "metric_caveats_extraction.csv"),
    "metric_caveats_panel": ("artifacts", "metric_caveats_panel.csv"),
}


@dataclass(frozen=True)
class RunWorkspace:
    run_scoped_id: str
    root: Path
    processed_dir: Path
    artifacts_dir: Path
    manual_validation_csv: Path
    use_legacy_shared_paths: bool = False

    def ensure_directories(self) -> "RunWorkspace":
        self.root.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        return self


def phase1_paths(workspace: RunWorkspace) -> dict[str, Path]:
    """Return the canonical Phase 1 output paths for ``workspace``."""
    return {
        role: (
            workspace.processed_dir / basename
            if area == "processed"
            else workspace.artifacts_dir / basename
        )
        for role, (area, basename) in _PHASE1_OUTPUT_LAYOUT.items()
    }


def build_run_workspace(
    *,
    workspace_root: Path,
    run_scoped_id: str,
    manual_validation_csv: Path,
    use_legacy_shared_paths: bool = False,
    legacy_processed_dir: Path | None = None,
    legacy_artifacts_dir: Path | None = None,
) -> RunWorkspace:
    root = workspace_root / run_scoped_id
    processed_dir = root / "processed"
    artifacts_dir = root / "artifacts"

    if use_legacy_shared_paths:
        processed_dir = legacy_processed_dir or config.DATA_PROCESSED
        artifacts_dir = legacy_artifacts_dir or config.DATA_ARTIFACTS

    return RunWorkspace(
        run_scoped_id=run_scoped_id,
        root=root,
        processed_dir=processed_dir,
        artifacts_dir=artifacts_dir,
        manual_validation_csv=manual_validation_csv,
        use_legacy_shared_paths=use_legacy_shared_paths,
    )
