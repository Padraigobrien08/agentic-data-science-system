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
from edgar_project.orchestration.schemas import (
    CODE_ORCH_UNSUPPORTED_GOAL,
    CODE_ORCH_VALIDATION,
    GoalPreferences,
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationError,
    OrchestrationInput,
    OrchestrationIntent,
    OrchestrationPlan,
    PlannedStep,
    PlanTemplateId,
    PlanningOutcome,
)

_MAX_TICKERS: Final[int] = 5


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
                "use_default_artifact_paths": True,
            },
            label=f"{TOOL_GENERATE_REPORT}:default_paths",
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
    return PlanningOutcome(ok=True, plan=plan, interpreted_goal=ig, errors=[])


def _unsupported_goal_failure() -> PlanningOutcome:
    return PlanningOutcome(
        ok=False,
        plan=None,
        interpreted_goal=None,
        errors=[
            OrchestrationError(
                code=CODE_ORCH_UNSUPPORTED_GOAL,
                message="Unsupported analysis_goal; no supported intent matched.",
                source_tool=None,
                mcp_error_code=None,
                detail=f"Supported intent ids: {supported_intents_summary()}.",
            )
        ],
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

        if request.intent_assistance is not None:
            prefs = request.intent_assistance.goal_preferences
        else:
            prefs = parse_goal_preferences(request.analysis_goal)
        interpretation = interpret_goal_intent(request.analysis_goal)
        if interpretation is None:
            return _unsupported_goal_failure()

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
