"""
Compact, JSON-serializable LLM user payloads per agent phase.

Reduces tokens vs passing full orchestration dumps while preserving fields the prompts need.
Size limits are driven by :class:`~backend.agents.context_budget.ContextBudget`.

**Transparency:** when trimming applies, payloads include ``llm_context_budget`` with booleans such as
``user_request_truncated``, ``interpreted_goal_intent_rules_truncated``,
``interpreted_goal_template_rules_truncated``, ``interpreted_goal_user_goal_excerpt_truncated``,
``plan_alignment_findings_truncated``, ``errors_sample_truncated``, ``warnings_sample_truncated``,
plus existing coverage/company/critic clip flags. :func:`audit_compact_context` records
``llm_context_budget_applied`` when any signal is set.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.agents.artifact_summaries import audit_summaries_bundle
from backend.agents.context_budget import (
    ContextBudget,
    clip_critic_for_report_llm,
    clip_sorted_role_list,
)

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

_DEFAULT_BUDGET = ContextBudget()


def _trunc(s: str | None, max_len: int) -> str:
    if not s:
        return ""
    t = s.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def slim_interpreted_goal_for_llm(
    ig: InterpretedGoal,
    budget: ContextBudget = _DEFAULT_BUDGET,
) -> tuple[dict[str, Any], dict[str, bool]]:
    """
    Template + prefs for planning/critic/report — omit bulky narrative lists.

    Returns ``(payload, truncation_flags)``. Flags are only present (True) when a list or string
    was shortened vs. the full orchestration object — surfaced under ``llm_context_budget`` on
    critic/report/planning payloads for transparency.
    """
    flags: dict[str, bool] = {}
    rules_full = list(ig.intent_rules_matched)
    if len(rules_full) > budget.max_intent_rules_matched:
        flags["interpreted_goal_intent_rules_truncated"] = True

    pt = ig.plan_template
    pt_out: dict[str, Any] | None = None
    if pt is not None:
        tr_full = list(pt.template_rules_matched)
        if len(tr_full) > budget.max_template_rules_matched:
            flags["interpreted_goal_template_rules_truncated"] = True
        pt_out = {
            "template_id": pt.template_id.value,
            "mcp_execution_profile": pt.mcp_execution_profile,
            "peer_analysis_mandatory": pt.peer_analysis_mandatory,
            "persistence_filtering_required": pt.persistence_filtering_required,
            "template_rules_matched": tr_full[: budget.max_template_rules_matched],
        }
    gp = ig.goal_preferences
    gp_out = gp.model_dump(mode="json") if gp is not None else None
    ug_raw = (ig.user_goal_text or "").strip()
    if len(ug_raw) > budget.max_goal_excerpt_chars:
        flags["interpreted_goal_user_goal_excerpt_truncated"] = True
    out = {
        "code": ig.code.value,
        "orchestration_intent": ig.intent.value if ig.intent is not None else None,
        "intent_rules_matched": rules_full[: budget.max_intent_rules_matched],
        "description": _trunc(ig.description, 512),
        "user_goal_excerpt": _trunc(ig.user_goal_text, budget.max_goal_excerpt_chars),
        "goal_preferences": gp_out,
        "plan_template": pt_out,
    }
    return out, flags


def _user_request_truncated(user_request: str | None, max_chars: int) -> bool:
    return len((user_request or "").strip()) > max_chars


def _warnings_errors_truncation_flags(orch: OrchestrationOutput, budget: ContextBudget) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    if len(orch.errors) > budget.max_warn_err_samples:
        flags["errors_sample_truncated"] = True
    if len(orch.warnings) > budget.max_warn_err_samples:
        flags["warnings_sample_truncated"] = True
    return flags


def _slim_tool_result_row(t: ToolResultSummary, budget: ContextBudget) -> dict[str, Any]:
    ap = t.artifact_paths or {}
    ap_keys = sorted(ap.keys())[: budget.max_tool_result_artifact_keys]
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


def _slim_step_row(s: StepStatusEntry, budget: ContextBudget) -> dict[str, Any]:
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
    budget: ContextBudget = _DEFAULT_BUDGET,
) -> dict[str, Any]:
    """Aggregated execution scope — no raw MCP envelopes."""
    max_s = budget.max_step_rows
    max_t = budget.max_tool_result_rows
    steps = [_slim_step_row(s, budget) for s in step_statuses[:max_s]]
    if len(step_statuses) > max_s:
        steps.append({"truncated": True, "omitted_count": len(step_statuses) - max_s})
    tr = [_slim_tool_result_row(t, budget) for t in tool_results_summary[:max_t]]
    if len(tool_results_summary) > max_t:
        tr.append({"truncated": True, "omitted_count": len(tool_results_summary) - max_t})
    return {
        "step_count": len(step_statuses),
        "tool_result_row_count": len(tool_results_summary),
        "steps": steps,
        "tool_results": tr,
    }


def _slim_errors(errs: list[OrchestrationError], budget: ContextBudget) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    n = budget.max_warn_err_samples
    mx = budget.max_warn_err_message_chars
    for e in errs[:n]:
        out.append(
            {
                "code": e.code,
                "message": _trunc(e.message, mx),
                "source_tool": e.source_tool,
            }
        )
    return out


def _slim_warnings(w: list[OrchestrationWarning], budget: ContextBudget) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    n = budget.max_warn_err_samples
    mx = budget.max_warn_err_message_chars
    for x in w[:n]:
        out.append(
            {
                "code": x.code,
                "message": _trunc(x.message, mx),
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


def build_run_fingerprint(orch: OrchestrationOutput, budget: ContextBudget = _DEFAULT_BUDGET) -> dict[str, Any]:
    return RunFingerprint(
        run_id=orch.run_id,
        status=orch.status.value,
        message=_trunc(orch.message, budget.max_run_message_chars),
        final_summary=_trunc(orch.final_summary, budget.max_final_summary_chars),
        final_report_path=orch.final_report_path,
    ).model_dump(mode="json")


def build_intent_llm_context(
    *,
    user_request: str,
    tickers: list[str],
    refresh: bool,
    budget: ContextBudget | None = None,
) -> dict[str, Any]:
    b = budget or _DEFAULT_BUDGET
    out: dict[str, Any] = {
        "contract_version": CONTRACT_INTENT_LLM,
        "user_request": _trunc(user_request, b.max_user_request_chars),
        "tickers": list(tickers),
        "refresh": refresh,
    }
    if _user_request_truncated(user_request, b.max_user_request_chars):
        out["llm_context_budget"] = {"user_request_truncated": True}
    return out


def build_planning_llm_context(
    *,
    interpreted_goal: InterpretedGoal,
    user_request: str,
    tickers: list[str],
    refresh: bool,
    budget: ContextBudget | None = None,
) -> dict[str, Any]:
    b = budget or _DEFAULT_BUDGET
    ig_slim, ig_flags = slim_interpreted_goal_for_llm(interpreted_goal, b)
    budget_meta: dict[str, bool] = {**ig_flags}
    if _user_request_truncated(user_request, b.max_user_request_chars):
        budget_meta["user_request_truncated"] = True
    out: dict[str, Any] = {
        "contract_version": CONTRACT_PLANNING_LLM,
        "user_request": _trunc(user_request, b.max_user_request_chars),
        "tickers": list(tickers),
        "refresh": refresh,
        "interpreted_goal": ig_slim,
    }
    if budget_meta:
        out["llm_context_budget"] = budget_meta
    return out


def build_critic_llm_context(
    *,
    orch: OrchestrationOutput,
    orch_input: OrchestrationInput,
    plan_alignment_findings: list[dict[str, Any]],
    artifact_summaries: dict[str, Any],
    paths_roles: list[str],
    summary_roles_loaded: list[str],
    budget: ContextBudget | None = None,
) -> dict[str, Any]:
    b = budget or _DEFAULT_BUDGET
    pa_full = list(plan_alignment_findings or [])
    pa = pa_full[: b.max_plan_alignment_findings]
    ig_slim, ig_flags = slim_interpreted_goal_for_llm(orch.interpreted_goal, b)
    max_co = b.max_resolved_companies
    companies = [
        {
            "ticker": c.ticker,
            "cik": c.cik,
            "company_name": c.company_name,
        }
        for c in orch.resolved_companies[:max_co]
    ]
    co_trunc = False
    if len(orch.resolved_companies) > max_co:
        co_trunc = True
        companies.append(
            {
                "truncated": True,
                "omitted_count": len(orch.resolved_companies) - max_co,
            }
        )

    paths_eff, paths_meta = clip_sorted_role_list(list(paths_roles), b.max_coverage_roles)
    summ_eff, summ_meta = clip_sorted_role_list(list(summary_roles_loaded), b.max_coverage_roles)
    llm_budget: dict[str, Any] = {
        "resolved_companies_truncated": co_trunc,
        "artifact_paths_roles_truncated": paths_meta.get("truncated", False),
        "artifact_summary_roles_truncated": summ_meta.get("truncated", False),
    }
    if paths_meta.get("truncated"):
        llm_budget["artifact_paths_roles_omitted_count"] = paths_meta.get("omitted_count", 0)
    if summ_meta.get("truncated"):
        llm_budget["artifact_summary_roles_omitted_count"] = summ_meta.get("omitted_count", 0)

    llm_budget.update({k: True for k, v in ig_flags.items() if v})
    if len(pa_full) > b.max_plan_alignment_findings:
        llm_budget["plan_alignment_findings_truncated"] = True
    llm_budget.update(_warnings_errors_truncation_flags(orch, b))
    if _user_request_truncated(orch_input.analysis_goal, b.max_user_request_chars):
        llm_budget["user_request_truncated"] = True

    return {
        "contract_version": CONTRACT_CRITIC_LLM,
        "run": build_run_fingerprint(orch, b),
        "request": {
            "analysis_goal": _trunc(orch_input.analysis_goal, b.max_user_request_chars),
            "tickers": list(orch_input.tickers),
            "refresh": orch_input.refresh,
        },
        "interpreted_goal": ig_slim,
        "resolved_companies": companies,
        "plan_alignment_findings": pa,
        "tool_scope": build_tool_scope_summary(
            step_statuses=orch.step_statuses,
            tool_results_summary=orch.tool_results_summary,
            budget=b,
        ),
        "warnings_errors": {
            "warnings_count": len(orch.warnings),
            "errors_count": len(orch.errors),
            "errors_sample": _slim_errors(orch.errors, b),
            "warnings_sample": _slim_warnings(orch.warnings, b),
        },
        "artifact_coverage": {
            "artifact_paths_roles": paths_eff,
            "artifact_summary_roles_loaded": summ_eff,
        },
        "artifact_summaries": artifact_summaries,
        "llm_context_budget": llm_budget,
    }


def build_report_llm_context(
    *,
    orch: OrchestrationOutput,
    orch_input: OrchestrationInput,
    critic: dict[str, Any],
    artifact_summaries: dict[str, Any],
    paths_roles: list[str],
    summary_roles_loaded: list[str],
    budget: ContextBudget | None = None,
) -> dict[str, Any]:
    """Critic must be structured critic output (e.g. CriticAgentLLMOutput.model_dump)."""
    b = budget or _DEFAULT_BUDGET
    critic_clipped, critic_trunc = clip_critic_for_report_llm(critic, b)
    ig_slim, ig_flags = slim_interpreted_goal_for_llm(orch.interpreted_goal, b)

    max_co = b.max_resolved_companies
    companies = [
        {
            "ticker": c.ticker,
            "cik": c.cik,
            "company_name": c.company_name,
        }
        for c in orch.resolved_companies[:max_co]
    ]
    co_trunc = False
    if len(orch.resolved_companies) > max_co:
        co_trunc = True
        companies.append(
            {
                "truncated": True,
                "omitted_count": len(orch.resolved_companies) - max_co,
            }
        )

    paths_eff, paths_meta = clip_sorted_role_list(list(paths_roles), b.max_coverage_roles)
    summ_eff, summ_meta = clip_sorted_role_list(list(summary_roles_loaded), b.max_coverage_roles)
    llm_budget: dict[str, Any] = {
        "resolved_companies_truncated": co_trunc,
        "artifact_paths_roles_truncated": paths_meta.get("truncated", False),
        "artifact_summary_roles_truncated": summ_meta.get("truncated", False),
    }
    if paths_meta.get("truncated"):
        llm_budget["artifact_paths_roles_omitted_count"] = paths_meta.get("omitted_count", 0)
    if summ_meta.get("truncated"):
        llm_budget["artifact_summary_roles_omitted_count"] = summ_meta.get("omitted_count", 0)
    for k, v in critic_trunc.items():
        llm_budget[f"critic_{k}"] = v
    llm_budget.update({k: True for k, v in ig_flags.items() if v})
    llm_budget.update(_warnings_errors_truncation_flags(orch, b))
    if _user_request_truncated(orch_input.analysis_goal, b.max_user_request_chars):
        llm_budget["user_request_truncated"] = True

    return {
        "contract_version": CONTRACT_REPORT_LLM,
        "run": build_run_fingerprint(orch, b),
        "request": {
            "analysis_goal": _trunc(orch_input.analysis_goal, b.max_user_request_chars),
            "tickers": list(orch_input.tickers),
            "refresh": orch_input.refresh,
        },
        "interpreted_goal": ig_slim,
        "critic": critic_clipped,
        "tool_scope": build_tool_scope_summary(
            step_statuses=orch.step_statuses,
            tool_results_summary=orch.tool_results_summary,
            budget=b,
        ),
        "warnings_errors": {
            "warnings_count": len(orch.warnings),
            "errors_count": len(orch.errors),
            "errors_sample": _slim_errors(orch.errors, b),
            "warnings_sample": _slim_warnings(orch.warnings, b),
        },
        "artifact_coverage": {
            "artifact_paths_roles": paths_eff,
            "artifact_summary_roles_loaded": summ_eff,
        },
        "artifact_summaries": artifact_summaries,
        "llm_context_budget": llm_budget,
    }


def build_intent_preferences_assistant_context(
    *,
    analysis_goal: str,
    tickers: list[str],
    rule_based_goal_preferences: GoalPreferences,
    budget: ContextBudget | None = None,
) -> dict[str, Any]:
    """Optional pre-orchestration preference patch — rule baseline + goal text only."""
    b = budget or _DEFAULT_BUDGET
    out: dict[str, Any] = {
        "contract_version": CONTRACT_INTENT_PREFERENCES_LLM,
        "analysis_goal": _trunc(analysis_goal, b.max_user_request_chars),
        "tickers": list(tickers),
        "rule_based_goal_preferences": rule_based_goal_preferences.model_dump(mode="json"),
    }
    if _user_request_truncated(analysis_goal, b.max_user_request_chars):
        out["llm_context_budget"] = {"user_request_truncated": True}
    return out


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
    lcb = context.get("llm_context_budget")
    _BUDGET_SIGNAL_KEYS = frozenset(
        {
            "resolved_companies_truncated",
            "artifact_paths_roles_truncated",
            "artifact_summary_roles_truncated",
            "user_request_truncated",
            "plan_alignment_findings_truncated",
            "interpreted_goal_intent_rules_truncated",
            "interpreted_goal_template_rules_truncated",
            "interpreted_goal_user_goal_excerpt_truncated",
            "errors_sample_truncated",
            "warnings_sample_truncated",
        }
    )
    if isinstance(lcb, dict) and (
        any(lcb.get(k) for k in _BUDGET_SIGNAL_KEYS)
        or lcb.get("critic_truncated")
    ):
        out["llm_context_budget_applied"] = True
    out.update(audit)
    return out
