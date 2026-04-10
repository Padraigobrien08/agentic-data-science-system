"""Typed schemas for deterministic benchmarks and evaluation results."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class EvaluationStatus(str, Enum):
    """Lifecycle status for a single benchmark/evaluation run."""

    pending = "pending"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    error = "error"


class InputMode(str, Enum):
    """How a benchmark case should source input data."""

    fixture = "fixture"
    live = "live"
    hybrid = "hybrid"


class ValueRange(BaseModel):
    """Inclusive range for count- or metric-style expectations."""

    minimum: float | None = Field(default=None)
    maximum: float | None = Field(default=None)

    @model_validator(mode="after")
    def validate_bounds(self) -> ValueRange:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum cannot be greater than maximum")
        return self


class BenchmarkInput(BaseModel):
    """
    Input contract for benchmark execution.

    Supports fixture-based and live-pipeline scenarios.
    """

    mode: InputMode = InputMode.live
    tickers: list[str] = Field(default_factory=list, description="Input tickers for pipeline scenarios")
    goal: str = Field(default="", description="Human-readable goal for the run")
    refresh: bool = Field(default=False, description="Bypass cache where supported")
    peer_set_label: str | None = Field(
        default=None,
        description="Optional named peer-set scenario label",
    )
    fixture_id: str | None = Field(
        default=None,
        description="Stable fixture identifier (e.g. deterioration_qoq_v1)",
    )
    fixture_paths: dict[str, str] = Field(
        default_factory=dict,
        description="Logical fixture key -> path for controlled cases",
    )
    notes: str = Field(default="")


class ExpectedArtifactItem(BaseModel):
    """Expectation for one logical artifact key."""

    key: str = Field(description="Logical artifact key, e.g. report_md, anomalies_csv")
    required: bool = Field(default=True, description="Whether this artifact must exist")
    expected_status: str | None = Field(
        default=None,
        description="Optional artifact status hint, e.g. produced, reused, skipped",
    )
    min_rows: int | None = Field(default=None, ge=0)
    max_rows: int | None = Field(default=None, ge=0)
    must_contain: list[str] = Field(
        default_factory=list,
        description="Optional required substrings for text artifacts",
    )
    notes: str = Field(default="")

    @model_validator(mode="after")
    def validate_row_bounds(self) -> ExpectedArtifactItem:
        if self.min_rows is not None and self.max_rows is not None and self.min_rows > self.max_rows:
            raise ValueError("min_rows cannot be greater than max_rows")
        return self


class ExpectedArtifacts(BaseModel):
    """Collection-level artifact expectations for a benchmark case."""

    expected_statuses: list[EvaluationStatus] = Field(
        default_factory=lambda: [EvaluationStatus.passed],
        description="Allowed run-level statuses for this case",
    )
    enforce_schema: bool = Field(
        default=True,
        description="If True, validate known CSV column sets for produced artifacts (lightweight header check)",
    )
    schema_exempt_keys: list[str] = Field(
        default_factory=list,
        description="Logical artifact keys to skip for schema validation (rare escape hatch)",
    )
    items: list[ExpectedArtifactItem] = Field(default_factory=list)
    required_keys: list[str] = Field(
        default_factory=list,
        description="Shorthand required artifact keys in addition to item-level requirements",
    )
    qualitative_checks: list[str] = Field(
        default_factory=list,
        description="Human-readable non-numeric checks for artifact quality",
    )
    notes: str = Field(default="")


class ExpectedFindings(BaseModel):
    """Deterministic expectations for unified findings content."""

    required_types: list[str] = Field(
        default_factory=list,
        description="Expected finding types, e.g. anomaly, trend_break",
    )
    required_categories: list[str] = Field(
        default_factory=list,
        description="Expected semantic categories present in findings",
    )
    total_count: ValueRange | None = Field(default=None)
    by_type_min_counts: dict[str, int] = Field(default_factory=dict)
    by_category_min_counts: dict[str, int] = Field(default_factory=dict)
    qualitative_expectations: list[str] = Field(
        default_factory=list,
        description="Optional rubric-like textual expectations",
    )
    notes: str = Field(default="")


class BenchmarkCase(BaseModel):
    """Declarative benchmark case consumed by evaluation runners."""

    case_id: str = Field(description="Stable case identifier, e.g. smoke_aapl_msft")
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list, description="Routing labels for CI and local runs")
    input: BenchmarkInput = Field(default_factory=BenchmarkInput)
    fixtures: dict[str, str] = Field(
        default_factory=dict,
        description="Optional fixture references for inspectable benchmark assets",
    )

    # Evaluation controls
    max_runtime_seconds: float | None = Field(
        default=None,
        description="Optional soft runtime budget for deterministic benchmark checks",
    )
    expected_artifacts: ExpectedArtifacts = Field(default_factory=ExpectedArtifacts)
    expected_findings: ExpectedFindings | None = Field(default=None)
    expected_metrics: dict[str, ValueRange] = Field(
        default_factory=dict,
        description="Metric name -> acceptable range",
    )
    qualitative_expectations: list[str] = Field(
        default_factory=list,
        description="Case-level non-numeric expectations",
    )
    notes: str = Field(default="")

    @model_validator(mode="after")
    def migrate_legacy_fields(self) -> BenchmarkCase:
        """
        Backward compatibility hook.

        If legacy top-level tickers/refresh are passed from old manifests,
        they should be mapped by the caller before validation.
        """

        return self


class RubricScore(BaseModel):
    """Scoring summary for non-LLM deterministic rubric checks."""

    rubric_id: str
    total_score: float = 0.0
    max_score: float = 0.0
    passed: bool = False
    details: dict[str, float] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Result contract emitted for one benchmark case."""

    case_id: str
    status: EvaluationStatus = EvaluationStatus.pending
    elapsed_seconds: float | None = None
    message: str = ""
    run_goal: str = Field(default="", description="Copied from benchmark input for traceability")
    artifacts: dict[str, str] = Field(default_factory=dict, description="Logical artifact key -> path")
    finding_counts: dict[str, int] = Field(default_factory=dict)
    checks: dict[str, bool] = Field(
        default_factory=dict,
        description="Deterministic check outcomes",
    )
    qualitative_notes: list[str] = Field(
        default_factory=list,
        description="Evaluator notes for qualitative expectations",
    )
    rubric_score: RubricScore | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationSummary(BaseModel):
    """Aggregated summary for a suite-level evaluation run."""

    suite_id: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    error_cases: int = 0
    generated_at: str | None = None
    notes: str = ""


class BenchmarkSuite(BaseModel):
    """A collection of benchmark cases plus output destinations."""

    suite_id: str = "default_suite"
    cases: list[BenchmarkCase] = Field(default_factory=list)
    output_dir: str = "data/evaluation"
