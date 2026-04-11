"""
Compact, JSON-serializable LLM user payloads per agent phase.

Reduces tokens vs passing full orchestration dumps while preserving fields the prompts need.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.agents.artifact_summaries import audit_summaries_bundle

from edgar_project.orchestration.schemas import (
    GoalPreferences,
    InterpretedGoal,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationWarning,
    OrchestrationError,
    StepStatusEntry,
    ToolResultSummary,
)

CONTRACT_INTENT_LLM = "intent_llm_v1"
CONTRACT_PLANNING_LLM = "planning_llm_v1"
CONTRACT_CRITIC_LLM = "critic_llm_v1"
CONTRACT_REPORT_LLM = "report_llm_v1"
CONTRACT_INTENT_PREFERENCES_LLM = "intent_preferences_llm_v1"

_MAX_USER_REQUEST_CHARS = 8_000
_MAX_GOAL_EXCERPT_CHARS = 600
_MAX_WARN_ERR_SAMPLES = 5
_MAX_MSG_CHARS = 240
_MAX_PLAN_ALIGNMENT = 12
_MAX_RESOLVED_COMPANIES = 24
_MAX_TOOL_RESULT_ROWS = 32
_MAX_STEP_ROWS = 48


def _trunc(s: str | None, max_len: int) -> str:
    if not s:
        return ""
    t = s.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def slim_interpreted_goal_for_llm(ig: InterpretedGoal) -> dict[str, Any]:
    """Template + prefs for planning/critic/report — omit bulky narrative lists."""
    pt = ig.plan_template
    pt_out: dict[str, Any] | None = None
    if pt is not None:
        pt_out = {
            "template_id": pt.template_id.value,
            "mcp_execution_profile": pt.mcp_execution_profile,
            "peer_analysis_mandatory": pt.peer_analysis_mandatory,
            "persistence_filtering_required": pt.persistence_filtering_required,
            "template_rules_matched": list(pt.template_rules_matched)[:12],
        }
    gp = ig.goal_preferences
    gp_out = gp.model_dump(mode="json") if gp is not None else None
    return {
        "code": ig.code.value,
        "orchestration_intent": ig.intent.value if ig.intent is not None else None,
        "intent_rules_matched": list(ig.intent_rules_matched)[:16],
        "description": _trunc(ig.description, 512),
        "user_goal_excerpt": _trunc(ig.user_goal_text, _MAX_GOAL_EXCERPT_CHARS),
        "goal_preferences": gp_out,
        "plan_template": pt_out,
    }


def _slim_tool_result_row(t: ToolResultSummary) -> dict[str, Any]:
    ap = t.artifact_paths or {}
    ap_keys = sorted(ap.keys())[:12]
    return {
        "order": t.order,
        "tool_name": t.tool_name,
        "mcp_status": t.mcp_status,
        "panel_row_count": t.panel_row_count,
        "feature_row_count": t.feature_row_count,
        "anomaly_count": t.anomaly_count,
        "report_character_count": t.report_character_count,
        "ciks_observed_count": len(t.ciks_observed or []),
        "artifact_role_keys": ap_keys,
    }


def _slim_step_row(s: StepStatusEntry) -> dict[str, Any]:
    return {
        "order": s.order,
        "tool_name": s.tool_name,
        "mcp_status": s.mcp_status,
        "label": _trunc(s.label, 200),
        "detail": _trunc(s.detail, 200) if s.detail else None,
    }


def build_tool_scope_summary(
    *,
    step_statuses: list[StepStatusEntry],
    tool_results_summary: list[ToolResultSummary],
) -> dict[str, Any]:
    """Aggregated execution scope — no raw MCP envelopes."""
    steps = [_slim_step_row(s) for s in step_statuses[:_MAX_STEP_ROWS]]
    if len(step_statuses) > _MAX_STEP_ROWS:
        steps.append({"truncated": True, "omitted_count": len(step_statuses) - _MAX_STEP_ROWS})
    tr = [_slim_tool_result_row(t) for t in tool_results_summary[:_MAX_TOOL_RESULT_ROWS]]
    if len(tool_results_summary) > _MAX_TOOL_RESULT_ROWS:
        tr.append({"truncated": True, "omitted_count": len(tool_results_summary) - _MAX_TOOL_RESULT_ROWS})
    return {
        "step_count": len(step_statuses),
        "tool_result_row_count": len(tool_results_summary),
        "steps": steps,
        "tool_results": tr,
    }


def _slim_errors(errs: list[OrchestrationError]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in errs[:_MAX_WARN_ERR_SAMPLES]:
        out.append(
            {
                "code": e.code,
                "message": _trunc(e.message, _MAX_MSG_CHARS),
                "source_tool": e.source_tool,
            }
        )
    return out


def _slim_warnings(w: list[OrchestrationWarning]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for x in w[:_MAX_WARN_ERR_SAMPLES]:
        out.append(
            {
                "code": x.code,
                "message": _trunc(x.message, _MAX_MSG_CHARS),
                "source_tool": x.source_tool,
            }
        )
    return out


class RunFingerprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    message: str = Field(description="Short status line.")
    final_summary: str = ""
    final_report_path: str | None = None


def build_run_fingerprint(orch: OrchestrationOutput) -> dict[str, Any]:
    return RunFingerprint(
        run_id=orch.run_id,
        status=orch.status.value,
        message=_trunc(orch.message, 1_000),
        final_summary=_trunc(orch.final_summary, 2_000),
        final_report_path=orch.final_report_path,
    ).model_dump(mode="json")


def build_intent_llm_context(
    *,
    user_request: str,
    tickers: list[str],
    refresh: bool,
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_INTENT_LLM,
        "user_request": _trunc(user_request, _MAX_USER_REQUEST_CHARS),
        "tickers": list(tickers),
        "refresh": refresh,
    }


def build_planning_llm_context(
    *,
    interpreted_goal: InterpretedGoal,
    user_request: str,
    tickers: list[str],
    refresh: bool,
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_PLANNING_LLM,
        "user_request": _trunc(user_request, _MAX_USER_REQUEST_CHARS),
        "tickers": list(tickers),
        "refresh": refresh,
        "interpreted_goal": slim_interpreted_goal_for_llm(interpreted_goal),
    }


def build_critic_llm_context(
    *,
    orch: OrchestrationOutput,
    orch_input: OrchestrationInput,
    plan_alignment_findings: list[dict[str, Any]],
    artifact_summaries: dict[str, Any],
    paths_roles: list[str],
    summary_roles_loaded: list[str],
) -> dict[str, Any]:
    pa = list(plan_alignment_findings or [])[:_MAX_PLAN_ALIGNMENT]
    companies = [
        {
            "ticker": c.ticker,
            "cik": c.cik,
            "company_name": c.company_name,
        }
        for c in orch.resolved_companies[:_MAX_RESOLVED_COMPANIES]
    ]
    if len(orch.resolved_companies) > _MAX_RESOLVED_COMPANIES:
        companies.append(
            {
                "truncated": True,
                "omitted_count": len(orch.resolved_companies) - _MAX_RESOLVED_COMPANIES,
            }
        )

    return {
        "contract_version": CONTRACT_CRITIC_LLM,
        "run": build_run_fingerprint(orch),
        "request": {
            "analysis_goal": _trunc(orch_input.analysis_goal, _MAX_USER_REQUEST_CHARS),
            "tickers": list(orch_input.tickers),
            "refresh": orch_input.refresh,
        },
        "interpreted_goal": slim_interpreted_goal_for_llm(orch.interpreted_goal),
        "resolved_companies": companies,
        "plan_alignment_findings": pa,
        "tool_scope": build_tool_scope_summary(
            step_statuses=orch.step_statuses,
            tool_results_summary=orch.tool_results_summary,
        ),
        "warnings_errors": {
            "warnings_count": len(orch.warnings),
            "errors_count": len(orch.errors),
            "errors_sample": _slim_errors(orch.errors),
            "warnings_sample": _slim_warnings(orch.warnings),
        },
        "artifact_coverage": {
            "artifact_paths_roles": sorted(paths_roles),
            "artifact_summary_roles_loaded": sorted(summary_roles_loaded),
        },
        "artifact_summaries": artifact_summaries,
    }


def build_report_llm_context(
    *,
    orch: OrchestrationOutput,
    orch_input: OrchestrationInput,
    critic: dict[str, Any],
    artifact_summaries: dict[str, Any],
    paths_roles: list[str],
    summary_roles_loaded: list[str],
) -> dict[str, Any]:
    """Critic must be structured critic output (e.g. CriticAgentLLMOutput.model_dump)."""
    return {
        "contract_version": CONTRACT_REPORT_LLM,
        "run": build_run_fingerprint(orch),
        "request": {
            "analysis_goal": _trunc(orch_input.analysis_goal, _MAX_USER_REQUEST_CHARS),
            "tickers": list(orch_input.tickers),
            "refresh": orch_input.refresh,
        },
        "interpreted_goal": slim_interpreted_goal_for_llm(orch.interpreted_goal),
        "critic": critic,
        "tool_scope": build_tool_scope_summary(
            step_statuses=orch.step_statuses,
            tool_results_summary=orch.tool_results_summary,
        ),
        "warnings_errors": {
            "warnings_count": len(orch.warnings),
            "errors_count": len(orch.errors),
            "errors_sample": _slim_errors(orch.errors),
            "warnings_sample": _slim_warnings(orch.warnings),
        },
        "artifact_coverage": {
            "artifact_paths_roles": sorted(paths_roles),
            "artifact_summary_roles_loaded": sorted(summary_roles_loaded),
        },
        "artifact_summaries": artifact_summaries,
    }


def build_intent_preferences_assistant_context(
    *,
    analysis_goal: str,
    tickers: list[str],
    rule_based_goal_preferences: GoalPreferences,
) -> dict[str, Any]:
    """Optional pre-orchestration preference patch — rule baseline + goal text only."""
    return {
        "contract_version": CONTRACT_INTENT_PREFERENCES_LLM,
        "analysis_goal": _trunc(analysis_goal, _MAX_USER_REQUEST_CHARS),
        "tickers": list(tickers),
        "rule_based_goal_preferences": rule_based_goal_preferences.model_dump(mode="json"),
    }


def audit_compact_context(context: dict[str, Any]) -> dict[str, Any]:
    """Persistable summary (sizes only) for meta_json."""
    summaries = context.get("artifact_summaries")
    audit = (
        audit_summaries_bundle(summaries)
        if isinstance(summaries, dict) and summaries.get("by_role") is not None
        else {}
    )
    out: dict[str, Any] = {
        "contract_version": context.get("contract_version"),
        "run_id": (context.get("run") or {}).get("run_id"),
        "artifact_roles": sorted((summaries or {}).get("by_role", {}).keys())
        if isinstance(summaries, dict)
        else [],
    }
    out.update(audit)
    return out
