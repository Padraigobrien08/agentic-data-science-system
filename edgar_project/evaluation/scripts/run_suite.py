"""CLI script for running an evaluation benchmark suite."""

from __future__ import annotations

import argparse
from pathlib import Path

from edgar_project.evaluation.rubric import Rubric
from edgar_project.evaluation.runner import EvaluationRunner
from edgar_project.evaluation.schemas import BenchmarkSuite, EvaluationStatus
from edgar_project.evaluation.summary_report import format_console_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic EDGAR evaluation suite")
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("edgar_project/evaluation/benchmarks/suite_fixtures_v1.json"),
        help="Path to benchmark suite JSON",
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        default=Path("edgar_project/evaluation/fixtures/rubric_baseline_v1.json"),
        help="Path to rubric JSON",
    )
    parser.add_argument(
        "--write-markdown",
        action="store_true",
        help="Write <suite_id>_report.md under output_dir (in addition to JSON)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the summary block (no per-path echoes)",
    )
    parser.add_argument(
        "--update-regression-goldens",
        action="store_true",
        help="Rewrite regression golden JSON files from current fixture outputs (cases with regression_golden set)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite = BenchmarkSuite.model_validate_json(args.suite.read_text(encoding="utf-8"))
    if args.write_markdown:
        suite = suite.model_copy(update={"write_markdown_report": True})
    rubric = Rubric.from_json_file(args.rubric)
    runner = EvaluationRunner(
        suite=suite,
        rubric=rubric,
        update_regression_goldens=args.update_regression_goldens,
    )
    results = runner.run_suite()
    summary = runner.latest_summary

    if summary is not None:
        print(format_console_report(summary, results))
    else:
        print(f"Ran {len(results)} case(s) for suite '{suite.suite_id}' (no summary).")

    if not args.quiet:
        results_path = Path(suite.output_dir) / f"{suite.suite_id}_results.json"
        summary_path = Path(suite.output_dir) / f"{suite.suite_id}_summary.json"
        print(f"Results JSON: {results_path.resolve()}")
        print(f"Summary JSON: {summary_path.resolve()}")
        if runner.latest_markdown_path is not None:
            print(f"Markdown report: {runner.latest_markdown_path}")
    if any(r.status in {EvaluationStatus.failed, EvaluationStatus.error} for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
