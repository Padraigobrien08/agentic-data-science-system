"""Typed schemas for deterministic benchmarks and evaluation results."""

from __future__ import annotations

from datetime import datetime
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
    orchestration_mocked = "orchestration_mocked"


class ValidationDegradationClass(str, Enum):
    """Why a validation case degraded, if it degraded at all."""

    none = "none"
    product_regression = "product_regression"
    upstream_sec_degraded = "upstream_sec_degraded"
    stale_source = "stale_source"
    policy_skipped = "policy_skipped"


class ValidationPolicy(BaseModel):
    """Policy contract for live or hybrid evaluation cases."""

    requires_explicit_live_opt_in: bool = False
    fair_access_policy: str | None = None
    allow_merge_blocking: bool = False
    normal_user_visible: bool = False
    freshness_window_seconds: int | None = Field(default=None, ge=0)


class ValidationObservation(BaseModel):
    """Observed freshness and source timing context for a case result."""

    observed_at: datetime | None = None
    source_observed_at: datetime | None = None
    source_age_seconds: float | None = None
    freshness_window_seconds: int | None = Field(default=None, ge=0)


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

    mode: InputMode = InputMode.fixture
    tickers: list[str] = Field(default_factory=list, description="Input tickers for pipeline scenarios")
    goal: str = Field(default="", description="Human-readable goal for the run")
    refresh: bool = Field(default=False, description="Bypass cache where supported")
    policy: ValidationPolicy | None = None
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
    orchestration_scenario: str | None = Field(
        default=None,
        description="Mock MCP scenario id when mode is orchestration_mocked (see orchestration_mocks.ORCHESTRATION_MOCK_SCENARIOS)",
    )
    notes: str = Field(default="")

    @model_validator(mode="after")
    def validate_live_policy(self) -> BenchmarkInput:
        if self.mode not in {InputMode.live, InputMode.hybrid}:
            return self
        if self.policy is None:
            raise ValueError("live and hybrid inputs require a policy block")
        if not self.policy.requires_explicit_live_opt_in:
            raise ValueError("live and hybrid policy must require explicit live opt-in")
        if not (self.policy.fair_access_policy or "").strip():
            raise ValueError("live and hybrid policy must declare fair_access_policy")
        if self.policy.allow_merge_blocking:
            raise ValueError("live and hybrid policy must remain non-merge-blocking")
        if self.policy.normal_user_visible:
            raise ValueError("live and hybrid policy must keep cases out of normal user-visible paths")
        if self.policy.freshness_window_seconds is None:
            raise ValueError("live and hybrid policy must declare freshness_window_seconds")
        return self


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


class ExpectedOrchestration(BaseModel):
    """Expectations for user-facing orchestration output (mocked MCP)."""

    expected_run_status: str = Field(
        ...,
        description="Terminal OrchestrationRunStatus value, e.g. success, partial_success, no_data, error",
    )
    required_artifact_keys: list[str] = Field(
        default_factory=list,
        description="Artifact role keys that must appear in OrchestrationOutput.artifact_paths with non-empty paths",
    )
    forbidden_artifact_keys: list[str] = Field(
        default_factory=list,
        description="Artifact keys that must be absent or empty",
    )
    final_report_path_non_null: bool = Field(
        default=False,
        description="If True, OrchestrationOutput.final_report_path must be set",
    )
    final_report_path_null: bool = Field(
        default=False,
        description="If True, final_report_path must be missing or empty",
    )
    tools_must_not_appear_in_call_sequence: list[str] = Field(
        default_factory=list,
        description="Tool names that must not appear in tool_call_sequence (e.g. build_panel on no_data path)",
    )
    warning_codes_must_include: list[str] = Field(
        default_factory=list,
        description="Every listed orchestration warning code must appear",
    )
    warning_codes_include_any: list[str] = Field(
        default_factory=list,
        description="At least one of these warning codes must appear",
    )
    max_errors: int | None = Field(
        default=None,
        description="If set, len(errors) must be <= this value",
    )
    min_errors: int | None = Field(
        default=None,
        description="If set, len(errors) must be >= this value",
    )


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

    # --- Analytical quality (deterministic; unified table is already sorted by the pipeline) ---
    top_n: int = Field(
        default=5,
        ge=1,
        description="Number of leading unified-finding rows used for top-slice containment checks",
    )
    top_must_include_metrics: list[str] = Field(
        default_factory=list,
        description="Each metric must appear in the metric column within the first top_n rows",
    )
    top_must_include_ciks: list[int] = Field(
        default_factory=list,
        description="Each CIK must appear in the first top_n rows",
    )
    min_rows_with_overlap_ge_threshold: int | None = Field(
        default=None,
        ge=0,
        description="Require at least this many rows with overlap_count >= overlap_ge_threshold",
    )
    overlap_ge_threshold: int = Field(
        default=2,
        ge=2,
        description="Threshold for overlap_count when counting rows (typically 2 = multi-source overlap)",
    )
    overlap_sources_one_row_must_include_substrings: list[str] = Field(
        default_factory=list,
        description="At least one row's overlap_sources must contain every substring (e.g. anomaly + trend_break)",
    )
    unified_caveat_substring_min_row_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Substring -> min row count in unified findings caveat_codes (e.g. sparse_history)",
    )
    anomaly_caveat_substring_min_row_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Substring -> min row count in anomalies.csv caveat_codes",
    )

    qualitative_expectations: list[str] = Field(
        default_factory=list,
        description="Optional rubric-like textual expectations",
    )
    notes: str = Field(default="")


class RegressionGolden(BaseModel):
    """Sparse JSON golden checked after a fixture run (subset comparison; see fixtures/regression/README)."""

    golden_json_path: str = Field(
        ...,
        min_length=1,
        description="Path to golden JSON, usually repo-relative to project root",
    )


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
    expected_orchestration: ExpectedOrchestration | None = Field(
        default=None,
        description="When using orchestration_mocked mode, validates OrchestrationOutput",
    )
    expected_metrics: dict[str, ValueRange] = Field(
        default_factory=dict,
        description="Metric name -> acceptable range",
    )
    regression_golden: RegressionGolden | None = Field(
        default=None,
        description="Optional compact regression snapshot (category counts, overlap, trust fingerprints)",
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
    degradation_class: ValidationDegradationClass = ValidationDegradationClass.none
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
    policy: ValidationPolicy | None = None
    observation: ValidationObservation | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseFailureBrief(BaseModel):
    """One-line context for a failed or errored benchmark case (for summaries and CI)."""

    case_id: str
    status: str
    reason_short: str = ""


class EvaluationSummary(BaseModel):
    """Aggregated summary for a suite-level evaluation run."""

    suite_id: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    error_cases: int = 0
    total_elapsed_seconds: float | None = Field(
        default=None,
        description="Sum of per-case elapsed_seconds (wall-ish CPU for the runner)",
    )
    failed_case_briefs: list[CaseFailureBrief] = Field(
        default_factory=list,
        description="Failed and error cases with shortened reasons",
    )
    generated_at: str | None = None
    notes: str = ""


class BenchmarkSuite(BaseModel):
    """A collection of benchmark cases plus output destinations."""

    suite_id: str = "default_suite"
    cases: list[BenchmarkCase] = Field(default_factory=list)
    output_dir: str = "data/evaluation"
    write_markdown_report: bool = Field(
        default=False,
        description="If True, write <suite_id>_report.md alongside JSON summaries",
    )
