"""Evaluation and benchmark scaffolding for ``edgar_project``."""

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
    "Rubric",
    "RubricCriterion",
    "RubricScore",
]
