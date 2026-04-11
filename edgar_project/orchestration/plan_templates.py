"""
Named plan templates: explicit phases, signal contracts, and MCP execution profiles.

Templates are **inspectable** (Pydantic snapshots on :class:`~edgar_project.orchestration.schemas.InterpretedGoal`)
and **testable** (pure selection + builders — no I/O).

Execution remains either:

* ``granular`` — resolve → fetch → … → detect_anomalies → generate_report
* ``run_pipeline`` — single MCP tool that runs Phase-1 bundle (trend breaks, unified findings, …)
"""

from __future__ import annotations

from typing import Final, Literal

from edgar_project.orchestration.goal_preferences import prefer_run_pipeline_over_granular
from edgar_project.orchestration.intent import IntentInterpretation
from edgar_project.orchestration.schemas import (
    GoalPreferences,
    InterpretedGoalCode,
    OrchestrationIntent,
    PlanTemplateId,
    PlanTemplateSnapshot,
    PrimaryAnalysisMode,
)

McpExecutionProfile = Literal["granular", "run_pipeline"]

# --- registry: one snapshot per PlanTemplateId --------------------------------

_SNAPSHOTS: Final[dict[PlanTemplateId, PlanTemplateSnapshot]] = {
    PlanTemplateId.anomaly_unusual_changes: PlanTemplateSnapshot(
        template_id=PlanTemplateId.anomaly_unusual_changes,
        ordered_phases=[
            "resolve_tickers",
            "fetch_company_facts",
            "build_panel",
            "compute_features",
            "detect_anomalies",
            "generate_report",
        ],
        required_signals=[
            "panel_time_series",
            "feature_table",
            "anomaly_flags_and_zscores",
        ],
        peer_analysis_mandatory=False,
        persistence_filtering_required=False,
        report_emphasis=[
            "Point-in-time outliers and |z| highlights.",
            "Per-metric tables; sparse-history caveats where applicable.",
        ],
        mcp_execution_profile="granular",
        template_rules_matched=[],
    ),
    PlanTemplateId.trend_deterioration: PlanTemplateSnapshot(
        template_id=PlanTemplateId.trend_deterioration,
        ordered_phases=[
            "run_full_phase1_pipeline",
            "emit_trend_breaks",
            "emit_unified_findings",
            "emit_metric_coverage_and_caveats",
            "optional_peer_signals_for_context",
            "generate_report",
        ],
        required_signals=[
            "trend_break_signals",
            "unified_findings",
            "deterioration_focus",
            "metric_coverage_summary",
            "metric_caveats",
            "anomaly_table",
        ],
        peer_analysis_mandatory=False,
        persistence_filtering_required=True,
        report_emphasis=[
            "Trend analysis and deterioration patterns (multi-quarter / sustained moves).",
            "Persistence filtering: down-rank one-off spikes when user asked for sustained weakness.",
            "Negative directional emphasis when goal language is stress / decline oriented.",
            "Peer comparison as supporting context, not sole basis for conclusions.",
        ],
        mcp_execution_profile="run_pipeline",
        template_rules_matched=[],
    ),
    PlanTemplateId.peer_comparison: PlanTemplateSnapshot(
        template_id=PlanTemplateId.peer_comparison,
        ordered_phases=[
            "run_full_phase1_pipeline",
            "peer_signals",
            "cross_sectional_features",
            "anomaly_and_relative_scores",
            "generate_report",
        ],
        required_signals=[
            "peer_signals_table",
            "panel_and_features",
            "anomalies_or_relative_alerts",
        ],
        peer_analysis_mandatory=True,
        persistence_filtering_required=False,
        report_emphasis=[
            "Cross-sectional ranking vs peers or industry benchmarks.",
            "Relative cheap/expensive or strong/weak vs peer set.",
        ],
        mcp_execution_profile="run_pipeline",
        template_rules_matched=[],
    ),
    PlanTemplateId.mixed_trend_and_anomaly: PlanTemplateSnapshot(
        template_id=PlanTemplateId.mixed_trend_and_anomaly,
        ordered_phases=[
            "run_full_phase1_pipeline",
            "trend_and_break_detection",
            "unified_findings_combined_with_point_anomalies",
            "optional_peer_context",
            "generate_report",
        ],
        required_signals=[
            "trend_break_signals",
            "unified_findings",
            "anomaly_flags",
            "metric_caveats",
        ],
        peer_analysis_mandatory=False,
        persistence_filtering_required=True,
        report_emphasis=[
            "Both episodic outliers (|z|, one-off quarters) and rolling / persistent trends.",
            "Clearly label which rows are spike-driven vs trend-driven.",
        ],
        mcp_execution_profile="run_pipeline",
        template_rules_matched=[],
    ),
}


def get_plan_template_snapshot(template_id: PlanTemplateId) -> PlanTemplateSnapshot:
    """Return the canonical snapshot for ``template_id`` (rules applied separately)."""
    base = _SNAPSHOTS[template_id]
    return base.model_copy(update={"template_rules_matched": list(base.template_rules_matched)})


def select_plan_template(
    prefs: GoalPreferences,
    interpretation: IntentInterpretation,
) -> tuple[PlanTemplateId, list[str]]:
    """
    Map preferences + coarse intent to a :class:`PlanTemplateId`.

    **Coupling (audit):** ``interpretation.intent`` is computed first in ``intent.py``
    (small fixed grammar). ``prefs`` come from ``parse_goal_preferences`` on the same
    user text. ``peer_report`` and ``full_pipeline_run`` short-circuit to fixed templates;
    for ``anomaly_analysis``, :func:`prefer_run_pipeline_over_granular` gates granular
    vs ``run_pipeline``, then ``primary_analysis_mode`` chooses among the remaining ids.
    Mismatches between intent and preference layers are surfaced by the critic's
    deterministic alignment pass, not reconciled here.

    Returns ``(template_id, template_rule_ids)`` for audit on the snapshot.
    """
    rules: list[str] = []

    if interpretation.intent == OrchestrationIntent.full_pipeline_run:
        rules.append("select:explicit_full_pipeline_intent")
        return PlanTemplateId.trend_deterioration, rules

    if interpretation.intent == OrchestrationIntent.peer_report:
        rules.append("select:peer_report_intent")
        return PlanTemplateId.peer_comparison, rules

    assert interpretation.intent == OrchestrationIntent.anomaly_analysis

    if not prefer_run_pipeline_over_granular(prefs):
        rules.append("select:anomaly_screen_granular")
        return PlanTemplateId.anomaly_unusual_changes, rules

    m = prefs.primary_analysis_mode
    if m == PrimaryAnalysisMode.mixed:
        rules.append("select:mixed_primary_mode")
        return PlanTemplateId.mixed_trend_and_anomaly, rules
    if m == PrimaryAnalysisMode.peer_comparison:
        rules.append("select:peer_comparison_primary")
        return PlanTemplateId.peer_comparison, rules
    if m in (PrimaryAnalysisMode.deterioration, PrimaryAnalysisMode.trend):
        rules.append("select:trend_or_deterioration_primary")
        return PlanTemplateId.trend_deterioration, rules
    if m == PrimaryAnalysisMode.anomaly:
        rules.append("select:persistent_negative_on_anomaly_axis")
        return PlanTemplateId.mixed_trend_and_anomaly, rules

    rules.append("select:fallback_mixed_pipeline")
    return PlanTemplateId.mixed_trend_and_anomaly, rules


def interpreted_goal_code_for(
    template_id: PlanTemplateId,
    interpretation: IntentInterpretation,
) -> InterpretedGoalCode:
    """Stable :class:`InterpretedGoalCode` aligned with the chosen template and NL intent."""
    if interpretation.intent == OrchestrationIntent.full_pipeline_run:
        return InterpretedGoalCode.full_pipeline
    mapping: dict[PlanTemplateId, InterpretedGoalCode] = {
        PlanTemplateId.anomaly_unusual_changes: InterpretedGoalCode.anomaly_unusual_changes,
        PlanTemplateId.trend_deterioration: InterpretedGoalCode.trend_deterioration,
        PlanTemplateId.peer_comparison: InterpretedGoalCode.peer_comparison,
        PlanTemplateId.mixed_trend_and_anomaly: InterpretedGoalCode.mixed_trend_and_anomaly,
    }
    return mapping[template_id]


def short_description_for_code(code: InterpretedGoalCode) -> str:
    """Planner-facing one-line description."""
    return {
        InterpretedGoalCode.anomaly_unusual_changes: (
            "Template anomaly_unusual_changes: granular MCP — z-score / point anomaly screen."
        ),
        InterpretedGoalCode.trend_deterioration: (
            "Template trend_deterioration: run_pipeline — trend breaks, unified findings, persistence emphasis."
        ),
        InterpretedGoalCode.peer_comparison: (
            "Template peer_comparison: run_pipeline — peer-relative signals required in narrative."
        ),
        InterpretedGoalCode.mixed_trend_and_anomaly: (
            "Template mixed_trend_and_anomaly: run_pipeline — combine spike and trend evidence."
        ),
        InterpretedGoalCode.full_pipeline: (
            "Explicit full-pipeline intent: single run_pipeline step."
        ),
    }.get(
        code,
        code.value,
    )


def build_plan_template_snapshot(
    template_id: PlanTemplateId,
    template_rules_matched: list[str],
) -> PlanTemplateSnapshot:
    """Attach selection rules to the canonical snapshot for persistence."""
    snap = get_plan_template_snapshot(template_id)
    return snap.model_copy(
        update={
            "template_rules_matched": sorted(set(template_rules_matched)),
        }
    )
