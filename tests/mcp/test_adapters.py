"""Adapter helpers (provenance, envelopes)."""

from __future__ import annotations

from edgar_project.mcp import adapters as ad


def test_provenance_from_resolve_matches_single_ticker_shape() -> None:
    ad.ensure_sys_path()
    p = ad.provenance_from_resolve(
        {"ticker": "AAPL", "cik": 320193, "company_name": "Apple Inc."}
    )
    assert p["input_tickers"] == ["AAPL"]
    assert p["ciks"] == [320193]
    assert p["resolved_ciks"] == [{"ticker": "AAPL", "cik": 320193}]
