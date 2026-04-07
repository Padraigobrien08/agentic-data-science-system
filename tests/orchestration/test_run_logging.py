from __future__ import annotations

from edgar_project.orchestration.run_logging import tool_summary_line
from edgar_project.orchestration.schemas import ToolResultSummary


def test_tool_summary_line_includes_counts() -> None:
    ts = ToolResultSummary(
        order=0,
        tool_name="detect_anomalies",
        mcp_status="success",
        panel_row_count=None,
        feature_row_count=12,
        anomaly_count=3,
        report_character_count=None,
        ciks_observed=[1, 2],
        artifact_paths={"features_csv": "/tmp/f.csv"},
        provenance_keys=[],
    )
    s = tool_summary_line(ts)
    assert "mcp_status=success" in s
    assert "feature_rows=12" in s
    assert "anomaly_count=3" in s
    assert "ciks=[1, 2]" in s
    assert "artifact_roles=" in s
