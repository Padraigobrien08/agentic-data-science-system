"""
Unified command-line interface for EDGAR analysis.

Examples::

    python3 -m edgar_project.cli run --tickers AAPL MSFT --goal "find unusual financial changes"
    python3 -m edgar_project.cli demo
    python3 -m edgar_project.cli demo --fixtures
    python3 -m edgar_project.cli evaluate
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from edgar_project.console_digest import print_run_digest_stdout
from edgar_project.demo import DemoScenario, get_demo_scenario, list_demo_scenario_ids, load_demo_catalog
from edgar_project.evaluation.rubric import Rubric
from edgar_project.evaluation.runner import EvaluationRunner
from edgar_project.evaluation.schemas import BenchmarkSuite, EvaluationStatus
from edgar_project.evaluation.summary_report import format_benchmark_cli_summary, format_console_report
from edgar_project.orchestration import OrchestrationInput, run_analysis_agent

_ARTIFACT_ORDER = (
    "report_md",
    "unified_findings_csv",
    "anomalies_csv",
    "trend_break_signals_csv",
    "peer_signals_csv",
    "features_csv",
    "panel_csv",
    "data_quality_csv",
    "metric_coverage_summary_csv",
    "manual_validation_csv",
)


def _chdir_repo_root() -> None:
    """Make cwd the repository root so MCP/pipeline paths match defaults."""
    try:
        os.chdir(_REPO_ROOT)
    except OSError:
        pass


def _format_artifact_lines(paths: dict[str, str]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for key in _ARTIFACT_ORDER:
        if key in paths and paths[key]:
            lines.append(f"  {key}: {paths[key]}")
            seen.add(key)
    for key in sorted(paths.keys()):
        if key in seen or not paths[key]:
            continue
        lines.append(f"  {key}: {paths[key]}")
    return lines


def _print_orchestration_result(
    out,
    *,
    tickers: list[str],
    verbose: bool,
    as_json: bool,
) -> None:
    if as_json:
        print(json.dumps(out.model_dump(mode="json"), indent=2, default=str))
        return

    print_run_digest_stdout(out=out, tickers=list(tickers))

    if verbose:
        print("─" * 52)
        print(" Verbose")
        print("─" * 52)
        if out.tool_call_sequence:
            names = [s.tool_name for s in out.tool_call_sequence]
            print("tools:    " + " → ".join(names))
        if out.resolved_companies:
            cos = ", ".join(f"{c.ticker} ({c.cik})" for c in out.resolved_companies[:12])
            if len(out.resolved_companies) > 12:
                cos += ", …"
            print(f"resolved: {cos}")
        if out.artifact_paths:
            print("all artifacts:")
            for line in _format_artifact_lines(out.artifact_paths):
                print(line)

    for e in out.errors:
        print(f"error [{e.code}]: {e.message}", file=sys.stderr)
    for w in out.warnings:
        print(f"warning [{w.code}]: {w.message}", file=sys.stderr)


def _cmd_run(args: argparse.Namespace) -> int:
    if args.verbose:
        orch = logging.getLogger("edgar_project.orchestration")
        orch.setLevel(logging.INFO)
        if not orch.handlers:
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
            orch.addHandler(h)

    req = OrchestrationInput(
        tickers=list(args.tickers),
        analysis_goal=args.goal,
        refresh=bool(args.refresh),
    )
    out = run_analysis_agent(req)
    _print_orchestration_result(
        out,
        tickers=list(args.tickers),
        verbose=args.verbose,
        as_json=args.json,
    )
    ok = out.status.value in ("success", "partial_success")
    return 0 if ok else 1


def _print_demo_guidance(scenario: DemoScenario) -> None:
    sep = "—" * 64
    print()
    print(sep)
    print(f"Demo: {scenario.title}  ({scenario.id})")
    print(sep)
    print(scenario.description)
    print()
    print("What to look for:")
    for line in scenario.look_for:
        print(f"  • {line}")
    if scenario.highlights:
        print()
        print("Highlights: " + ", ".join(scenario.highlights))
    print()
    print(
        "Live runs write under data/processed/ and data/artifacts/ "
        f"(not data/evaluation/). See {_REPO_ROOT / 'data' / 'README.md'}"
    )
    print(sep)


def _cmd_demo_list() -> int:
    _, default_id, scenarios = load_demo_catalog()
    print("Curated demo scenarios (edit edgar_project/demo/scenarios.json)")
    print(f"Default: {default_id}")
    print()
    for s in scenarios:
        t = " ".join(s.tickers)
        print(f"  {s.id}")
        print(f"      {s.title}")
        print(f"      tickers: {t}")
        print()
    print("Run:  python3 -m edgar_project.cli demo [<scenario_id>]")
    print("       python3 -m edgar_project.cli demo --fixtures   # offline benchmarks")
    print("       python3 -m edgar_project.cli evaluate            # same fixtures, summary only")
    return 0


def _cmd_demo_fixtures(args: argparse.Namespace) -> int:
    suite_path = _REPO_ROOT / "edgar_project/evaluation/benchmarks/suite_fixtures_v1.json"
    rubric_path = _REPO_ROOT / "edgar_project/evaluation/fixtures/rubric_baseline_v1.json"
    print("EDGAR demo — deterministic fixture benchmarks (no live SEC).")
    print(f"Suite: {suite_path.relative_to(_REPO_ROOT)}")
    print()
    suite = BenchmarkSuite.model_validate_json(suite_path.read_text(encoding="utf-8"))
    rubric = Rubric.from_json_file(rubric_path)
    runner = EvaluationRunner(suite=suite, rubric=rubric)
    results = runner.run_suite()
    summary = runner.latest_summary
    if summary is not None:
        print(format_console_report(summary, results))
    if args.verbose and summary is not None:
        print()
        print("Per-case checks (verbose):")
        for r in results:
            print(f"  {r.case_id}: {r.status.value}")
            for k, v in sorted(r.checks.items()):
                print(f"    {k}: {v}")
    out_dir = Path(suite.output_dir).resolve()
    suite_root = out_dir / suite.suite_id
    print()
    print(" Benchmark / demo outputs (under data/evaluation/, not data/artifacts/)")
    print(f"   Suite index:     {out_dir / f'{suite.suite_id}_results.json'}")
    print(f"   Suite summary:   {out_dir / f'{suite.suite_id}_summary.json'}")
    print(f"   Per-case CSVs:   {suite_root}/<case_id>/")
    print(f"   Layout guide:    {_REPO_ROOT / 'data' / 'README.md'}")
    print()
    print("Tip: Live pipeline outputs go to data/processed/ and data/artifacts/ — see data/README.md")
    print("Tip: For a live SEC demo with curated tickers, run:  python3 -m edgar_project.cli demo --list")
    if any(r.status in {EvaluationStatus.failed, EvaluationStatus.error} for r in results):
        return 1
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    if args.demo_list:
        return _cmd_demo_list()
    if args.fixtures:
        return _cmd_demo_fixtures(args)

    raw = args.scenario_opt if args.scenario_opt is not None else args.scenario_pos
    scenario_id = raw.strip() if isinstance(raw, str) and raw.strip() else None
    try:
        scenario = get_demo_scenario(scenario_id)
    except KeyError:
        known = ", ".join(list_demo_scenario_ids()) or "(none)"
        print(
            f"Unknown scenario {scenario_id!r}. Known ids: {known}. "
            "Use: python3 -m edgar_project.cli demo --list",
            file=sys.stderr,
        )
        return 2

    print(f"Scenario: {scenario.id} — {scenario.title}")
    print(f"Tickers:  {' '.join(scenario.tickers)}")
    print("(Live run: uses orchestration + MCP / SEC; may take a minute.)")
    print()

    if args.verbose:
        orch = logging.getLogger("edgar_project.orchestration")
        orch.setLevel(logging.INFO)
        if not orch.handlers:
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
            orch.addHandler(h)

    req = OrchestrationInput(
        tickers=list(scenario.tickers),
        analysis_goal=scenario.goal,
        refresh=bool(args.refresh),
    )
    out = run_analysis_agent(req)
    _print_orchestration_result(
        out,
        tickers=list(scenario.tickers),
        verbose=args.verbose,
        as_json=args.json,
    )

    if not args.json:
        _print_demo_guidance(scenario)

    ok = out.status.value in ("success", "partial_success")
    return 0 if ok else 1


def _cmd_evaluate(args: argparse.Namespace) -> int:
    suite_path = Path(args.suite)
    if not suite_path.is_absolute():
        suite_path = (_REPO_ROOT / suite_path).resolve()
    rubric_path = Path(args.rubric)
    if not rubric_path.is_absolute():
        rubric_path = (_REPO_ROOT / rubric_path).resolve()
    suite = BenchmarkSuite.model_validate_json(suite_path.read_text(encoding="utf-8"))
    if args.write_markdown:
        suite = suite.model_copy(update={"write_markdown_report": True})
    rubric = Rubric.from_json_file(rubric_path)
    runner = EvaluationRunner(
        suite=suite,
        rubric=rubric,
        update_regression_goldens=args.update_regression_goldens,
    )
    results = runner.run_suite()
    summary = runner.latest_summary
    out_dir = Path(suite.output_dir).resolve()
    results_json = out_dir / f"{suite.suite_id}_results.json"
    summary_json = out_dir / f"{suite.suite_id}_summary.json"

    if summary is not None:
        print(
            format_benchmark_cli_summary(
                summary,
                results,
                results_json_path=str(results_json),
                summary_json_path=str(summary_json),
            )
        )
    else:
        print(f"Benchmark finished ({len(results)} case(s)) but no summary was built.")
        print(f"  details (JSON): {results_json}")

    if not args.quiet:
        print()
        print(f"  per-case outputs: {out_dir / suite.suite_id}/<case_id>/")
        if runner.latest_markdown_path is not None:
            print(f"  markdown report:  {runner.latest_markdown_path}")

    if args.verbose and summary is not None:
        print()
        print(format_console_report(summary, results))
    if any(r.status in {EvaluationStatus.failed, EvaluationStatus.error} for r in results):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m edgar_project.cli",
        description="EDGAR analysis — run orchestration, demo scenarios, or benchmarks.",
        epilog=(
            "Typical:  python3 -m edgar_project.cli demo --fixtures\n"
            "          python3 -m edgar_project.cli evaluate\n"
            "          python3 -m edgar_project.cli run --tickers AAPL MSFT --goal \"find unusual financial changes\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("run", help="Run analysis via orchestration (planner + MCP tools)")
    pr.add_argument("-v", "--verbose", action="store_true", help="Orchestration INFO logs on stderr")
    pr.add_argument("--tickers", nargs="+", metavar="SYM", required=True, help="US equity symbols")
    pr.add_argument(
        "--goal",
        required=True,
        help='Analysis goal, e.g. "find unusual financial changes"',
    )
    pr.add_argument("--refresh", action="store_true", help="Bypass cache on fetch steps")
    pr.add_argument(
        "--json",
        action="store_true",
        help="Print full OrchestrationOutput as JSON",
    )
    pr.set_defaults(func=_cmd_run)

    pdemo = sub.add_parser(
        "demo",
        help="Curated live demo (default) or --fixtures / --list",
    )
    pdemo.add_argument(
        "scenario_pos",
        nargs="?",
        default=None,
        metavar="SCENARIO",
        help="Curated scenario id (default: scenarios.json default_scenario)",
    )
    pdemo.add_argument(
        "--scenario",
        dest="scenario_opt",
        metavar="ID",
        help="Same as positional SCENARIO",
    )
    pdemo.add_argument(
        "--list",
        action="store_true",
        dest="demo_list",
        help="List curated scenarios and exit",
    )
    pdemo.add_argument(
        "--fixtures",
        action="store_true",
        help="Offline fixture benchmarks only (no SEC)",
    )
    pdemo.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Orchestration INFO on stderr (live) or per-case checks (fixtures)",
    )
    pdemo.add_argument("--refresh", action="store_true", help="Bypass cache (live demo)")
    pdemo.add_argument("--json", action="store_true", help="Print OrchestrationOutput JSON (live demo)")
    pdemo.set_defaults(func=_cmd_demo)

    pe = sub.add_parser(
        "evaluate",
        help="Run benchmark suite (default: fixture suite; no SEC)",
    )
    pe.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print extended case table (in addition to the short summary)",
    )
    pe.add_argument(
        "--suite",
        type=Path,
        default=Path("edgar_project/evaluation/benchmarks/suite_fixtures_v1.json"),
        help="Benchmark suite JSON manifest",
    )
    pe.add_argument(
        "--rubric",
        type=Path,
        default=Path("edgar_project/evaluation/fixtures/rubric_baseline_v1.json"),
        help="Rubric JSON",
    )
    pe.add_argument("--write-markdown", action="store_true", help="Write suite markdown report")
    pe.add_argument(
        "--quiet",
        action="store_true",
        help="Only the short summary (no per-case directory / markdown hints)",
    )
    pe.add_argument(
        "--update-regression-goldens",
        action="store_true",
        help="Rewrite regression golden JSON files for cases that define them",
    )
    pe.set_defaults(func=_cmd_evaluate)

    return p


def main(argv: list[str] | None = None) -> int:
    _chdir_repo_root()
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
