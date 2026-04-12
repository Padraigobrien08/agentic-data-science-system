"""
Compare estimated LLM **user-message** JSON sizes across two :class:`ContextBudget` profiles.

No model calls — sizes are ``len(json.dumps(..., ensure_ascii=False).encode("utf-8"))`` for the
same logical fixture (representative orchestration + artifact bundle).

Usage::

    python -m backend.dev.llm_context_compare --a default --b tight

    python -m backend.dev.llm_context_compare --a default --b path/to/budget_overrides.json

JSON override files merge onto :class:`~backend.agents.context_budget.ContextBudget` defaults
(dataclass field names only), e.g. ``{"max_step_rows": 8, "max_user_request_chars": 2000}``.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, Iterable

from backend.agents.context_budget import ContextBudget
from backend.agents.llm_context import (
    build_critic_llm_context,
    build_intent_llm_context,
    build_intent_preferences_assistant_context,
    build_planning_llm_context,
    build_report_llm_context,
)
from edgar_project.orchestration.goal_preferences import parse_goal_preferences
from edgar_project.orchestration.plan_templates import get_plan_template_snapshot
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationRunStatus,
    PlanTemplateId,
    ResolvedCompany,
    StepStatusEntry,
    ToolResultSummary,
)

# Presets are **partial** field overrides merged onto ``ContextBudget()`` — for local what-if only;
# not production defaults (see ``ContextBudget`` / ``EDGAR_BACKEND_AGENT_CONTEXT_*``).
BUDGET_PRESETS: dict[str, dict[str, Any]] = {
    "default": {},
    "tight": {
        "max_user_request_chars": 2_500,
        "max_step_rows": 10,
        "max_tool_result_rows": 8,
        "max_goal_excerpt_chars": 320,
        "max_intent_rules_matched": 6,
        "max_template_rules_matched": 4,
        "max_plan_alignment_findings": 6,
        "max_resolved_companies": 6,
        "max_coverage_roles": 4,
        "max_critic_text_field_chars": 3_000,
        "max_critic_issue_items": 8,
        "max_warn_err_samples": 3,
        "max_tool_result_artifact_keys": 6,
    },
}


def json_utf8_bytes(obj: Any) -> int:
    """Byte length of JSON as sent on the wire (UTF-8, no ASCII escaping of non-ASCII)."""
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return len(raw.encode("utf-8"))


def rough_tokens_from_bytes(n: int) -> int:
    """Very rough heuristic (~4 bytes per token for English-ish JSON); for dev comparison only."""
    return max(0, n // 4)


@dataclass(frozen=True)
class PhaseSizeRow:
    phase: str
    old_bytes: int
    new_bytes: int

    @property
    def delta_bytes(self) -> int:
        return self.old_bytes - self.new_bytes

    @property
    def reduction_pct(self) -> float | None:
        if self.old_bytes <= 0:
            return None
        return 100.0 * (self.old_bytes - self.new_bytes) / self.old_bytes


def _budget_field_names() -> set[str]:
    return {f.name for f in fields(ContextBudget)}


def budget_from_spec(spec: str) -> ContextBudget:
    """
    ``spec`` is either a preset name in ``BUDGET_PRESETS`` or a path to a JSON object of overrides.
    """
    s = spec.strip()
    path = Path(s)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Budget JSON must be an object: {path}")
        return merge_budget_overrides(ContextBudget(), data)
    key = s.lower()
    if key not in BUDGET_PRESETS:
        raise ValueError(
            f"Unknown budget preset {spec!r}. Known: {sorted(BUDGET_PRESETS)} or a .json path.",
        )
    return merge_budget_overrides(ContextBudget(), BUDGET_PRESETS[key])


def merge_budget_overrides(base: ContextBudget, overrides: dict[str, Any]) -> ContextBudget:
    valid = _budget_field_names()
    bad = set(overrides) - valid
    if bad:
        raise ValueError(f"Unknown ContextBudget fields: {sorted(bad)}")
    return replace(base, **{k: overrides[k] for k in overrides})


def _minimal_interpreted_goal() -> InterpretedGoal:
    snap = get_plan_template_snapshot(PlanTemplateId.trend_deterioration)
    return InterpretedGoal(
        code=InterpretedGoalCode.trend_deterioration,
        intent=None,
        intent_rules_matched=[f"rule_{i}" for i in range(20)],
        description="Regression-sized description for context compare.",
        user_goal_text=("User goal echo " * 120).strip(),
        goal_preferences=None,
        plan_template=snap,
    )


def _standard_orchestration_bundle() -> tuple[
    OrchestrationOutput,
    OrchestrationInput,
    list[dict[str, Any]],
    dict[str, Any],
    list[str],
    list[str],
    dict[str, Any],
]:
    """Synthetic but valid shapes so critic/report builders exercise truncation paths."""
    ig = _minimal_interpreted_goal()
    companies = [
        ResolvedCompany(ticker=t, cik=1000000 + i, company_name=f"Co {t}")
        for i, t in enumerate(["AAPL", "MSFT", "NVDA", "GOOG", "META", "AMZN", "TSLA", "IBM"])
    ]
    steps = [
        StepStatusEntry(order=i, tool_name="resolve_company" if i % 2 == 0 else "run_pipeline", mcp_status="success")
        for i in range(24)
    ]
    tool_rows = [
        ToolResultSummary(
            order=i,
            tool_name="run_pipeline",
            mcp_status="success",
            panel_row_count=10 + i,
            artifact_paths={f"role_{j}": f"/tmp/{i}_{j}.csv" for j in range(6)},
        )
        for i in range(18)
    ]
    orch = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message=("Run finished ok. " * 80).strip(),
        final_summary=("Summary line " * 40).strip(),
        interpreted_goal=ig,
        resolved_companies=companies,
        step_statuses=steps,
        tool_results_summary=tool_rows,
    )
    inp = OrchestrationInput(
        tickers=["AAPL", "MSFT"],
        analysis_goal=("Detect deterioration vs peers — " * 200).strip(),
        refresh=False,
    )
    plan_findings = [
        {"code": f"align_{i}", "detail": f"Finding text {i} " * 4}
        for i in range(14)
    ]
    summaries = {
        "contract_version": "artifact_summaries_v1",
        "by_role": {
            "anomalies_csv": {"kind": "anomalies_csv", "top_rows": [{"x": i} for i in range(5)]},
            "findings_summary": {"kind": "findings_summary", "top_rows": [{"y": i} for i in range(5)]},
        },
        "artifact_index": [{"role": "r1", "path": "/p1"}],
        "context_budget": {"truncated": False, "artifact_roles_omitted": [], "artifact_index_truncated": False},
    }
    paths_roles = [f"path_role_{i}" for i in range(12)]
    summary_roles = ["anomalies_csv", "findings_summary", "panel_trim"]
    critic = {
        "findings_assessment": ("Assessment " * 30).strip(),
        "caveat_coverage": ("Caveats " * 30).strip(),
        "trustworthiness_notes": ("Trust " * 30).strip(),
        "issues": [f"Issue {i}" for i in range(16)],
        "overall_confidence": "medium",
    }
    return orch, inp, plan_findings, summaries, paths_roles, summary_roles, critic


def build_phase_payloads(budget: ContextBudget) -> dict[str, dict[str, Any]]:
    """Build one user JSON payload per agent phase (same inputs as :func:`_standard_orchestration_bundle`)."""
    ig = _minimal_interpreted_goal()
    orch, inp, plan_findings, summaries, paths_roles, summary_roles, critic = _standard_orchestration_bundle()
    prefs = parse_goal_preferences(inp.analysis_goal)
    out: dict[str, dict[str, Any]] = {
        "intent": build_intent_llm_context(
            user_request=inp.analysis_goal,
            tickers=list(inp.tickers),
            refresh=inp.refresh,
            budget=budget,
        ),
        "planning": build_planning_llm_context(
            interpreted_goal=ig,
            user_request=inp.analysis_goal,
            tickers=list(inp.tickers),
            refresh=inp.refresh,
            budget=budget,
        ),
        "intent_preferences": build_intent_preferences_assistant_context(
            analysis_goal=inp.analysis_goal,
            tickers=list(inp.tickers),
            rule_based_goal_preferences=prefs,
            budget=budget,
        ),
        "critic": build_critic_llm_context(
            orch=orch,
            orch_input=inp,
            plan_alignment_findings=plan_findings,
            artifact_summaries=summaries,
            paths_roles=paths_roles,
            summary_roles_loaded=summary_roles,
            budget=budget,
        ),
        "report": build_report_llm_context(
            orch=orch,
            orch_input=inp,
            critic=critic,
            artifact_summaries=summaries,
            paths_roles=paths_roles,
            summary_roles_loaded=summary_roles,
            budget=budget,
        ),
    }
    return out


def compare_budgets(
    budget_old: ContextBudget,
    budget_new: ContextBudget,
) -> list[PhaseSizeRow]:
    """
    Return per-phase size rows (``old`` = first budget, ``new`` = second).

    Interpreting **reduction**: positive ``delta_bytes`` means the second budget produced a
    smaller payload (good for token savings).
    """
    old_payloads = build_phase_payloads(budget_old)
    new_payloads = build_phase_payloads(budget_new)
    phases = sorted(old_payloads.keys())
    rows: list[PhaseSizeRow] = []
    for ph in phases:
        ob = json_utf8_bytes(old_payloads[ph])
        nb = json_utf8_bytes(new_payloads[ph])
        rows.append(PhaseSizeRow(phase=ph, old_bytes=ob, new_bytes=nb))
    return rows


def format_table(
    rows: Iterable[PhaseSizeRow],
    *,
    label_old: str,
    label_new: str,
) -> str:
    lines: list[str] = []
    header = (
        f"{'phase':<20} {label_old:>14} {label_new:>14} {'Δ bytes':>10} {'reduction %':>12} {'~tok old':>10} {'~tok new':>10}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in rows:
        pct = r.reduction_pct
        pct_s = f"{pct:+.1f}" if pct is not None else "n/a"
        lines.append(
            f"{r.phase:<20} {r.old_bytes:>14,} {r.new_bytes:>14,} {r.delta_bytes:>+10,} {pct_s:>12} "
            f"{rough_tokens_from_bytes(r.old_bytes):>10,} {rough_tokens_from_bytes(r.new_bytes):>10,}"
        )
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compare estimated LLM user JSON sizes for two ContextBudget profiles (offline).",
    )
    p.add_argument(
        "--a",
        default="default",
        metavar="SPEC",
        help="First budget: preset name or path to JSON overrides (default: %(default)s).",
    )
    p.add_argument(
        "--b",
        default="tight",
        metavar="SPEC",
        help="Second budget: preset name or JSON path (default: %(default)s).",
    )
    p.add_argument(
        "--label-a",
        default="baseline (A)",
        help="Column label for first budget.",
    )
    p.add_argument(
        "--label-b",
        default="comparison (B)",
        help="Column label for second budget.",
    )
    p.add_argument(
        "--list-presets",
        action="store_true",
        help="Print known preset names and exit.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.list_presets:
        print("Presets:", ", ".join(sorted(BUDGET_PRESETS)))
        for name, ov in sorted(BUDGET_PRESETS.items()):
            if not ov:
                print(f"  {name}: (defaults)")
            else:
                print(f"  {name}: {len(ov)} override(s)")
        return 0
    ba = budget_from_spec(args.a)
    bb = budget_from_spec(args.b)
    rows = compare_budgets(ba, bb)
    print(format_table(rows, label_old=args.label_a, label_new=args.label_b))
    print()
    print(
        "Notes: sizes are UTF-8 bytes of compact JSON user payloads; ~tok ≈ bytes/4 (rough). "
        "Positive Δ / positive reduction % means B is smaller than A."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
