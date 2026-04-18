"""CLI and docs guardrails for explicit live evaluation opt-in."""

from __future__ import annotations

from pathlib import Path

from edgar_project.cli import build_parser
from edgar_project.evaluation.scripts.run_suite import parse_args


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_root_evaluate_parser_defaults_to_fixture_suite_without_live_opt_in() -> None:
    args = build_parser().parse_args(["evaluate"])

    assert args.allow_live is False
    assert args.suite_id == "suite_fixtures_v1"
    assert args.suite is None


def test_root_evaluate_parser_accepts_explicit_live_opt_in() -> None:
    args = build_parser().parse_args(["evaluate", "--allow-live"])

    assert args.allow_live is True


def test_run_suite_parser_defaults_to_fixture_suite_without_live_opt_in() -> None:
    args = parse_args([])

    assert args.allow_live is False
    assert args.suite == Path("edgar_project/evaluation/benchmarks/suite_fixtures_v1.json")


def test_run_suite_parser_accepts_explicit_live_opt_in() -> None:
    args = parse_args(["--allow-live"])

    assert args.allow_live is True


def test_docs_keep_live_validation_operator_only() -> None:
    evaluation_readme = (REPO_ROOT / "edgar_project/evaluation/README.md").read_text(encoding="utf-8")
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    data_readme = (REPO_ROOT / "data/README.md").read_text(encoding="utf-8")

    assert "--allow-live" in evaluation_readme
    assert "operator-invoked" in evaluation_readme
    assert "non-merge-blocking" in evaluation_readme
    assert "API-backed" in evaluation_readme
    assert "compatibility path" in evaluation_readme

    assert "evaluate" in root_readme
    assert "--allow-live" in root_readme
    assert "offline fixture suite" in root_readme
    assert "--suite-id" in root_readme
    assert "developer fallback" in root_readme

    assert "evaluation/" in data_readme
    assert "not normal user-run histories" in data_readme
