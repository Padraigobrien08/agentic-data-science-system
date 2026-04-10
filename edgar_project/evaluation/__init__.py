"""Evaluation and benchmark scaffolding for ``edgar_project``."""

from .artifact_checks import (
    REQUIRED_COLUMNS_BY_ARTIFACT_KEY,
    check_csv_schema,
    known_schema_keys,
    missing_columns,
    validate_produced_artifact_schemas,
)
from .rubric import Rubric, RubricCriterion
from .runner import EvaluationRunner
from .schemas import (
    BenchmarkCase,
    BenchmarkInput,
    BenchmarkSuite,
    EvaluationResult,
    EvaluationSummary,
    EvaluationStatus,
    ExpectedArtifacts,
    ExpectedFindings,
    InputMode,
    RubricScore,
)

__all__ = [
    "REQUIRED_COLUMNS_BY_ARTIFACT_KEY",
    "BenchmarkCase",
    "BenchmarkInput",
    "BenchmarkSuite",
    "EvaluationRunner",
    "EvaluationResult",
    "EvaluationSummary",
    "EvaluationStatus",
    "ExpectedArtifacts",
    "ExpectedFindings",
    "InputMode",
    "check_csv_schema",
    "known_schema_keys",
    "missing_columns",
    "validate_produced_artifact_schemas",
    "Rubric",
    "RubricCriterion",
    "RubricScore",
]
