"""
Compact, machine-friendly ``phase_output`` payloads for agent / orchestration phases.

Used under ``analysis_run.meta_json['ai_agents']`` and ``run_steps.meta_json`` — avoid storing
unbounded prose; use excerpts, counts, and stable enums.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    OrchestrationPlan,
    PlannedStep,
    StepStatusEntry,
)

from backend.agents.output_schemas import CriticAgentLLMOutput, ReportAgentLLMOutput

PHASE_OUTPUT_CONTRACT_VERSION = "1"

_MAX_ISSUES = 20
_MAX_TAKEAWAYS = 15
_MAX_ARTIFACT_REFS = 30
_DEFAULT_PROSE_EXCERPT = 360
_DEFAULT_GOAL_EXCERPT = 400
_DEFAULT_MARKDOWN_PREVIEW = 480


def _trunc(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def build_intent_phase_output(
    *,
    interpreted_goal: InterpretedGoal | None,
    tickers: list[str],
    analysis_goal: str,
    source: str,
    confidence: str | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    """Structured intent record (deterministic planner or LLM)."""
    entities: dict[str, Any] = {"tickers": list(tickers)}
    if not interpreted_goal:
        return {
            "contract_version": PHASE_OUTPUT_CONTRACT_VERSION,
            "source": source,
            "interpreted_goal": None,
            "goal_code": None,
            "orchestration_intent": None,
            "rules_matched": [],
            "description_excerpt": "",
            "user_goal_excerpt": _trunc(analysis_goal, _DEFAULT_GOAL_EXCERPT),
            "entities": entities,
            "confidence": confidence,
            "caveats": list(caveats or []),
        }
    return {
        "contract_version": PHASE_OUTPUT_CONTRACT_VERSION,
        "source": source,
        "goal_code": interpreted_goal.code.value,
        "orchestration_intent": interpreted_goal.intent.value if interpreted_goal.intent else None,
        "rules_matched": list(interpreted_goal.intent_rules_matched),
        "description_excerpt": _trunc(interpreted_goal.description, _DEFAULT_GOAL_EXCERPT),
        "user_goal_excerpt": _trunc(interpreted_goal.user_goal_text, _DEFAULT_GOAL_EXCERPT),
        "entities": entities,
        "confidence": confidence,
        "caveats": list(caveats or []),
    }


def build_planning_phase_output(
    *,
    plan: OrchestrationPlan | None,
    interpreted_goal: InterpretedGoal | None,
    source: str,
    ordered_steps: list[PlannedStep] | None = None,
) -> dict[str, Any]:
    """Ordered plan + chosen path hint (deterministic or LLM)."""
    steps_src = ordered_steps
    if steps_src is None and plan is not None:
        steps_src = plan.steps
    ordered: list[dict[str, Any]] = []
    if steps_src:
        for s in sorted(steps_src, key=lambda x: x.order):
            ordered.append(
                {
                    "order": s.order,
                    "tool_name": s.tool_name,
                    "label": s.label or f"{s.tool_name}:{s.order}",
                }
            )
    chosen: dict[str, Any] = {}
    if interpreted_goal is not None:
        chosen = {
            "goal_code": interpreted_goal.code.value,
            "orchestration_intent": interpreted_goal.intent.value if interpreted_goal.intent else None,
        }
    return {
        "contract_version": PHASE_OUTPUT_CONTRACT_VERSION,
        "source": source,
        "chosen_path": chosen,
        "ordered_plan": ordered,
        "step_count": len(ordered),
        "rationale": "rule_based_planner_v1" if source == "deterministic_rules" else "llm_planning_agent",
    }


def build_planning_phase_output_from_step_statuses(
    step_statuses: list[StepStatusEntry],
    *,
    interpreted_goal: InterpretedGoal | None,
    source: str = "orchestration_output",
) -> dict[str, Any]:
    """Fallback when executor state is missing but orchestration output lists steps."""
    ordered = [
        {
            "order": s.order,
            "tool_name": s.tool_name,
            "label": s.label or f"{s.tool_name}:{s.order}",
            "mcp_status": s.mcp_status,
        }
        for s in sorted(step_statuses, key=lambda x: x.order)
    ]
    chosen: dict[str, Any] = {}
    if interpreted_goal is not None:
        chosen = {
            "goal_code": interpreted_goal.code.value,
            "orchestration_intent": interpreted_goal.intent.value if interpreted_goal.intent else None,
        }
    return {
        "contract_version": PHASE_OUTPUT_CONTRACT_VERSION,
        "source": source,
        "chosen_path": chosen,
        "ordered_plan": ordered,
        "step_count": len(ordered),
        "rationale": "inferred_from_step_statuses",
    }


def build_critic_phase_output(critic: CriticAgentLLMOutput, *, prose_max: int = _DEFAULT_PROSE_EXCERPT) -> dict[str, Any]:
    """Major concerns, excerpts, coarse signals (full JSON still in ai_agents.result when present)."""
    weak: list[str] = []
    if critic.overall_confidence == "low":
        weak.append("low_overall_confidence")
    if len(critic.issues) > 0:
        weak.append("flagged_issues")
    return {
        "contract_version": PHASE_OUTPUT_CONTRACT_VERSION,
        "overall_confidence": critic.overall_confidence,
        "issue_count": len(critic.issues),
        "issues": critic.issues[:_MAX_ISSUES],
        "findings_assessment_excerpt": _trunc(critic.findings_assessment, prose_max),
        "caveat_coverage_excerpt": _trunc(critic.caveat_coverage, prose_max),
        "trustworthiness_notes_excerpt": _trunc(critic.trustworthiness_notes, prose_max),
        "weak_evidence_signals": weak,
    }


def build_report_phase_output(
    report: ReportAgentLLMOutput,
    artifact_paths: dict[str, str],
    *,
    markdown_preview_len: int = _DEFAULT_MARKDOWN_PREVIEW,
) -> dict[str, Any]:
    """Summary bullets, short preview, artifact roles (basenames only)."""
    refs: list[dict[str, str]] = []
    for role, path_str in artifact_paths.items():
        if not path_str or not str(path_str).strip():
            continue
        refs.append({"role": role, "basename": Path(str(path_str)).name})
        if len(refs) >= _MAX_ARTIFACT_REFS:
            break
    return {
        "contract_version": PHASE_OUTPUT_CONTRACT_VERSION,
        "key_takeaways": report.key_takeaways[:_MAX_TAKEAWAYS],
        "markdown_preview": _trunc(report.user_report_markdown, markdown_preview_len),
        "markdown_char_count": len(report.user_report_markdown or ""),
        "artifact_refs": refs,
    }


def build_skipped_phase_output(
    *,
    reason: str,
    error: str | None = None,
    boundary_failure_class: str | None = None,
    phase_status: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "contract_version": PHASE_OUTPUT_CONTRACT_VERSION,
        "skipped": True,
        "reason": reason,
        "error": error,
    }
    if boundary_failure_class:
        out["boundary_failure_class"] = boundary_failure_class
    if phase_status:
        out["phase_status"] = phase_status
    return out
