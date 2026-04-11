"""
Persist each orchestration planned step to :class:`~backend.models.run_step.RunStep` / ``ToolCall``.

Maps :class:`~edgar_project.orchestration.schemas.OrchestrationOutput` ``step_statuses`` to rows, attaching
MCP envelopes from :attr:`~edgar_project.orchestration.state.OrchestrationRunState.steps_completed` when the
step was executed. **No MCP calls** — DB writes only.
"""

from __future__ import annotations

from uuid import UUID

from edgar_project.orchestration.constants import STEP_STATUS_SKIPPED
from edgar_project.orchestration.schemas import OrchestrationOutput, PlannedStep
from edgar_project.orchestration.state import OrchestrationRunState
from edgar_project.mcp.schemas import ToolResponseEnvelope, ToolStatus
from sqlalchemy.orm import Session

from backend.models.enums import RunStepStatus, ToolCallMcpStatus
from backend.services.run_step_service import RunStepService
from backend.services.tool_call_service import ToolCallService


def _mcp_status_to_run_step(status: str) -> RunStepStatus:
    if status == ToolStatus.success.value:
        return RunStepStatus.success
    if status == ToolStatus.no_data.value:
        return RunStepStatus.no_data
    if status == ToolStatus.error.value:
        return RunStepStatus.error
    return RunStepStatus.error


def _tool_status_to_call_status(status: str) -> ToolCallMcpStatus:
    if status == ToolStatus.success.value:
        return ToolCallMcpStatus.success
    if status == ToolStatus.no_data.value:
        return ToolCallMcpStatus.no_data
    return ToolCallMcpStatus.error


def persist_orchestration_step_trace(
    session: Session,
    analysis_run_id: UUID,
    orch_output: OrchestrationOutput,
    run_state: OrchestrationRunState,
    *,
    step_index_base: int = 0,
    run_step_svc: RunStepService | None = None,
    tool_call_svc: ToolCallService | None = None,
) -> list[UUID]:
    """
    For each entry in ``orch_output.step_statuses``, insert a run step and (when not skipped) a tool call.

    Returns created :class:`~backend.models.run_step.RunStep` ids in order.
    """
    rs_svc = run_step_svc or RunStepService(session)
    tc_svc = tool_call_svc or ToolCallService(session)

    records_by_order = {rec.order: rec for rec in run_state.steps_completed}
    plan_by_order: dict[int, PlannedStep] = {}
    if run_state.plan is not None:
        plan_by_order = {s.order: s for s in run_state.plan.steps}
    summaries_by_order = {s.order: s for s in orch_output.tool_results_summary}

    created_ids: list[UUID] = []

    for i, sse in enumerate(orch_output.step_statuses):
        step_index = step_index_base + i
        planned = plan_by_order.get(sse.order)
        planner_input = planned.tool_input if planned is not None else None

        rs = rs_svc.create(
            analysis_run_id,
            step_index,
            label=sse.label or f"{sse.tool_name}:{sse.order}",
            planned_tool_name=sse.tool_name,
            planner_tool_input_json=planner_input,
            meta_json={
                "trace": "mcp_executor",
                "orchestration_order": sse.order,
                "step_status_entry_mcp_status": sse.mcp_status,
            },
        )
        created_ids.append(rs.id)

        if sse.mcp_status == STEP_STATUS_SKIPPED:
            rs_svc.transition_status(rs.id, RunStepStatus.skipped, detail=sse.detail)
            continue

        rs_svc.transition_status(rs.id, RunStepStatus.running)

        rec = records_by_order.get(sse.order)
        if rec is None:
            rs_svc.transition_status(
                rs.id,
                RunStepStatus.error,
                detail=sse.detail or "Missing executor StepRecord for non-skipped step",
            )
            continue

        try:
            env = ToolResponseEnvelope.model_validate(rec.envelope)
        except Exception as exc:
            tc = tc_svc.create(
                analysis_run_id,
                rs.id,
                sse.tool_name,
                request_params_json=planner_input,
            )
            tc_svc.start_execution(tc.id)
            tc_svc.record_response(
                tc.id,
                ToolCallMcpStatus.error,
                response_envelope_json=rec.envelope if rec.envelope else None,
                error_detail=str(exc)[:2048],
            )
            rs_svc.transition_status(rs.id, RunStepStatus.error, detail=str(exc)[:512])
            continue

        tc = tc_svc.create(
            analysis_run_id,
            rs.id,
            sse.tool_name,
            request_params_json=planner_input,
        )
        tc_svc.start_execution(tc.id)

        summ = summaries_by_order.get(sse.order)
        tc_svc.record_response(
            tc.id,
            _tool_status_to_call_status(env.status.value),
            response_envelope_json=rec.envelope,
            panel_row_count=summ.panel_row_count if summ is not None else None,
            feature_row_count=summ.feature_row_count if summ is not None else None,
            anomaly_count=summ.anomaly_count if summ is not None else None,
            report_character_count=summ.report_character_count if summ is not None else None,
        )

        rs_svc.transition_status(rs.id, _mcp_status_to_run_step(env.status.value))

    return created_ids
