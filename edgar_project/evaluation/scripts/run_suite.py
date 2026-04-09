"""CLI script for running an evaluation benchmark suite."""

from __future__ import annotations

import argparse
from pathlib import Path

from edgar_project.evaluation.rubric import Rubric
from edgar_project.evaluation.runner import EvaluationRunner
from edgar_project.evaluation.schemas import BenchmarkSuite, EvaluationStatus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic EDGAR evaluation suite")
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("edgar_project/evaluation/benchmarks/suite_smoke.json"),
        help="Path to benchmark suite JSON",
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        default=Path("edgar_project/evaluation/fixtures/rubric_baseline_v1.json"),
        help="Path to rubric JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite = BenchmarkSuite.model_validate_json(args.suite.read_text(encoding="utf-8"))
    rubric = Rubric.from_json_file(args.rubric)
    runner = EvaluationRunner(suite=suite, rubric=rubric)
    results = runner.run_suite()
    summary = runner.latest_summary

    print(f"Ran {len(results)} case(s) for suite '{suite.suite_id}'.")
    if summary is not None:
        print(
            "Summary:",
            f"passed={summary.passed_cases}",
            f"failed={summary.failed_cases}",
            f"skipped={summary.skipped_cases}",
            f"errors={summary.error_cases}",
        )

    failed = [r for r in results if r.status in {EvaluationStatus.failed, EvaluationStatus.error}]
    if failed:
        print("Failing cases:")
        for r in failed:
            print(f"  - {r.case_id}: {r.message}")

    results_path = Path(suite.output_dir) / f"{suite.suite_id}_results.json"
    summary_path = Path(suite.output_dir) / f"{suite.suite_id}_summary.json"
    print(f"Results JSON: {results_path}")
    print(f"Summary JSON: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
