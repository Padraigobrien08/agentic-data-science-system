"""
Deterministic, rule-based planner (no LLM).

Maps :class:`OrchestrationInput` to a :class:`PlanningOutcome` containing an
:class:`OrchestrationPlan` and :class:`InterpretedGoal`, or structured
:class:`OrchestrationError` entries when inputs are invalid.

Natural-language goals are classified by :mod:`edgar_project.orchestration.intent`
into :class:`OrchestrationIntent` before choosing a plan shape.

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
from edgar_project.orchestration.intent import (
    IntentInterpretation,
    interpret_goal_intent,
    supported_intents_summary,
)
from edgar_project.orchestration.schemas import (
    CODE_ORCH_UNSUPPORTED_GOAL,
    CODE_ORCH_VALIDATION,
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationError,
    OrchestrationInput,
    OrchestrationIntent,
    OrchestrationPlan,
    PlannedStep,
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


def _success_granular_outcome(
    tickers: list[str],
    refresh: bool,
    user_goal_text: str,
    interpretation: IntentInterpretation,
    *,
    code: InterpretedGoalCode,
    description: str,
) -> PlanningOutcome:
    """Shared granular plan + :class:`InterpretedGoal` for anomaly and peer intents."""
    plan = _granular_plan(tickers, refresh)
    ig = InterpretedGoal(
        code=code,
        intent=interpretation.intent,
        intent_rules_matched=list(interpretation.rules_matched),
        description=description,
        user_goal_text=user_goal_text,
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


def _granular_plan(tickers: list[str], refresh: bool) -> OrchestrationPlan:
    """
    Standard sequence: resolve → fetch per ticker, then panel → features → anomalies → report.

    Later, branching (skip fetch if cache fresh) can insert conditions here without
    changing the outer :class:`PlanningOutcome` shape.
    """
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


class Planner:
    """
    Rule-based plan builder: interpreted goal + ordered :class:`PlannedStep` list.

    See module docstring **Purity** — no MCP/SEC I/O; intent rules live in
    :mod:`edgar_project.orchestration.intent`.
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

        interpretation = interpret_goal_intent(request.analysis_goal)
        if interpretation is None:
            return _unsupported_goal_failure()

        user_text = request.analysis_goal.strip()

        if interpretation.intent == OrchestrationIntent.anomaly_analysis:
            return _success_granular_outcome(
                tickers,
                request.refresh,
                user_text,
                interpretation,
                code=InterpretedGoalCode.anomaly_unusual_changes,
                description="Anomaly-style path: resolve → fetch → panel → features → anomalies → report.",
            )

        if interpretation.intent == OrchestrationIntent.peer_report:
            return _success_granular_outcome(
                tickers,
                request.refresh,
                user_text,
                interpretation,
                code=InterpretedGoalCode.report_peer_set,
                description="Peer / compare path with report: same granular MCP sequence.",
            )

        plan = _run_pipeline_plan(tickers, request.refresh)
        ig = InterpretedGoal(
            code=InterpretedGoalCode.full_pipeline,
            intent=interpretation.intent,
            intent_rules_matched=list(interpretation.rules_matched),
            description="Single-step run_pipeline (explicit full-pipeline intent).",
            user_goal_text=user_text,
        )
        return PlanningOutcome(ok=True, plan=plan, interpreted_goal=ig, errors=[])

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
