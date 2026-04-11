"""
Traceable EDGAR analysis: coordinator MCP execution, DB step/envelope persistence, critic, report.

The control flow below is intentionally **linear and explicit** (no hidden mega-pipeline helper).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.agents.critic_agent import CriticAgent
from backend.agents.critic_artifact_keys import collect_critic_excerpts
from backend.agents.output_schemas import CriticAgentLLMOutput
from backend.agents.boundary_failures import (
    CRITIC_BLOCKED_REPORT,
    LLM_NOT_CONFIGURED,
    classify_llm_phase_exception,
)
from backend.agents.persist_mcp_trace import persist_orchestration_step_trace
from backend.agents.phase_outputs import (
    build_critic_phase_output,
    build_intent_phase_output,
    build_planning_phase_output,
    build_planning_phase_output_from_step_statuses,
    build_report_phase_output,
    build_skipped_phase_output,
)
from backend.agents.report_agent import ReportAgent
from backend.agents.ai_agents_meta import merge_ai_agents_meta
from backend.agents.llm_phase_status import (
    PHASE_DEGRADED,
    PHASE_FAILED,
    PHASE_SKIPPED,
    PHASE_SUCCESS,
    build_llm_phases_summary_payload,
    latest_model_call_for_agent_prompt,
)
from backend.agents.prompt_registry import AGENT_PROMPT_IDS
from backend.agents.traceability_summary import build_runtime_traceability_bundle
from backend.config.settings import Settings, get_settings
from backend.llm.protocol import ChatCompletionProvider
from backend.models.enums import RunStepStatus
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService
from backend.services.run_step_service import RunStepService
from edgar_project.orchestration.agent import AnalysisAgent
from edgar_project.orchestration.schemas import OrchestrationInput, OrchestrationOutput
from edgar_project.orchestration.state import OrchestrationRunState


@dataclass(frozen=True)
class TraceableEdgarPipelineResult:
    """Return bundle so the execution service can ``set_output_payload`` then ``merge_output_payload``."""

    orchestration_output: OrchestrationOutput
    output_payload_patch: dict[str, Any]


def run_traceable_edgar_pipeline(
    session: Session,
    analysis_run_id: UUID,
    orch_input: OrchestrationInput,
    *,
    llm_provider: ChatCompletionProvider | None,
    settings: Settings | None = None,
    coordinator: Callable[
        [OrchestrationInput], tuple[OrchestrationOutput, OrchestrationRunState | None]
    ]
    | None = None,
) -> TraceableEdgarPipelineResult:
    """
    Run plan + MCP tools, persist per-step trace, optionally run critic + report LLMs.
    """
    s = settings if settings is not None else get_settings()
    coord_fn = coordinator or AnalysisAgent().run_returning_state

    # --- Step 1: coordinator → planner → Executor (only MCP entry; existing tool layer) ---
    orch_out, run_state = coord_fn(orch_input)

    run_svc = AnalysisRunService(session)
    rs_steps = RunStepService(session)

    # --- Step 2: persist every planned MCP step (skipped → RunStep only; executed → ToolCall + envelope) ---
    if run_state is not None:
        persist_orchestration_step_trace(session, analysis_run_id, orch_out, run_state, step_index_base=0)
    else:
        merge_ai_agents_meta(
            session,
            analysis_run_id,
            "mcp_trace",
            {"persisted": False, "reason": "no_executor_state"},
        )

    ig = orch_out.interpreted_goal
    tickers = list(orch_input.tickers)
    analysis_goal = orch_input.analysis_goal
    if run_state is not None:
        ig_effective = run_state.interpreted_goal or ig
        intent_po = build_intent_phase_output(
            interpreted_goal=ig_effective,
            tickers=tickers,
            analysis_goal=analysis_goal,
            source="deterministic_rules",
        )
        plan_po = build_planning_phase_output(
            plan=run_state.plan,
            interpreted_goal=ig_effective,
            source="deterministic_rules",
        )
    else:
        intent_po = build_intent_phase_output(
            interpreted_goal=ig,
            tickers=tickers,
            analysis_goal=analysis_goal,
            source="deterministic_rules",
            caveats=["executor_state_unavailable"],
        )
        plan_po = build_planning_phase_output_from_step_statuses(
            orch_out.step_statuses,
            interpreted_goal=ig,
        )
    merge_ai_agents_meta(
        session,
        analysis_run_id,
        "intent",
        {
            "source": "deterministic_rules",
            "phase_output": intent_po,
            "interpreted_goal": ig.model_dump(mode="json"),
        },
    )
    planning_steps_wire = [
        {"order": s["order"], "tool_name": s["tool_name"], "label": s.get("label", "")}
        for s in plan_po["ordered_plan"]
    ]
    merge_ai_agents_meta(
        session,
        analysis_run_id,
        "planning",
        {
            "source": "deterministic_rules",
            "phase_output": plan_po,
            "steps": planning_steps_wire,
        },
    )

    mcp_step_count = len(orch_out.step_statuses)
    base_idx = mcp_step_count

    row_meta = run_svc.require(analysis_run_id)
    base_meta = row_meta.meta_json if isinstance(row_meta.meta_json, dict) else {}
    ai_meta = dict(base_meta.get("ai_agents") or {})
    prompt_versions = dict(ai_meta.get("prompt_versions") or {})
    prompt_versions["critic"] = s.agent_critic_prompt_version
    prompt_versions["report"] = s.agent_report_prompt_version
    merge_ai_agents_meta(session, analysis_run_id, "prompt_versions", prompt_versions)

    orchestration_summary = {
        "run_id": orch_out.run_id,
        "status": orch_out.status.value,
        "message": orch_out.message,
        "final_summary": orch_out.final_summary,
        "tickers": list(orch_input.tickers),
        "analysis_goal": orch_input.analysis_goal,
        "refresh": orch_input.refresh,
        "warnings_count": len(orch_out.warnings),
        "errors_count": len(orch_out.errors),
        "step_statuses": [e.model_dump(mode="json") for e in orch_out.step_statuses],
        "errors": [e.model_dump(mode="json") for e in orch_out.errors],
        "warnings": [w.model_dump(mode="json") for w in orch_out.warnings],
    }

    output_patch: dict[str, Any] = {}

    # --- Step 3: critic (LLM) — artifact excerpts + orchestration summary ---
    critic_row = rs_steps.create(
        analysis_run_id,
        base_idx,
        label="critic_agent",
        planned_tool_name=None,
        planner_tool_input_json=None,
        meta_json={"trace": "critic_agent", "phase": "llm"},
    )
    rs_steps.transition_status(critic_row.id, RunStepStatus.running)

    critic_patch: dict[str, Any] = {"skipped": True, "phase_status": PHASE_SKIPPED}
    report_patch: dict[str, Any] = {"skipped": True, "phase_status": PHASE_SKIPPED}

    excerpts = collect_critic_excerpts(orch_out.artifact_paths)
    critic_excerpt_roles = sorted(excerpts.keys())

    if llm_provider is None:
        co_skip = build_skipped_phase_output(
            reason="llm_provider_unavailable",
            boundary_failure_class=LLM_NOT_CONFIGURED,
            phase_status=PHASE_SKIPPED,
        )
        critic_patch = {
            "phase_status": PHASE_SKIPPED,
            "skipped": True,
            "reason": "llm_provider_unavailable",
            "boundary_failure_class": LLM_NOT_CONFIGURED,
            "phase_output": co_skip,
        }
        rs_steps.merge_meta_json(
            critic_row.id,
            {
                "phase_output": co_skip,
                "boundary_failure_class": LLM_NOT_CONFIGURED,
                "phase_status": PHASE_SKIPPED,
            },
        )
        rs_steps.transition_status(
            critic_row.id,
            RunStepStatus.skipped,
            detail="No LLM provider configured for critic",
        )
    else:
        recorder = RecordedChatCompletionService(session, llm_provider)
        try:
            critic_out, critic_mc = CriticAgent(recorder, settings=s).run(
                analysis_run_id=analysis_run_id,
                orchestration_summary=orchestration_summary,
                artifact_excerpts=excerpts,
            )
        except Exception as exc:
            rs_steps.transition_status(critic_row.id, RunStepStatus.error, detail=str(exc)[:2048])
            bf = classify_llm_phase_exception(exc)
            link_mc = latest_model_call_for_agent_prompt(
                session,
                analysis_run_id,
                prompt_id=AGENT_PROMPT_IDS["critic"],
            )
            mid = str(link_mc.id) if link_mc is not None else None
            po = build_skipped_phase_output(
                reason="critic_error",
                error=str(exc)[:512],
                boundary_failure_class=bf,
                phase_status=PHASE_FAILED,
            )
            rs_steps.merge_meta_json(
                critic_row.id,
                {
                    "phase_output": po,
                    "boundary_failure_class": bf,
                    "phase_status": PHASE_FAILED,
                    "model_call_id": mid,
                },
            )
            critic_patch = {
                "phase_status": PHASE_FAILED,
                "skipped": True,
                "error": str(exc)[:2048],
                "boundary_failure_class": bf,
                "phase_output": po,
                "model_call_id": mid,
            }
        else:
            rs_steps.transition_status(critic_row.id, RunStepStatus.success)
            co = build_critic_phase_output(critic_out)
            degraded = critic_out.overall_confidence == "low"
            c_status = PHASE_DEGRADED if degraded else PHASE_SUCCESS
            rs_steps.merge_meta_json(
                critic_row.id,
                {
                    "model_call_id": str(critic_mc.id),
                    "phase_output": co,
                    "phase_status": c_status,
                    "degraded": degraded,
                },
            )
            critic_patch = {
                "phase_status": c_status,
                "skipped": False,
                "degraded": degraded,
                "model_call_id": str(critic_mc.id),
                "result": critic_out.model_dump(mode="json"),
                "phase_output": co,
                "boundary_failure_class": None,
            }

    merge_ai_agents_meta(session, analysis_run_id, "critic", critic_patch)

    # --- Step 4: report (LLM) — user-facing narrative (uses critic when present) ---
    report_row = rs_steps.create(
        analysis_run_id,
        base_idx + 1,
        label="report_agent",
        planned_tool_name=None,
        planner_tool_input_json=None,
        meta_json={"trace": "report_agent", "phase": "llm"},
    )
    rs_steps.transition_status(report_row.id, RunStepStatus.running)

    if llm_provider is None:
        ro_skip = build_skipped_phase_output(
            reason="llm_provider_unavailable",
            boundary_failure_class=LLM_NOT_CONFIGURED,
            phase_status=PHASE_SKIPPED,
        )
        report_patch = {
            "phase_status": PHASE_SKIPPED,
            "skipped": True,
            "reason": "llm_provider_unavailable",
            "boundary_failure_class": LLM_NOT_CONFIGURED,
            "phase_output": ro_skip,
        }
        rs_steps.merge_meta_json(
            report_row.id,
            {
                "phase_output": ro_skip,
                "boundary_failure_class": LLM_NOT_CONFIGURED,
                "phase_status": PHASE_SKIPPED,
            },
        )
        rs_steps.transition_status(
            report_row.id,
            RunStepStatus.skipped,
            detail="No LLM provider configured for report",
        )
    elif critic_patch.get("phase_status") not in (PHASE_SUCCESS, PHASE_DEGRADED):
        rep_reason = (
            "critic_phase_failed"
            if critic_patch.get("phase_status") == PHASE_FAILED
            else "critic_not_available"
        )
        ro_skip = build_skipped_phase_output(
            reason=rep_reason,
            boundary_failure_class=CRITIC_BLOCKED_REPORT,
            phase_status=PHASE_SKIPPED,
        )
        report_patch = {
            "phase_status": PHASE_SKIPPED,
            "skipped": True,
            "reason": rep_reason,
            "boundary_failure_class": CRITIC_BLOCKED_REPORT,
            "phase_output": ro_skip,
        }
        rs_steps.merge_meta_json(
            report_row.id,
            {
                "phase_output": ro_skip,
                "boundary_failure_class": CRITIC_BLOCKED_REPORT,
                "phase_status": PHASE_SKIPPED,
            },
        )
        rs_steps.transition_status(
            report_row.id,
            RunStepStatus.skipped,
            detail=(
                "Report skipped: critic phase failed"
                if rep_reason == "critic_phase_failed"
                else "Report skipped: critic did not run or produced no output"
            ),
        )
    else:
        critic_model = CriticAgentLLMOutput.model_validate(critic_patch["result"])
        recorder = RecordedChatCompletionService(session, llm_provider)
        try:
            report_out, report_mc = ReportAgent(recorder, settings=s).run(
                analysis_run_id=analysis_run_id,
                orchestration_summary=orchestration_summary,
                critic=critic_model,
            )
        except Exception as exc:
            rs_steps.transition_status(report_row.id, RunStepStatus.error, detail=str(exc)[:2048])
            bf = classify_llm_phase_exception(exc)
            link_mc = latest_model_call_for_agent_prompt(
                session,
                analysis_run_id,
                prompt_id=AGENT_PROMPT_IDS["report"],
            )
            r_mid = str(link_mc.id) if link_mc is not None else None
            po = build_skipped_phase_output(
                reason="report_error",
                error=str(exc)[:512],
                boundary_failure_class=bf,
                phase_status=PHASE_FAILED,
            )
            rs_steps.merge_meta_json(
                report_row.id,
                {
                    "phase_output": po,
                    "boundary_failure_class": bf,
                    "phase_status": PHASE_FAILED,
                    "model_call_id": r_mid,
                },
            )
            report_patch = {
                "phase_status": PHASE_FAILED,
                "skipped": True,
                "error": str(exc)[:2048],
                "boundary_failure_class": bf,
                "phase_output": po,
                "model_call_id": r_mid,
            }
        else:
            rs_steps.transition_status(report_row.id, RunStepStatus.success)
            ro = build_report_phase_output(report_out, orch_out.artifact_paths)
            rs_steps.merge_meta_json(
                report_row.id,
                {
                    "model_call_id": str(report_mc.id),
                    "phase_output": ro,
                    "phase_status": PHASE_SUCCESS,
                },
            )
            report_patch = {
                "phase_status": PHASE_SUCCESS,
                "skipped": False,
                "model_call_id": str(report_mc.id),
                "result": report_out.model_dump(mode="json"),
                "phase_output": ro,
                "boundary_failure_class": None,
            }
            output_patch["user_facing_report"] = {
                "markdown": report_out.user_report_markdown,
                "key_takeaways": report_out.key_takeaways,
                "model_call_id": str(report_mc.id),
            }

    merge_ai_agents_meta(session, analysis_run_id, "report", report_patch)

    merge_ai_agents_meta(
        session,
        analysis_run_id,
        "traceable_pipeline",
        {
            "mcp_step_count": mcp_step_count,
            "llm_step_indices": [base_idx, base_idx + 1],
            "critic_phase_status": critic_patch.get("phase_status"),
            "report_phase_status": report_patch.get("phase_status"),
        },
    )

    trace_full, trace_critic_step, trace_report_step = build_runtime_traceability_bundle(
        interpreted_goal=ig,
        planning_source=str(plan_po.get("source", "deterministic_rules")),
        selected_tools=planning_steps_wire,
        orch_out=orch_out,
        mcp_step_count=mcp_step_count,
        base_idx=base_idx,
        critic_patch=critic_patch,
        report_patch=report_patch,
        critic_excerpt_roles=critic_excerpt_roles,
    )
    merge_ai_agents_meta(session, analysis_run_id, "traceability", trace_full)
    rs_steps.merge_meta_json(critic_row.id, {"traceability": trace_critic_step})
    rs_steps.merge_meta_json(report_row.id, {"traceability": trace_report_step})

    output_patch["llm_phases_summary"] = build_llm_phases_summary_payload(critic_patch, report_patch)

    return TraceableEdgarPipelineResult(
        orchestration_output=orch_out,
        output_payload_patch=output_patch,
    )
