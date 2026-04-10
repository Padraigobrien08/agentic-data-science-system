"""Evaluation and benchmark scaffolding for ``edgar_project``."""

from .analytical_checks import run_analytical_findings_checks
from .artifact_checks import (
    REQUIRED_COLUMNS_BY_ARTIFACT_KEY,
    check_csv_schema,
    known_schema_keys,
    missing_columns,
    validate_produced_artifact_schemas,
)
from .rubric import Rubric, RubricCriterion
from .runner import EvaluationRunner
from .regression_snapshot import build_regression_blob, compare_regression_golden, dump_sorted_json, load_golden
from .schemas import (
    BenchmarkCase,
    BenchmarkInput,
    BenchmarkSuite,
    CaseFailureBrief,
    EvaluationResult,
    EvaluationSummary,
    EvaluationStatus,
    ExpectedArtifacts,
    ExpectedFindings,
    ExpectedOrchestration,
    InputMode,
    RegressionGolden,
    RubricScore,
)
from .summary_report import format_console_report, failure_reason_short, render_markdown_report

__all__ = [
    "REQUIRED_COLUMNS_BY_ARTIFACT_KEY",
    "build_regression_blob",
    "compare_regression_golden",
    "dump_sorted_json",
    "load_golden",
    "CaseFailureBrief",
    "BenchmarkCase",
    "BenchmarkInput",
    "BenchmarkSuite",
    "EvaluationRunner",
    "EvaluationResult",
    "EvaluationSummary",
    "EvaluationStatus",
    "ExpectedArtifacts",
    "ExpectedFindings",
    "ExpectedOrchestration",
    "InputMode",
    "RegressionGolden",
    "check_csv_schema",
    "known_schema_keys",
    "missing_columns",
    "run_analytical_findings_checks",
    "validate_produced_artifact_schemas",
    "format_console_report",
    "failure_reason_short",
    "render_markdown_report",
    "Rubric",
    "RubricCriterion",
    "RubricScore",
]
