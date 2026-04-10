"""
Deterministic MCP mocks for orchestration end-to-end evaluation (no SEC / no live I/O).

Patches ``edgar_project.orchestration.executor.mcp_tools`` where the executor imports it.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_REPORT,
    ErrorInfo,
    ResolveCompanyInput,
    ToolResponseEnvelope,
    ToolStatus,
)

_MCP = "edgar_project.orchestration.executor.mcp_tools"


def _ok(
    *,
    message: str = "ok",
    data: dict[str, Any] | None = None,
    artifacts: dict[str, str] | None = None,
) -> ToolResponseEnvelope:
    return ToolResponseEnvelope(
        status=ToolStatus.success,
        message=message,
        data=data or {},
        artifacts=artifacts or {},
        errors=[],
    )


def _no_data(message: str = "no data") -> ToolResponseEnvelope:
    return ToolResponseEnvelope(
        status=ToolStatus.no_data,
        message=message,
        data={},
        artifacts={},
        errors=[],
    )


def _err(code: str, message: str) -> ToolResponseEnvelope:
    return ToolResponseEnvelope(
        status=ToolStatus.error,
        message=message,
        data={},
        artifacts={},
        errors=[ErrorInfo(code=code, message=message)],
    )


def _mocks_granular_success_two_tickers() -> dict[str, MagicMock]:
    """Happy path granular plan: resolve → fetch → panel → features → anomalies → report."""

    def resolve(inp: ResolveCompanyInput):
        cik = {"AAPL": 320193, "MSFT": 789019}[inp.ticker]
        return _ok(data={"ticker": inp.ticker, "cik": cik, "company_name": f"Co-{inp.ticker}"})

    def fetch(inp):
        return _ok(data={"ticker": inp.ticker})

    def build_panel(inp):
        return _ok(
            data={"row_count": 4, "ciks": [320193, 789019]},
            artifacts={ARTIFACT_KEY_PANEL: "/eval/mock/panel.csv"},
        )

    def compute_features(inp):
        return _ok(data={"row_count": 4}, artifacts={ARTIFACT_KEY_FEATURES: "/eval/mock/features.csv"})

    def detect(inp):
        return _ok(
            data={"feature_row_count": 4, "anomaly_count": 2},
            artifacts={ARTIFACT_KEY_ANOMALIES: "/eval/mock/anomalies.csv"},
        )

    def report(inp):
        return _ok(
            data={"report_chars": 1200, "report": {"path": "/eval/mock/report.md"}},
            artifacts={ARTIFACT_KEY_REPORT: "/eval/mock/report.md"},
        )

    return {
        "resolve_company_tool": MagicMock(side_effect=resolve),
        "fetch_company_data_tool": MagicMock(side_effect=fetch),
        "build_panel_tool": MagicMock(side_effect=build_panel),
        "compute_features_tool": MagicMock(side_effect=compute_features),
        "detect_anomalies_tool": MagicMock(side_effect=detect),
        "generate_report_tool": MagicMock(side_effect=report),
        "run_pipeline_tool": MagicMock(side_effect=lambda *_a, **_k: _err("UNEXPECTED", "run_pipeline not used")),
    }


def _mocks_partial_one_resolve_fails() -> dict[str, MagicMock]:
    """One ticker fails resolve; downstream still produces a panel for the good ticker."""

    def resolve(inp: ResolveCompanyInput):
        if inp.ticker == "AAPL":
            return _ok(data={"ticker": inp.ticker, "cik": 1, "company_name": "A"})
        return _err("UNKNOWN_TICKER", f"bad {inp.ticker}")

    return {
        "resolve_company_tool": MagicMock(side_effect=resolve),
        "fetch_company_data_tool": MagicMock(side_effect=lambda inp: _ok(data={"ticker": inp.ticker})),
        "build_panel_tool": MagicMock(
            side_effect=lambda inp: _ok(
                data={"row_count": 2, "ciks": [1]},
                artifacts={ARTIFACT_KEY_PANEL: "/eval/mock/panel.csv"},
            )
        ),
        "compute_features_tool": MagicMock(
            side_effect=lambda inp: _ok(data={"row_count": 2}, artifacts={ARTIFACT_KEY_FEATURES: "/eval/mock/features.csv"})
        ),
        "detect_anomalies_tool": MagicMock(
            side_effect=lambda inp: _ok(
                data={"feature_row_count": 2, "anomaly_count": 1},
                artifacts={ARTIFACT_KEY_ANOMALIES: "/eval/mock/anomalies.csv"},
            )
        ),
        "generate_report_tool": MagicMock(
            side_effect=lambda inp: _ok(
                data={"report_chars": 100, "report": {"path": "/eval/mock/report.md"}},
                artifacts={ARTIFACT_KEY_REPORT: "/eval/mock/report.md"},
            )
        ),
        "run_pipeline_tool": MagicMock(side_effect=lambda *_a, **_k: _err("UNEXPECTED", "run_pipeline not used")),
    }


def _mocks_no_data_all_fetches() -> dict[str, MagicMock]:
    """All fetches return no_data; executor should classify terminal no_data without panel."""

    return {
        "resolve_company_tool": MagicMock(
            side_effect=lambda inp: _ok(data={"ticker": inp.ticker, "cik": 999, "company_name": "X"})
        ),
        "fetch_company_data_tool": MagicMock(side_effect=lambda inp: _no_data("empty cache")),
        "build_panel_tool": MagicMock(side_effect=lambda inp: _ok(data={"row_count": 0})),
        "compute_features_tool": MagicMock(),
        "detect_anomalies_tool": MagicMock(),
        "generate_report_tool": MagicMock(),
        "run_pipeline_tool": MagicMock(),
    }


def _mocks_run_pipeline_success() -> dict[str, MagicMock]:
    """Single-step run_pipeline plan."""

    def run_pipeline(inp):
        return _ok(
            data={"panel_rows": 4, "feature_rows": 4, "anomaly_rows": 2},
            artifacts={
                ARTIFACT_KEY_PANEL: "/eval/mock/panel.csv",
                ARTIFACT_KEY_FEATURES: "/eval/mock/features.csv",
                ARTIFACT_KEY_ANOMALIES: "/eval/mock/anomalies.csv",
                ARTIFACT_KEY_REPORT: "/eval/mock/report.md",
            },
        )

    return {
        "run_pipeline_tool": MagicMock(side_effect=run_pipeline),
        "resolve_company_tool": MagicMock(side_effect=lambda *_a, **_k: _err("UNEXPECTED", "resolve not used")),
        "fetch_company_data_tool": MagicMock(),
        "build_panel_tool": MagicMock(),
        "compute_features_tool": MagicMock(),
        "detect_anomalies_tool": MagicMock(),
        "generate_report_tool": MagicMock(),
    }


ORCHESTRATION_MOCK_SCENARIOS: dict[str, Any] = {
    "mock_granular_success": _mocks_granular_success_two_tickers,
    "mock_partial_resolve": _mocks_partial_one_resolve_fails,
    "mock_no_data_fetch": _mocks_no_data_all_fetches,
    "mock_run_pipeline_success": _mocks_run_pipeline_success,
}


def list_mock_scenario_ids() -> tuple[str, ...]:
    return tuple(sorted(ORCHESTRATION_MOCK_SCENARIOS.keys()))


@contextmanager
def patched_mcp_tools(scenario_id: str):
    """Apply MCP mocks for a named scenario for the duration of the context."""
    factory = ORCHESTRATION_MOCK_SCENARIOS.get(scenario_id)
    if factory is None:
        known = ", ".join(ORCHESTRATION_MOCK_SCENARIOS.keys())
        raise KeyError(f"Unknown orchestration mock scenario {scenario_id!r}. Known: {known}")
    mocks = factory()
    with patch.multiple(_MCP, **mocks):
        yield
