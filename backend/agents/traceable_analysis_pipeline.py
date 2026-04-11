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
from backend.agents.persist_mcp_trace import persist_orchestration_step_trace
from backend.agents.report_agent import ReportAgent
from backend.agents.ai_agents_meta import merge_ai_agents_meta
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

    critic_patch: dict[str, Any] = {"skipped": True}
    report_patch: dict[str, Any] = {"skipped": True}

    if llm_provider is None:
        critic_patch = {"skipped": True, "reason": "llm_provider_unavailable"}
        rs_steps.transition_status(
            critic_row.id,
            RunStepStatus.skipped,
            detail="No LLM provider configured for critic",
        )
    else:
        excerpts = collect_critic_excerpts(orch_out.artifact_paths)
        recorder = RecordedChatCompletionService(session, llm_provider)
        try:
            critic_out, critic_mc = CriticAgent(recorder, settings=s).run(
                analysis_run_id=analysis_run_id,
                orchestration_summary=orchestration_summary,
                artifact_excerpts=excerpts,
            )
        except Exception as exc:
            rs_steps.transition_status(critic_row.id, RunStepStatus.error, detail=str(exc)[:2048])
            critic_patch = {"skipped": True, "error": str(exc)[:2048]}
        else:
            rs_steps.transition_status(critic_row.id, RunStepStatus.success)
            rs_steps.merge_meta_json(critic_row.id, {"model_call_id": str(critic_mc.id)})
            critic_patch = {
                "skipped": False,
                "model_call_id": str(critic_mc.id),
                "result": critic_out.model_dump(mode="json"),
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
        report_patch = {"skipped": True, "reason": "llm_provider_unavailable"}
        rs_steps.transition_status(
            report_row.id,
            RunStepStatus.skipped,
            detail="No LLM provider configured for report",
        )
    elif critic_patch.get("skipped"):
        report_patch = {"skipped": True, "reason": "critic_not_available"}
        rs_steps.transition_status(
            report_row.id,
            RunStepStatus.skipped,
            detail="Report skipped because critic did not produce output",
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
            report_patch = {"skipped": True, "error": str(exc)[:2048]}
        else:
            rs_steps.transition_status(report_row.id, RunStepStatus.success)
            rs_steps.merge_meta_json(report_row.id, {"model_call_id": str(report_mc.id)})
            report_patch = {
                "skipped": False,
                "model_call_id": str(report_mc.id),
                "result": report_out.model_dump(mode="json"),
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
        },
    )

    return TraceableEdgarPipelineResult(
        orchestration_output=orch_out,
        output_payload_patch=output_patch,
    )
