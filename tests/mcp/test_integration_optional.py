"""
Opt-in checks against real resolver / cache (not run by default).

Does not mock ``resolve_company_dict``. Uses SEC ``company_tickers`` cache under
``data/raw/`` after first successful fetch, or network on cold cache.

Run::

    MCP_LIVE_SEC=1 python -m pytest tests/mcp/test_integration_optional.py -v
"""

from __future__ import annotations

import os

import pytest

from edgar_project.mcp import tools as mcp_tools
from edgar_project.mcp.schemas import ResolveCompanyInput


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("MCP_LIVE_SEC") != "1",
    reason="Set MCP_LIVE_SEC=1 to enable (uses resolver; may hit network if cache cold)",
)
def test_resolve_company_live_aapl() -> None:
    env = mcp_tools.resolve_company_tool(ResolveCompanyInput(ticker="AAPL"))
    assert env.status.value == "success"
    assert env.data.get("cik") == 320193
    assert env.data.get("ticker") == "AAPL"
