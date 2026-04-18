"""
Phase 3 orchestration contract — JSON-serializable request/response models.

All public types are designed for ``model_dump(mode="json")``. Prefer structured fields
over long prose; use :class:`OrchestrationError` / :class:`OrchestrationWarning` and
small summaries instead of opaque report text blobs.

MCP Phase 2 artifact role keys (for ``artifact_paths``) align with
``edgar_project.mcp.schemas`` (e.g. ``panel_csv``, ``features_csv``, ``data_quality_csv``,
``peer_signals_csv``, ``metric_coverage_*_csv``, ``metric_caveats_*_csv``,
``trend_break_signals_csv``, ``unified_findings_csv``,
``findings_summary_by_{company,metric,period}_csv``, ``manual_validation_csv``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, Field, JsonValue, field_validator
from edgar_project.orchestration.constants import (
    ORCH_STATUS_ERROR,
    ORCH_STATUS_NO_DATA,
    ORCH_STATUS_PARTIAL_SUCCESS,
    ORCH_STATUS_SUCCESS,
    STEP_STATUS_MCP_ERROR,
    STEP_STATUS_MCP_NO_DATA,
    STEP_STATUS_MCP_SUCCESS,
    STEP_STATUS_SKIPPED,
)

# JSON-safe primitive values for ``ToolCallStep.params`` (no opaque nested blobs).
ToolParamValue: TypeAlias = str | int | float | bool | None | list[str]

# Nested JSON-compatible structures (MCP envelopes, planner ``tool_input``, run ``context``).
# Prefer :class:`OrchestrationRunState` fields typed with ``JsonValue`` over ``dict[str, Any]``.
JsonDict: TypeAlias = dict[str, JsonValue]


class RunWorkspacePayload(BaseModel):
    """Serialized run workspace contract carried in ``ExecutionRequest.context['run_workspace']``."""

    model_config = {"extra": "forbid"}

    run_scoped_id: str = Field(..., description="Stable run identifier used in workspace folder naming.")
    root: str = Field(..., description="Workspace root directory for this run.")
    processed_dir: str = Field(..., description="Processed output directory for panel/features CSVs.")
    artifacts_dir: str = Field(..., description="Artifact output directory for anomalies/report/trust CSVs.")
    manual_validation_csv: str = Field(
        ...,
        description="Explicit shared validation input path; not copied into the run workspace.",
    )
    use_legacy_shared_paths: bool = Field(
        default=False,
        description="When true, processed/artifact paths point at the shared legacy Phase 1 roots.",
    )

# ---------------------------------------------------------------------------
# Entrypoint input (single orchestration API)
# ---------------------------------------------------------------------------


class OrchestrationInput(BaseModel):
    """
    Arguments accepted by the orchestration entrypoint.

    ``analysis_goal`` is a short user phrase; the planner maps it to
    :class:`InterpretedGoal` (structured, not free-form output).
    """

    tickers: list[str] = Field(
        default_factory=list,
        description="US equity symbols (1–5); empty may fall back to pipeline defaults.",
    )
    analysis_goal: str = Field(
        ...,
        min_length=1,
        description='User intent, e.g. "find unusual financial changes".',
    )
    refresh: bool = Field(
        default=False,
        description="When True, MCP fetch steps may bypass cache (Phase 2 semantics).",
    )
    intent_assistance: IntentAssistancePayload | None = Field(
        default=None,
        description=(
            "Optional validated LLM refinement of :class:`GoalPreferences` merged over rule-based parsing; "
            "does not select tools or plans directly — :class:`~edgar_project.orchestration.planner.Planner` "
            "still runs deterministic template selection."
        ),
    )

    @field_validator("tickers", mode="before")
    @classmethod
    def _strip_tickers(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return v
        return [str(t).strip().upper() for t in v if str(t).strip()]


# ---------------------------------------------------------------------------
# Rule-based NL intent (orchestration layer; not a chat agent)
# ---------------------------------------------------------------------------


class OrchestrationIntent(str, Enum):
    """High-level user intent from deterministic phrase / token rules."""

    anomaly_analysis = "anomaly_analysis"
    peer_report = "peer_report"
    full_pipeline_run = "full_pipeline_run"


# ---------------------------------------------------------------------------
# Structured analytical preferences (rule-based; persisted on InterpretedGoal)
# ---------------------------------------------------------------------------


class PrimaryAnalysisMode(str, Enum):
    """What the user is primarily trying to learn."""

    anomaly = "anomaly"
    trend = "trend"
    deterioration = "deterioration"
    peer_comparison = "peer_comparison"
    mixed = "mixed"


class PreferredSignalStyle(str, Enum):
    """Whether the user cares about one-off spikes vs sustained patterns."""

    one_off = "one_off"
    persistent = "persistent"
    mixed = "mixed"


class DirectionalFocus(str, Enum):
    """Emphasis on negative (weakness) vs positive (strength) moves."""

    negative = "negative"
    positive = "positive"
    both = "both"


class TimeFocus(str, Enum):
    """Horizon emphasis for the analysis."""

    recent_quarters = "recent_quarters"
    full_history = "full_history"
    mixed = "mixed"


class PeerRequirement(str, Enum):
    """How much peer-relative context the user expects."""

    required = "required"
    optional = "optional"
    none = "none"


class MetricPriority(str, Enum):
    """Ordered metric themes (planner uses order as priority)."""

    margins = "margins"
    revenue_growth = "revenue_growth"
    cash_flow = "cash_flow"
    liquidity = "liquidity"
    leverage = "leverage"


class PlanTemplateId(str, Enum):
    """
    Named plan templates (planner → MCP shape + reporting contract).

    Each template maps to one execution profile: granular steps vs single ``run_pipeline``.
    """

    anomaly_unusual_changes = "anomaly_unusual_changes"
    trend_deterioration = "trend_deterioration"
    peer_comparison = "peer_comparison"
    mixed_trend_and_anomaly = "mixed_trend_and_anomaly"


class PlanTemplateSnapshot(BaseModel):
    """
    Inspectable contract for a plan template — persisted on :class:`InterpretedGoal` for transparency.

    Values are rule-defined in :mod:`edgar_project.orchestration.plan_templates`.
    """

    template_id: PlanTemplateId
    ordered_phases: list[str] = Field(
        ...,
        description="Logical phases in execution order (human-readable).",
    )
    required_signals: list[str] = Field(
        default_factory=list,
        description="Artifact / analytic signals this template expects downstream to surface.",
    )
    peer_analysis_mandatory: bool = Field(
        ...,
        description="Whether peer-relative context is required for the narrative.",
    )
    persistence_filtering_required: bool = Field(
        ...,
        description="Whether sustained-pattern / multi-quarter filtering is part of the ask.",
    )
    report_emphasis: list[str] = Field(
        default_factory=list,
        description="What the written report should foreground.",
    )
    mcp_execution_profile: str = Field(
        ...,
        description="``granular`` (stepwise MCP) or ``run_pipeline`` (single Phase-1 bundle).",
    )
    template_rules_matched: list[str] = Field(
        default_factory=list,
        description="Planner rule ids that selected this template.",
    )
    schema_version: str = Field(default="1")


class GoalPreferences(BaseModel):
    """
    Rule-derived analytical preferences from ``analysis_goal`` text.

    Compact, JSON-serializable; optional on :class:`InterpretedGoal` for backward compatibility.
    """

    primary_analysis_mode: PrimaryAnalysisMode = Field(
        default=PrimaryAnalysisMode.mixed,
        description="Dominant analytical framing.",
    )
    preferred_signal_style: PreferredSignalStyle = Field(
        default=PreferredSignalStyle.mixed,
        description="One-off outliers vs persistent patterns.",
    )
    directional_focus: DirectionalFocus = Field(
        default=DirectionalFocus.both,
        description="Negative vs positive emphasis.",
    )
    priority_metrics: list[MetricPriority] = Field(
        default_factory=list,
        description="User-stated metric themes in priority order (max 5).",
    )
    time_focus: TimeFocus = Field(
        default=TimeFocus.mixed,
        description="Recent quarters vs long history.",
    )
    peer_requirement: PeerRequirement = Field(
        default=PeerRequirement.optional,
        description="Whether peer-relative analysis is required.",
    )
    preference_rules_matched: list[str] = Field(
        default_factory=list,
        description="Stable ids for which preference rules fired (audit).",
    )
    schema_version: str = Field(default="1", description="Bump when fields or enums change.")


class IntentAssistancePayload(BaseModel):
    """
    Audit bundle for optional LLM-assisted preference extraction.

    Only :class:`GoalPreferences` is consumed by the planner; LLM never emits tool names or step lists.
    """

    model_config = {"extra": "forbid"}

    goal_preferences: GoalPreferences = Field(
        ...,
        description="Merged preferences (rules baseline + validated LLM patch).",
    )
    validation_status: Literal["llm_validated"] = Field(
        default="llm_validated",
        description="Set when JSON passed schema validation and merge completed.",
    )
    model_call_id: str = Field(..., description="Recorded chat completion row id.")
    prompt_id: str = Field(..., description="Registry id, e.g. edgar.agent.intent_preferences_assistant.")
    prompt_version: str = Field(..., description="Prompt file / template version.")


# ---------------------------------------------------------------------------
# Interpreted goal (structured; replaces opaque goal blobs)
# ---------------------------------------------------------------------------


class InterpretedGoalCode(str, Enum):
    """
    Canonical analysis templates produced from ``analysis_goal`` text.

    The planner maps natural-language goals to exactly one code.
    """

    anomaly_unusual_changes = "anomaly_unusual_changes"
    """Granular MCP path — z-score / point anomaly screen."""

    anomaly_for_companies = "anomaly_for_companies"
    """e.g. run anomaly analysis for these companies."""

    peer_comparison = "peer_comparison"
    """Peer / compare goals — ``run_pipeline`` with peer-forward reporting."""

    full_pipeline = "full_pipeline"
    """User explicitly asked to run the full MCP pipeline (single ``run_pipeline`` step)."""

    trend_deterioration = "trend_deterioration"
    """Sustained weakness / trend breaks — ``run_pipeline`` with trend-first reporting."""

    mixed_trend_and_anomaly = "mixed_trend_and_anomaly"
    """Both episodic outliers and rolling trends — ``run_pipeline``."""

    resolve_only = "resolve_only"
    """Ticker → CIK / name only."""

    fetch_raw = "fetch_raw"
    """Cache SEC JSON only."""

    planning_failed = "planning_failed"
    """Validation or intent failed before any MCP step; no ``intent`` on :class:`InterpretedGoal`."""


class InterpretedGoal(BaseModel):
    """Machine-readable goal after interpretation (provenance for *why* tools ran)."""

    code: InterpretedGoalCode
    intent: OrchestrationIntent | None = Field(
        default=None,
        description="Rule-based NL intent when planning succeeded (see ``intent.py``).",
    )
    intent_rules_matched: list[str] = Field(
        default_factory=list,
        description="Stable rule ids that selected ``intent`` (transparent audit trail).",
    )
    description: str = Field(
        ...,
        max_length=512,
        description="Short canonical label (not the full user essay).",
    )
    user_goal_text: str = Field(
        ...,
        description="Echo of ``OrchestrationInput.analysis_goal`` for audit.",
    )
    goal_preferences: GoalPreferences | None = Field(
        default=None,
        description="Structured preferences when the planner filled them (rule-based v1).",
    )
    plan_template: PlanTemplateSnapshot | None = Field(
        default=None,
        description="Named plan template contract (phases, signals, report emphasis).",
    )


# ---------------------------------------------------------------------------
# Terminal run status (orchestration-level, distinct from per-tool MCP status)
# ---------------------------------------------------------------------------


class OrchestrationRunStatus(str, Enum):
    """
    Outcome of the whole orchestration.

    * ``success`` — all planned steps succeeded with MCP ``success`` where required.
    * ``partial_success`` — run stopped early or some steps no_data/error while others ok.
    * ``no_data`` — completed without usable data (e.g. MCP ``no_data`` on critical path).
    * ``error`` — failed (validation, fatal MCP error, or abort).
    """

    success = ORCH_STATUS_SUCCESS
    partial_success = ORCH_STATUS_PARTIAL_SUCCESS
    no_data = ORCH_STATUS_NO_DATA
    error = ORCH_STATUS_ERROR


# ---------------------------------------------------------------------------
# Companies & tool sequence (provenance)
# ---------------------------------------------------------------------------


class ResolvedCompany(BaseModel):
    """One issuer after ticker resolution (from MCP ``resolve_company`` / panel CIKs)."""

    ticker: str
    cik: int
    company_name: str | None = None


class ToolCallStep(BaseModel):
    """One planned or executed tool invocation in order."""

    order: int = Field(..., ge=0)
    tool_name: str = Field(
        ...,
        description="MCP tool name, e.g. run_pipeline, resolve_company.",
    )
    params: dict[str, ToolParamValue] = Field(
        default_factory=dict,
        description="JSON-safe arguments only (strings, numbers, bools, string lists).",
    )


class StepStatusEntry(BaseModel):
    """
    One planned step with execution outcome for the final response.

    ``mcp_status`` is the MCP envelope status when the tool ran
    (``success`` / ``no_data`` / ``error``); ``skipped`` means the tool was not
    invoked (orchestration stopped or short-circuited earlier).
    """

    order: int = Field(..., ge=0)
    tool_name: str
    label: str = Field(default="", description="Planner label, e.g. resolve_company:AAPL.")
    mcp_status: str = Field(
        ...,
        description=(
            "MCP status: "
            f"{STEP_STATUS_MCP_SUCCESS} | {STEP_STATUS_MCP_NO_DATA} | {STEP_STATUS_MCP_ERROR}, "
            f"or orchestration '{STEP_STATUS_SKIPPED}'."
        ),
    )
    detail: str | None = Field(
        default=None,
        description="Short reason for skipped steps or extra context.",
    )


class ToolResultSummary(BaseModel):
    """
    Compact summary for one tool call (avoid storing full MCP ``data`` trees here).

    Populate from ``ToolResponseEnvelope`` in the executor when wiring MCP.
    """

    order: int = Field(..., ge=0)
    tool_name: str
    mcp_status: str = Field(
        ...,
        description=(
            "MCP envelope status: "
            f"{STEP_STATUS_MCP_SUCCESS} | {STEP_STATUS_MCP_NO_DATA} | {STEP_STATUS_MCP_ERROR}."
        ),
    )
    panel_row_count: int | None = None
    feature_row_count: int | None = None
    anomaly_count: int | None = None
    report_character_count: int | None = None
    ciks_observed: list[int] = Field(default_factory=list)
    artifact_paths: dict[str, str] = Field(
        default_factory=dict,
        description="Subset of MCP ``artifacts`` map for this step (role → path).",
    )
    provenance_keys: list[str] = Field(
        default_factory=list,
        description="Keys taken from MCP ``data`` for audit (e.g. input_tickers, ciks).",
    )


# ---------------------------------------------------------------------------
# Errors & warnings (structured)
# ---------------------------------------------------------------------------


class OrchestrationError(BaseModel):
    """Fatal or step-level error exposed to the client."""

    code: str = Field(..., description="Stable code, e.g. ORCH_VALIDATION, MCP_UNKNOWN_TICKER.")
    message: str
    source_tool: str | None = Field(
        default=None,
        description="MCP tool name if error originated in a tool step.",
    )
    mcp_error_code: str | None = Field(
        default=None,
        description="Phase 2 ``errors[].code`` when proxied from MCP.",
    )
    detail: str | None = Field(
        default=None,
        description="Short diagnostic; avoid large stack dumps in production responses.",
    )


class OrchestrationWarning(BaseModel):
    """Non-fatal issue (e.g. partial step, degraded path)."""

    code: str
    message: str
    source_tool: str | None = None
    detail: str | None = None


# ---------------------------------------------------------------------------
# Planner/executor internals (unchanged semantics; kept for wiring)
# ---------------------------------------------------------------------------


class PlannedStep(BaseModel):
    """One step in an execution plan (before MCP)."""

    tool_name: str = Field(
        ...,
        description="MCP tool name (matches ``edgar_project.mcp.server`` registration).",
    )
    tool_input: JsonDict = Field(
        default_factory=dict,
        description="Keyword payload to build MCP Pydantic inputs (JSON-serializable only).",
    )
    order: int = Field(..., ge=0)
    label: str = Field(
        default="",
        description="Short id for logs/tests, e.g. resolve_company:AAPL.",
    )


class OrchestrationPlan(BaseModel):
    """Ordered steps from the planner."""

    steps: list[PlannedStep] = Field(default_factory=list)


# Stable orchestration-layer error / warning codes (planning + execution).
CODE_ORCH_VALIDATION = "ORCH_VALIDATION"
CODE_ORCH_UNSUPPORTED_GOAL = "ORCH_UNSUPPORTED_GOAL"
CODE_ORCH_DISPATCH = "ORCH_DISPATCH"
CODE_ORCH_ALL_RESOLVE_FAILED = "ORCH_ALL_RESOLVE_FAILED"
CODE_ORCH_PARTIAL_RESOLVE = "ORCH_PARTIAL_RESOLVE"
CODE_ORCH_FETCH_ALL_NO_DATA = "ORCH_FETCH_ALL_NO_DATA"
CODE_ORCH_FETCH_TICKER_NO_DATA = "ORCH_FETCH_TICKER_NO_DATA"
CODE_ORCH_BUILD_PANEL_NO_DATA = "ORCH_BUILD_PANEL_NO_DATA"
CODE_ORCH_COMPUTE_FEATURES_FAILED = "ORCH_COMPUTE_FEATURES_FAILED"
CODE_ORCH_WARN_ZERO_ANOMALIES = "ORCH_WARN_ZERO_ANOMALIES"
CODE_ORCH_REPORT_FAILED = "ORCH_REPORT_FAILED"
CODE_ORCH_DOWNSTREAM_SKIPPED = "ORCH_DOWNSTREAM_SKIPPED"
CODE_ORCH_RESOLVE_TICKER_FAILED = "ORCH_RESOLVE_TICKER_FAILED"


class PlanningOutcome(BaseModel):
    """
    Result of rule-based planning: either a plan + interpreted goal, or structured errors.

    Use ``model_dump(mode="json")`` for logs and tests.
    """

    ok: bool
    plan: OrchestrationPlan | None = None
    interpreted_goal: InterpretedGoal | None = None
    errors: list[OrchestrationError] = Field(default_factory=list)
    routing_source: Literal["deterministic"] = Field(
        default="deterministic",
        description="Routing provenance for Phase 13 preview and guidance surfaces.",
    )
    effective_tickers: list[str] = Field(
        default_factory=list,
        description="Ticker scope the deterministic planner actually used for routing.",
    )
    out_of_scope_tickers: list[str] = Field(
        default_factory=list,
        description="Prompt-named symbols outside the current workspace scope.",
    )
    rewrite_suggestions: list[str] = Field(
        default_factory=list,
        description="Deterministic rewrite suggestions for unsupported prompts.",
    )

    model_config = {"extra": "forbid"}


class StepRecord(BaseModel):
    """One executed step; ``envelope`` is MCP JSON (``model_dump(mode='json')``-compatible)."""

    tool_name: str
    order: int
    envelope: JsonDict = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ---------------------------------------------------------------------------
# Final orchestration output (single structured result)
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrchestrationOutput(BaseModel):
    """
    Single return value from the orchestration entrypoint.

    Serialize with ``model_dump(mode="json")`` for agents and APIs.
    """

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: OrchestrationRunStatus
    message: str = Field(
        ...,
        description="One-line summary (not a full narrative report).",
    )
    final_summary: str = Field(
        default="",
        description="Concise end-user line: status, outcome, executed tool chain (set by run_analysis_agent).",
    )
    interpreted_goal: InterpretedGoal
    resolved_companies: list[ResolvedCompany] = Field(default_factory=list)
    tool_call_sequence: list[ToolCallStep] = Field(
        default_factory=list,
        description="Ordered MCP tools actually executed (may be shorter than the plan if stopped early).",
    )
    tool_results_summary: list[ToolResultSummary] = Field(
        default_factory=list,
        description="Per-tool compact outcomes aligned with MCP envelopes.",
    )
    step_statuses: list[StepStatusEntry] = Field(
        default_factory=list,
        description="Planned steps in order with MCP or skipped status for each.",
    )
    artifact_paths: dict[str, str] = Field(
        default_factory=dict,
        description="Merged artifact paths (MCP role key → filesystem path).",
    )
    final_report_path: str | None = Field(
        default=None,
        description="Path to ``report_md`` when a report artifact was produced.",
    )
    errors: list[OrchestrationError] = Field(default_factory=list)
    warnings: list[OrchestrationWarning] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)

    model_config = {"extra": "forbid"}
