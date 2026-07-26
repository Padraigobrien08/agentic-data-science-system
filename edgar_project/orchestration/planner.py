"""
Deterministic, rule-based planner (no LLM).

Maps :class:`OrchestrationInput` to a :class:`PlanningOutcome` containing an
:class:`OrchestrationPlan` and :class:`InterpretedGoal`, or structured
:class:`OrchestrationError` entries when inputs are invalid.

Plan **templates** (:mod:`edgar_project.orchestration.plan_templates`) define ordered phases,
required signals, peer/persistence/report contracts, and whether execution is ``granular``
or ``run_pipeline``.

**Purity (planning only)**

The planner is a pure planning component for a given :class:`OrchestrationInput`:

* **Does:** classify ``analysis_goal`` (deterministic rules), validate ticker count,
  choose default tickers when the input list is empty (from orchestration constants—
  aligned with Phase 1 ``config.DEFAULT_TICKERS``), emit :class:`PlannedStep` records
  whose ``tool_name`` / ``tool_input`` match the Phase 2 MCP tool contracts (names and
  shapes only—**no tool execution**).
* **Does not:** call MCP tools, perform SEC or network I/O, read/write artifact files,
  or import :mod:`edgar_project.mcp` / Phase 1 pipeline modules. It does not depend on
  executor runtime behavior beyond those documented input shapes.

**Boundary** — outputs :class:`PlanningOutcome` only. Execution is
:class:`~edgar_project.orchestration.executor.Executor`'s responsibility.
"""

from __future__ import annotations

from typing import Final

from edgar_project.orchestration.constants import (
    DEFAULT_TICKERS_WHEN_INPUT_EMPTY,
    TOOL_BUILD_PANEL,
    TOOL_COMPUTE_FEATURES,
    TOOL_DETECT_ANOMALIES,
    TOOL_FETCH_COMPANY_DATA,
    TOOL_GENERATE_REPORT,
    TOOL_RESOLVE_COMPANY,
    TOOL_RUN_PIPELINE,
)
from edgar_project.orchestration.goal_preferences import parse_goal_preferences
from edgar_project.orchestration.intent import (
    IntentInterpretation,
    interpret_goal_intent,
    supported_intents_summary,
)
from edgar_project.orchestration.plan_templates import (
    build_plan_template_snapshot,
    interpreted_goal_code_for,
    select_plan_template,
    short_description_for_code,
)
from edgar_project.orchestration.prompt_scope import extract_prompt_scope
from edgar_project.orchestration.schemas import (
    CODE_ORCH_UNSUPPORTED_GOAL,
    CODE_ORCH_VALIDATION,
    GoalPreferences,
    InterpretedGoal,
    MetricPriority,
    OrchestrationError,
    OrchestrationInput,
    OrchestrationPlan,
    PlannedStep,
    PlanningOutcome,
    PlanTemplateId,
)

_MAX_TICKERS: Final[int] = 5
_COMPARISON_CUES: Final[tuple[str, ...]] = (
    "compare",
    "comparison",
    "versus",
    " vs ",
    "relative to",
    "weaker",
    "stronger",
    "underperform",
    "outperform",
    "peer",
)
_METRIC_SUGGESTION_LABELS: Final[dict[MetricPriority, str]] = {
    MetricPriority.margins: "operating margin",
    MetricPriority.revenue_growth: "revenue growth",
    MetricPriority.cash_flow: "cash flow quality",
    MetricPriority.liquidity: "liquidity",
    MetricPriority.leverage: "leverage",
}


def _effective_tickers(request: OrchestrationInput) -> list[str]:
    """
    Normalized tickers, or orchestration defaults when the list is empty.

    Uses :data:`~edgar_project.orchestration.constants.DEFAULT_TICKERS_WHEN_INPUT_EMPTY`
    instead of loading the repo ``config`` module so planning avoids that module's
    import-time side effects and does not depend on the MCP adapter layer.
    """
    if request.tickers:
        return list(request.tickers)[:_MAX_TICKERS]
    return list(DEFAULT_TICKERS_WHEN_INPUT_EMPTY[:_MAX_TICKERS])


def _validation_failure(message: str, *, detail: str | None = None) -> PlanningOutcome:
    return PlanningOutcome(
        ok=False,
        plan=None,
        interpreted_goal=None,
        errors=[
            OrchestrationError(
                code=CODE_ORCH_VALIDATION,
                message=message,
                source_tool=None,
                mcp_error_code=None,
                detail=detail,
            )
        ],
        routing_source="deterministic",
    )


def _granular_plan(tickers: list[str], refresh: bool) -> OrchestrationPlan:
    """Template *anomaly_unusual_changes* — stepwise MCP through anomaly + report."""
    steps: list[PlannedStep] = []
    order = 0

    for t in tickers:
        steps.append(
            PlannedStep(
                order=order,
                tool_name=TOOL_RESOLVE_COMPANY,
                tool_input={"ticker": t},
                label=f"{TOOL_RESOLVE_COMPANY}:{t}",
            )
        )
        order += 1

    for t in tickers:
        steps.append(
            PlannedStep(
                order=order,
                tool_name=TOOL_FETCH_COMPANY_DATA,
                tool_input={"ticker": t, "refresh": refresh},
                label=f"{TOOL_FETCH_COMPANY_DATA}:{t}",
            )
        )
        order += 1

    steps.append(
        PlannedStep(
            order=order,
            tool_name=TOOL_BUILD_PANEL,
            tool_input={"tickers": list(tickers), "refresh": refresh},
            label=f"{TOOL_BUILD_PANEL}:{','.join(tickers)}",
        )
    )
    order += 1

    steps.append(
        PlannedStep(
            order=order,
            tool_name=TOOL_COMPUTE_FEATURES,
            tool_input={"tickers": list(tickers), "panel_csv_path": None},
            label=f"{TOOL_COMPUTE_FEATURES}:{','.join(tickers)}",
        )
    )
    order += 1

    steps.append(
        PlannedStep(
            order=order,
            tool_name=TOOL_DETECT_ANOMALIES,
            tool_input={"tickers": list(tickers), "features_csv_path": None},
            label=f"{TOOL_DETECT_ANOMALIES}:{','.join(tickers)}",
        )
    )
    order += 1

    steps.append(
        PlannedStep(
            order=order,
            tool_name=TOOL_GENERATE_REPORT,
            tool_input={
                "anomalies_csv_path": None,
                "features_csv_path": None,
                "use_default_artifact_paths": False,
            },
            label=f"{TOOL_GENERATE_REPORT}:explicit_paths",
        )
    )

    return OrchestrationPlan(steps=steps)


def _run_pipeline_plan(tickers: list[str], refresh: bool) -> OrchestrationPlan:
    """Templates with ``mcp_execution_profile == run_pipeline``."""
    return OrchestrationPlan(
        steps=[
            PlannedStep(
                order=0,
                tool_name=TOOL_RUN_PIPELINE,
                tool_input={"tickers": list(tickers), "refresh": refresh},
                label=f"{TOOL_RUN_PIPELINE}:{','.join(tickers)}",
            )
        ]
    )


def _plan_for_template(template_id: PlanTemplateId, tickers: list[str], refresh: bool) -> OrchestrationPlan:
    if template_id == PlanTemplateId.anomaly_unusual_changes:
        return _granular_plan(tickers, refresh)
    return _run_pipeline_plan(tickers, refresh)


def _human_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _metric_focus_text(prefs: GoalPreferences) -> str:
    labels = [
        _METRIC_SUGGESTION_LABELS[metric]
        for metric in prefs.priority_metrics[:3]
        if metric in _METRIC_SUGGESTION_LABELS
    ]
    if not labels:
        return "operating margin, revenue growth, and cash flow quality"
    return _human_join(labels)


def _single_company_suggestion(*, ticker: str, prefs: GoalPreferences) -> str:
    return (
        f"Analyze {ticker} over the last eight quarters for financial deterioration. "
        f"Focus on {_metric_focus_text(prefs)} and call out whether the pressure looks temporary or structural."
    )


def _anomaly_suggestion(*, ticker: str, prefs: GoalPreferences) -> str:
    return (
        f"Detect unusual quarterly changes in {ticker}. "
        f"Focus on {_metric_focus_text(prefs)} and explain whether the move looks one-off or persistent."
    )


def _comparison_suggestion(*, tickers: list[str], prefs: GoalPreferences) -> str:
    pair_text = _human_join(tickers[:2])
    return (
        f"Compare {pair_text} on {_metric_focus_text(prefs)} over the last eight quarters, "
        "and highlight which company shows weaker trends."
    )


def _scope_guidance_suggestion(*, effective_tickers: list[str], out_of_scope_tickers: list[str]) -> str:
    return (
        f"Your workspace scope is {_human_join(effective_tickers)}. "
        f"Either update the workspace to include {_human_join(out_of_scope_tickers)} "
        "or rewrite the question using the current symbols."
    )


def _build_rewrite_suggestions(
    *,
    analysis_goal: str,
    effective_tickers: list[str],
    out_of_scope_tickers: list[str],
    prefs: GoalPreferences,
) -> list[str]:
    suggestions: list[str] = []

    if effective_tickers and out_of_scope_tickers:
        suggestions.append(
            _scope_guidance_suggestion(
                effective_tickers=effective_tickers,
                out_of_scope_tickers=out_of_scope_tickers,
            )
        )

    goal_text = analysis_goal.lower()
    compare_shaped = any(cue in goal_text for cue in _COMPARISON_CUES)
    primary_ticker = effective_tickers[0] if effective_tickers else "the selected company"
    if len(effective_tickers) >= 2 and (compare_shaped or len(effective_tickers) == 2):
        suggestions.append(_comparison_suggestion(tickers=effective_tickers, prefs=prefs))
        suggestions.append(_single_company_suggestion(ticker=primary_ticker, prefs=prefs))
    else:
        suggestions.append(_single_company_suggestion(ticker=primary_ticker, prefs=prefs))
        suggestions.append(_anomaly_suggestion(ticker=primary_ticker, prefs=prefs))

    deduped: list[str] = []
    for suggestion in suggestions:
        if suggestion not in deduped:
            deduped.append(suggestion)
    return deduped[:3]


def _planning_success(
    *,
    tickers: list[str],
    refresh: bool,
    user_goal_text: str,
    interpretation: IntentInterpretation,
    prefs: GoalPreferences,
    template_id: PlanTemplateId,
    template_rules: list[str],
) -> PlanningOutcome:
    code = interpreted_goal_code_for(template_id, interpretation)
    plan = _plan_for_template(template_id, tickers, refresh)
    template_snap = build_plan_template_snapshot(template_id, template_rules)
    desc = short_description_for_code(code)
    ig = InterpretedGoal(
        code=code,
        intent=interpretation.intent,
        intent_rules_matched=list(interpretation.rules_matched),
        description=desc[:512],
        user_goal_text=user_goal_text,
        goal_preferences=prefs,
        plan_template=template_snap,
    )
    return PlanningOutcome(
        ok=True,
        plan=plan,
        interpreted_goal=ig,
        errors=[],
        routing_source="deterministic",
        effective_tickers=list(tickers),
    )


def _unsupported_goal_failure(
    *,
    analysis_goal: str,
    effective_tickers: list[str],
    out_of_scope_tickers: list[str],
    prefs: GoalPreferences,
    message: str = "Unsupported analysis_goal; no supported intent matched.",
    detail: str | None = None,
) -> PlanningOutcome:
    supported = f"Supported intent ids: {supported_intents_summary()}."
    combined_detail = supported if detail is None else f"{detail} {supported}"
    return PlanningOutcome(
        ok=False,
        plan=None,
        interpreted_goal=None,
        errors=[
            OrchestrationError(
                code=CODE_ORCH_UNSUPPORTED_GOAL,
                message=message,
                source_tool=None,
                mcp_error_code=None,
                detail=combined_detail,
            )
        ],
        routing_source="deterministic",
        effective_tickers=list(effective_tickers),
        out_of_scope_tickers=list(out_of_scope_tickers),
        rewrite_suggestions=_build_rewrite_suggestions(
            analysis_goal=analysis_goal,
            effective_tickers=effective_tickers,
            out_of_scope_tickers=out_of_scope_tickers,
            prefs=prefs,
        ),
    )


class Planner:
    """
    Rule-based plan builder: interpreted goal + ordered :class:`PlannedStep` list.

    See module docstring **Purity** — no MCP/SEC I/O; intent rules live in
    :mod:`edgar_project.orchestration.intent`; preferences in
    :mod:`edgar_project.orchestration.goal_preferences`; templates in
    :mod:`edgar_project.orchestration.plan_templates`.

    **Optional LLM intent assistance:** when ``OrchestrationInput.intent_assistance`` is set,
    goal preferences are taken from that payload instead of :func:`parse_goal_preferences`.
    That can rescue under-specified phrasing the keyword maps miss, but can also disagree
    with the deterministic intent layer—alignment findings in the critic should be trusted
    for audit when both paths are enabled.
    """

    def build_plan(self, request: OrchestrationInput) -> PlanningOutcome:
        """
        Produce a :class:`PlanningOutcome`: either ``ok=True`` with plan + interpreted goal,
        or ``ok=False`` with :class:`OrchestrationError` entries (e.g. invalid tickers).

        ``request`` must already satisfy :class:`OrchestrationInput` validation (coordinator
        or tests); this method does not re-validate field types beyond orchestration rules
        (e.g. ticker count).
        """
        if len(request.tickers) > _MAX_TICKERS:
            return _validation_failure(
                f"At most {_MAX_TICKERS} tickers allowed.",
                detail=f"Received {len(request.tickers)} symbols.",
            )

        tickers = _effective_tickers(request)
        if not tickers:
            return _validation_failure(
                "No tickers available after normalization.",
                detail="Provide at least one ticker or rely on default tickers when the list is empty.",
            )

        prompt_scope = extract_prompt_scope(request.analysis_goal, tickers)
        if request.intent_assistance is not None:
            prefs = request.intent_assistance.goal_preferences
        else:
            prefs = parse_goal_preferences(request.analysis_goal)
        if prompt_scope.out_of_scope_tickers:
            return _unsupported_goal_failure(
                analysis_goal=request.analysis_goal,
                effective_tickers=list(prompt_scope.effective_tickers),
                out_of_scope_tickers=list(prompt_scope.out_of_scope_tickers),
                prefs=prefs,
                message="Requested tickers fall outside the current workspace scope.",
                detail=(
                    "Out-of-scope symbols: "
                    f"{', '.join(prompt_scope.out_of_scope_tickers)}. "
                    f"Workspace scope: {', '.join(tickers)}. "
                    "The planner did not expand scope automatically."
                ),
            )
        tickers = list(prompt_scope.effective_tickers)

        interpretation = interpret_goal_intent(request.analysis_goal)
        if interpretation is None:
            return _unsupported_goal_failure(
                analysis_goal=request.analysis_goal,
                effective_tickers=list(tickers),
                out_of_scope_tickers=[],
                prefs=prefs,
            )

        user_text = request.analysis_goal.strip()
        template_id, template_rules = select_plan_template(prefs, interpretation)

        return _planning_success(
            tickers=tickers,
            refresh=request.refresh,
            user_goal_text=user_text,
            interpretation=interpretation,
            prefs=prefs,
            template_id=template_id,
            template_rules=template_rules,
        )

    def describe_plan(self, plan: OrchestrationPlan) -> str:
        """Human-readable summary for logging (one line per step)."""
        if not plan.steps:
            return "(empty plan)"
        lines = []
        for s in sorted(plan.steps, key=lambda x: x.order):
            lbl = f" [{s.label}]" if s.label else ""
            lines.append(f"{s.order}: {s.tool_name}{lbl}")
        return "\n".join(lines)

    def describe_outcome(self, outcome: PlanningOutcome) -> str:
        """Log-friendly single block for tests and structured logs."""
        if not outcome.ok:
            err = outcome.errors[0] if outcome.errors else None
            return f"planning_failed code={err.code if err else 'unknown'} message={err.message if err else ''}"
        assert outcome.plan is not None
        return self.describe_plan(outcome.plan)
