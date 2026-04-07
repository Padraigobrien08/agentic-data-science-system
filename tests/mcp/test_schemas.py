"""Input schema validation and envelope invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from edgar_project.mcp.schemas import (
    BuildPanelInput,
    ErrorInfo,
    ResolveCompanyInput,
    ToolResponseEnvelope,
    ToolStatus,
)


def test_resolve_company_input_rejects_empty_ticker() -> None:
    with pytest.raises(ValidationError):
        ResolveCompanyInput(ticker="")


def test_build_panel_input_rejects_too_many_tickers() -> None:
    with pytest.raises(ValidationError):
        BuildPanelInput(tickers=["A", "B", "C", "D", "E", "F"])


def test_build_panel_input_accepts_valid() -> None:
    inp = BuildPanelInput(tickers=["AAPL", "MSFT"])
    assert inp.tickers == ["AAPL", "MSFT"]


def test_error_envelope_requires_error_entries() -> None:
    with pytest.raises(ValueError):
        ToolResponseEnvelope(
            status=ToolStatus.error,
            message="fail",
            errors=[],
        )


def test_success_envelope_must_not_carry_errors() -> None:
    with pytest.raises(ValueError):
        ToolResponseEnvelope(
            status=ToolStatus.success,
            message="ok",
            errors=[ErrorInfo(code="X", message="y")],
        )


def test_success_envelope_round_trip() -> None:
    env = ToolResponseEnvelope(
        status=ToolStatus.success,
        message="ok",
        data={"a": 1},
        artifacts={"panel_csv": "/tmp/p.csv"},
        errors=[],
    )
    d = env.model_dump(mode="json")
    assert d["status"] == "success"
    assert d["errors"] == []
    assert d["data"]["a"] == 1
