"""
Local CLI for invoking MCP tools without an MCP client (development / debugging).

Run from repository root::

    python -m edgar_project.mcp.cli resolve-company AAPL
    python -m edgar_project.mcp.cli run-pipeline --tickers AAPL MSFT

Output is JSON (pretty-printed) on stdout; tool names and args are logged on stderr.
Use ``-q`` before the subcommand to suppress INFO logs, e.g.
``python -m edgar_project.mcp.cli -q resolve-company AAPL``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from edgar_project.mcp import tools as mcp_tools
from edgar_project.mcp.adapters import ensure_sys_path
from edgar_project.mcp.schemas import (
    BuildPanelInput,
    ComputeFeaturesInput,
    DetectAnomaliesInput,
    FetchCompanyDataInput,
    GenerateReportInput,
    ResolveCompanyInput,
    RunPipelineInput,
)

ensure_sys_path()

_LOG = logging.getLogger("edgar.mcp.cli")


def _emit(result: dict[str, Any]) -> None:
    print(json.dumps(result, indent=2, default=str))


def _cmd_resolve_company(ns: argparse.Namespace) -> None:
    env = mcp_tools.resolve_company_tool(ResolveCompanyInput(ticker=ns.ticker))
    _emit(mcp_tools.to_json_dict(env))


def _cmd_fetch_company_data(ns: argparse.Namespace) -> None:
    env = mcp_tools.fetch_company_data_tool(
        FetchCompanyDataInput(ticker=ns.ticker, refresh=ns.refresh)
    )
    _emit(mcp_tools.to_json_dict(env))


def _cmd_build_panel(ns: argparse.Namespace) -> None:
    env = mcp_tools.build_panel_tool(
        BuildPanelInput(tickers=list(ns.tickers), refresh=ns.refresh)
    )
    _emit(mcp_tools.to_json_dict(env))


def _cmd_compute_features(ns: argparse.Namespace) -> None:
    tickers = list(ns.tickers) if ns.tickers else None
    env = mcp_tools.compute_features_tool(
        ComputeFeaturesInput(tickers=tickers, panel_csv_path=ns.panel_csv)
    )
    _emit(mcp_tools.to_json_dict(env))


def _cmd_detect_anomalies(ns: argparse.Namespace) -> None:
    tickers = list(ns.tickers) if ns.tickers else None
    env = mcp_tools.detect_anomalies_tool(
        DetectAnomaliesInput(tickers=tickers, features_csv_path=ns.features_csv)
    )
    _emit(mcp_tools.to_json_dict(env))


def _cmd_generate_report(ns: argparse.Namespace) -> None:
    env = mcp_tools.generate_report_tool(
        GenerateReportInput(
            anomalies_csv_path=ns.anomalies_csv,
            features_csv_path=ns.features_csv,
            use_default_artifact_paths=ns.use_default,
        )
    )
    _emit(mcp_tools.to_json_dict(env))


def _cmd_run_pipeline(ns: argparse.Namespace) -> None:
    tickers = list(ns.tickers) if ns.tickers else None
    env = mcp_tools.run_pipeline_tool(
        RunPipelineInput(tickers=tickers, refresh=ns.refresh)
    )
    _emit(mcp_tools.to_json_dict(env))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m edgar_project.mcp.cli",
        description="Invoke EDGAR MCP tools locally; prints JSON envelope on stdout.",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress INFO logs (stderr); errors still log at WARNING+.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s1 = sub.add_parser("resolve-company", help="Ticker → CIK / name")
    s1.add_argument("ticker")
    s1.set_defaults(func=_cmd_resolve_company)

    s2 = sub.add_parser("fetch-company-data", help="Cache SEC submissions + companyfacts JSON")
    s2.add_argument("ticker")
    s2.add_argument("--refresh", action="store_true")
    s2.set_defaults(func=_cmd_fetch_company_data)

    s3 = sub.add_parser("build-panel", help="Wide quarterly panel → panel.csv")
    s3.add_argument("tickers", nargs="+", metavar="TICKER")
    s3.add_argument("--refresh", action="store_true")
    s3.set_defaults(func=_cmd_build_panel)

    s4 = sub.add_parser("compute-features", help="Panel → features.csv (tickers XOR --panel-csv)")
    g4 = s4.add_mutually_exclusive_group(required=True)
    g4.add_argument("--tickers", nargs="+", metavar="TICKER")
    g4.add_argument("--panel-csv", dest="panel_csv")
    s4.set_defaults(func=_cmd_compute_features)

    s5 = sub.add_parser("detect-anomalies", help="Features → anomalies.csv (tickers XOR --features-csv)")
    g5 = s5.add_mutually_exclusive_group(required=True)
    g5.add_argument("--tickers", nargs="+", metavar="TICKER")
    g5.add_argument("--features-csv", dest="features_csv")
    s5.set_defaults(func=_cmd_detect_anomalies)

    s6 = sub.add_parser("generate-report", help="Markdown report from feature + anomaly CSVs")
    s6.add_argument(
        "--use-default",
        action="store_true",
        help="Use Phase 1 paths under config.DATA_*",
    )
    s6.add_argument("--features-csv", dest="features_csv")
    s6.add_argument("--anomalies-csv", dest="anomalies_csv")
    s6.set_defaults(func=_cmd_generate_report)

    s7 = sub.add_parser("run-pipeline", help="Full pipeline → all Phase 1 artifacts")
    s7.add_argument("--tickers", nargs="*", metavar="TICKER")
    s7.add_argument("--refresh", action="store_true")
    s7.set_defaults(func=_cmd_run_pipeline)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    ns = parser.parse_args(argv)
    level = logging.WARNING if ns.quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )
    _LOG.info("cli_invoke command=%s", ns.command)
    try:
        ns.func(ns)
    except Exception as e:
        _LOG.exception("cli failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
