"""
**Executor** — the only orchestration component that invokes MCP tools.

Within ``edgar_project.orchestration``, all SEC/data work goes through
``edgar_project.mcp.tools`` (see :func:`_dispatch_mcp`). There are **no** direct imports of
Phase 1 packages (e.g. code under ``src/``) here; that code stays inside MCP tools only.

Responsibilities:

* Accept :class:`~edgar_project.orchestration.execution_contract.ExecutionRequest` (public) and
  run against :class:`~edgar_project.orchestration.state.OrchestrationRunState` (in-process).
* Dispatch each :class:`~edgar_project.orchestration.schemas.PlannedStep` to the matching MCP tool;
  accumulate :class:`~edgar_project.orchestration.schemas.StepRecord` / summaries / artifact paths.
* Classify terminal :class:`~edgar_project.orchestration.schemas.OrchestrationRunStatus`
  (``success`` / ``partial_success`` / ``no_data`` / ``error``) from envelopes + orchestration rules.
* Emit :class:`~edgar_project.orchestration.schemas.OrchestrationOutput` and ``log_run_finished``.

Does **not**:

* Call :class:`~edgar_project.orchestration.planner.Planner` or re-run intent rules.
* Treat ``analysis_goal`` as anything other than audit text (see :func:`_placeholder_interpreted_goal`).
* Replace MCP with ad-hoc Phase 1 calls. Skipping a planned step without MCP (e.g. all fetches ``no_data``
  before ``build_panel``) is a documented execution shortcut, not a Phase 1 bypass.
"""

from __future__ import annotations

from datetime import datetime, timezone

from edgar_project.mcp import tools as mcp_tools
from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_REPORT,
    BuildPanelInput,
    ComputeFeaturesInput,
    DetectAnomaliesInput,
    FetchCompanyDataInput,
    GenerateReportInput,
    ResolveCompanyInput,
    RunPipelineInput,
    ToolResponseEnvelope,
    ToolStatus,
)
from edgar_project.orchestration.constants import (
    STEP_STATUS_SKIPPED,
    TOOL_BUILD_PANEL,
    TOOL_COMPUTE_FEATURES,
    TOOL_DETECT_ANOMALIES,
    TOOL_FETCH_COMPANY_DATA,
    TOOL_GENERATE_REPORT,
    TOOL_RESOLVE_COMPANY,
    TOOL_RUN_PIPELINE,
)
from edgar_project.orchestration.execution_contract import ExecutionRequest, ExecutionResult
from edgar_project.orchestration.schemas import (
    CODE_ORCH_ALL_RESOLVE_FAILED,
    CODE_ORCH_BUILD_PANEL_NO_DATA,
    CODE_ORCH_DISPATCH,
    CODE_ORCH_COMPUTE_FEATURES_FAILED,
    CODE_ORCH_DOWNSTREAM_SKIPPED,
    CODE_ORCH_FETCH_ALL_NO_DATA,
    CODE_ORCH_FETCH_TICKER_NO_DATA,
    CODE_ORCH_PARTIAL_RESOLVE,
    CODE_ORCH_REPORT_FAILED,
    CODE_ORCH_RESOLVE_TICKER_FAILED,
    CODE_ORCH_WARN_ZERO_ANOMALIES,
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationError,
    OrchestrationOutput,
    OrchestrationRunStatus,
    OrchestrationWarning,
    PlannedStep,
    ResolvedCompany,
    StepRecord,
    StepStatusEntry,
    ToolResultSummary,
)
from edgar_project.orchestration.run_logging import log_run_finished, logger, tool_summary_line
from edgar_project.orchestration.state import OrchestrationRunState


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _placeholder_interpreted_goal(request_text: str) -> InterpretedGoal:
    """
    Schema fallback when ``state.interpreted_goal`` is missing (tests or malformed state).

    This does **not** classify user intent — it only fills :class:`InterpretedGoal` so
    :class:`OrchestrationOutput` validates. Normal runs always have a planner-produced goal.
    """
    return InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="Placeholder when goal not set on state.",
        user_goal_text=request_text,
    )


def _dispatch_mcp(step: PlannedStep) -> ToolResponseEnvelope:
    """
    Single dispatch gate for MCP tools in orchestration — all tool I/O goes through here.

    Maps ``step.tool_name`` to ``edgar_project.mcp.tools.*_tool``; unknown names raise
    :class:`ValueError` (orchestration error with :data:`~edgar_project.orchestration.schemas.CODE_ORCH_DISPATCH`).
    """
    name = step.tool_name
    raw = dict(step.tool_input)

    if name == TOOL_RESOLVE_COMPANY:
        return mcp_tools.resolve_company_tool(ResolveCompanyInput(**raw))
    if name == TOOL_FETCH_COMPANY_DATA:
        return mcp_tools.fetch_company_data_tool(FetchCompanyDataInput(**raw))
    if name == TOOL_BUILD_PANEL:
        return mcp_tools.build_panel_tool(BuildPanelInput(**raw))
    if name == TOOL_COMPUTE_FEATURES:
        return mcp_tools.compute_features_tool(ComputeFeaturesInput(**raw))
    if name == TOOL_DETECT_ANOMALIES:
        return mcp_tools.detect_anomalies_tool(DetectAnomaliesInput(**raw))
    if name == TOOL_GENERATE_REPORT:
        return mcp_tools.generate_report_tool(GenerateReportInput(**raw))
    if name == TOOL_RUN_PIPELINE:
        return mcp_tools.run_pipeline_tool(RunPipelineInput(**raw))

    raise ValueError(f"Unknown MCP tool in plan: {name!r}")


def _summary_from_envelope(order: int, tool_name: str, env: ToolResponseEnvelope) -> ToolResultSummary:
    data = env.data or {}
    arts = {str(k): str(v) for k, v in (env.artifacts or {}).items()}
    ciks: list[int] = []
    if isinstance(data.get("ciks"), list):
        ciks = [int(x) for x in data["ciks"]]
    elif isinstance(data.get("provenance"), dict) and isinstance(data["provenance"].get("ciks"), list):
        ciks = [int(x) for x in data["provenance"]["ciks"]]

    panel_row: int | None = None
    feat_row: int | None = None
    anom_n: int | None = None
    rep_n = data.get("report_chars")

    if tool_name == TOOL_RUN_PIPELINE:
        pr = data.get("panel_rows")
        panel_row = int(pr) if isinstance(pr, int) else None
        fr = data.get("feature_rows")
        feat_row = int(fr) if isinstance(fr, int) else None
        ar = data.get("anomaly_rows")
        anom_n = int(ar) if isinstance(ar, int) else None
    elif tool_name == TOOL_BUILD_PANEL:
        pr = data.get("row_count")
        panel_row = int(pr) if isinstance(pr, int) else None
    elif tool_name == TOOL_COMPUTE_FEATURES:
        pr = data.get("row_count")
        feat_row = int(pr) if isinstance(pr, int) else None
    elif tool_name == TOOL_DETECT_ANOMALIES:
        fr = data.get("feature_row_count")
        feat_row = int(fr) if isinstance(fr, int) else None
        an = data.get("anomaly_count")
        anom_n = int(an) if isinstance(an, int) else None
    else:
        pr = data.get("row_count")
        panel_row = int(pr) if isinstance(pr, int) else None

    prov_keys = [k for k in ("input_tickers", "ciks", "provenance", "source") if k in data]

    return ToolResultSummary(
        order=order,
        tool_name=tool_name,
        mcp_status=env.status.value,
        panel_row_count=panel_row,
        feature_row_count=feat_row,
        anomaly_count=anom_n,
        report_character_count=int(rep_n) if isinstance(rep_n, int) else None,
        ciks_observed=ciks,
        artifact_paths=arts,
        provenance_keys=prov_keys,
    )


def _synthetic_dispatch_summary(order: int, tool_name: str) -> ToolResultSummary:
    return ToolResultSummary(
        order=order,
        tool_name=tool_name,
        mcp_status=ToolStatus.error.value,
        panel_row_count=None,
        feature_row_count=None,
        anomaly_count=None,
        report_character_count=None,
        ciks_observed=[],
        artifact_paths={},
        provenance_keys=[],
    )


def _merge_artifact_paths(accum: dict[str, str], env: ToolResponseEnvelope) -> None:
    for k, v in (env.artifacts or {}).items():
        accum[str(k)] = str(v)
    data = env.data or {}
    if isinstance(data.get("artifacts_detail"), dict):
        for role, meta in data["artifacts_detail"].items():
            if isinstance(meta, dict) and meta.get("path"):
                accum[str(role)] = str(meta["path"])
    if isinstance(data.get("report"), dict) and data["report"].get("path"):
        accum[ARTIFACT_KEY_REPORT] = str(data["report"]["path"])


def _report_path_from_env(env: ToolResponseEnvelope) -> str | None:
    arts = env.artifacts or {}
    if ARTIFACT_KEY_REPORT in arts:
        return str(arts[ARTIFACT_KEY_REPORT])
    rep = (env.data or {}).get("report")
    if isinstance(rep, dict) and rep.get("path"):
        return str(rep["path"])
    return None


def _resolved_from_resolve_success(env: ToolResponseEnvelope) -> ResolvedCompany | None:
    if env.status != ToolStatus.success:
        return None
    d = env.data or {}
    if "ticker" not in d or "cik" not in d:
        return None
    return ResolvedCompany(
        ticker=str(d["ticker"]),
        cik=int(d["cik"]),
        company_name=d.get("company_name"),
    )


def _build_step_statuses(
    plan_steps: list[PlannedStep],
    tool_summaries: list[ToolResultSummary],
) -> list[StepStatusEntry]:
    by_order = {s.order: s for s in tool_summaries}
    out: list[StepStatusEntry] = []
    for ps in sorted(plan_steps, key=lambda x: x.order):
        if ps.order in by_order:
            ts = by_order[ps.order]
            out.append(
                StepStatusEntry(
                    order=ps.order,
                    tool_name=ps.tool_name,
                    label=ps.label,
                    mcp_status=ts.mcp_status,
                    detail=None,
                )
            )
        else:
            out.append(
                StepStatusEntry(
                    order=ps.order,
                    tool_name=ps.tool_name,
                    label=ps.label,
                    mcp_status=STEP_STATUS_SKIPPED,
                    detail="Not executed (orchestration stopped earlier).",
                )
            )
    return out


# Warnings that imply the run should not be reported as plain ``success`` (but may still be
# ``partial_success`` with no ``errors``). Terminal ``no_data`` paths return before post-loop classify.
_PARTIAL_WARNING_CODES = frozenset(
    {
        CODE_ORCH_PARTIAL_RESOLVE,
        CODE_ORCH_FETCH_TICKER_NO_DATA,
        CODE_ORCH_REPORT_FAILED,
        CODE_ORCH_DOWNSTREAM_SKIPPED,
    }
)


def _successful_tool_count(summaries: list[ToolResultSummary]) -> int:
    return sum(1 for s in summaries if s.mcp_status == ToolStatus.success.value)


def _should_partial_success(
    warnings: list[OrchestrationWarning],
    errors: list[OrchestrationError],
    summaries: list[ToolResultSummary],
    artifact_paths: dict[str, str],
) -> bool:
    if any(w.code in _PARTIAL_WARNING_CODES for w in warnings):
        return True
    if errors and (_successful_tool_count(summaries) > 0 or bool(artifact_paths)):
        return True
    return False


def _classify_post_loop(
    errors: list[OrchestrationError],
    warnings: list[OrchestrationWarning],
    summaries: list[ToolResultSummary],
    artifact_paths: dict[str, str],
) -> tuple[OrchestrationRunStatus, str]:
    if _should_partial_success(warnings, errors, summaries, artifact_paths):
        if errors:
            return (
                OrchestrationRunStatus.partial_success,
                "Completed with step failures or skipped work; prior outputs are retained where available.",
            )
        return (
            OrchestrationRunStatus.partial_success,
            "Completed with partial results; see warnings.",
        )
    if errors:
        return (OrchestrationRunStatus.error, "Orchestration failed; see errors.")
    return (OrchestrationRunStatus.success, "Orchestration completed successfully.")


class Executor:
    """
    MCP execution engine for orchestration.

    See module docstring: this class is the **only** place in ``edgar_project.orchestration``
    that calls ``edgar_project.mcp.tools``.
    """

    def run(self, execution: ExecutionRequest) -> ExecutionResult:
        """Execute the planned MCP sequence (planner/executor contract entry point)."""
        return self._run_with_state(execution.to_run_state())

    def _run_with_state(self, state: OrchestrationRunState) -> OrchestrationOutput:
        # Interpreted goal comes from the planner via ExecutionRequest; never re-derived from NL here.
        ig = state.interpreted_goal or _placeholder_interpreted_goal(state.request.analysis_goal)

        if state.plan is None or not state.plan.steps:
            logger.info("[%s] execute skipped: empty plan", state.run_id)
            out = state.to_output(
                status=OrchestrationRunStatus.success,
                message="No steps to execute (empty plan).",
                interpreted_goal=ig,
                step_statuses=[],
            )
            log_run_finished(
                state.run_id,
                status=out.status,
                message=out.message,
                errors=list(out.errors),
                warnings_count=len(out.warnings),
                artifact_path_count=len(out.artifact_paths),
            )
            return out

        steps_sorted = sorted(state.plan.steps, key=lambda x: x.order)
        logger.info("[%s] execute start planned_steps=%d", state.run_id, len(steps_sorted))
        planned_resolve_tickers = [s.tool_input["ticker"] for s in steps_sorted if s.tool_name == TOOL_RESOLVE_COMPANY]
        has_fetch = any(s.tool_name == TOOL_FETCH_COMPANY_DATA for s in steps_sorted)

        resolve_ok: set[str] = set()
        resolve_fail: set[str] = set()
        fetch_mcp_statuses: list[str] = []

        errors: list[OrchestrationError] = []
        warnings: list[OrchestrationWarning] = []
        tool_summaries: list[ToolResultSummary] = []
        artifact_paths: dict[str, str] = {}
        final_report_path: str | None = None
        resolved_companies: list[ResolvedCompany] = []
        seen_cik: set[int] = set()

        aborted = False

        def _emit(
            *,
            status: OrchestrationRunStatus,
            message: str,
        ) -> OrchestrationOutput:
            ss = _build_step_statuses(steps_sorted, tool_summaries)
            out = state.to_output(
                status=status,
                message=message,
                interpreted_goal=ig,
                resolved_companies=resolved_companies,
                tool_call_sequence=state.executed_tool_call_sequence(),
                tool_results_summary=tool_summaries,
                step_statuses=ss,
                artifact_paths=artifact_paths,
                final_report_path=final_report_path,
                errors=errors,
                warnings=warnings,
            )
            log_run_finished(
                state.run_id,
                status=status,
                message=message,
                errors=errors,
                warnings_count=len(warnings),
                artifact_path_count=len(artifact_paths),
            )
            return out

        for step in steps_sorted:
            # Execution optimization: if every fetch returned no_data, skip build_panel MCP call
            # and short-circuit to no_data (still no Phase 1 imports — data path would be empty).
            if step.tool_name == TOOL_BUILD_PANEL:
                if has_fetch and fetch_mcp_statuses and all(
                    s == ToolStatus.no_data.value for s in fetch_mcp_statuses
                ):
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_FETCH_ALL_NO_DATA,
                            message="No SEC data for any ticker after fetch.",
                            source_tool=TOOL_FETCH_COMPANY_DATA,
                        )
                    )
                    logger.info(
                        "[%s] skip_dispatch order=%d tool=%s reason=all_fetches_no_data",
                        state.run_id,
                        step.order,
                        step.tool_name,
                    )
                    return _emit(
                        status=OrchestrationRunStatus.no_data,
                        message="All fetch_company_data steps returned no_data; skipping build_panel.",
                    )

            t0 = _utc_now()
            logger.info(
                "[%s] step_start order=%d tool=%s label=%r",
                state.run_id,
                step.order,
                step.tool_name,
                step.label,
            )
            try:
                env = _dispatch_mcp(step)
            except Exception as exc:
                err_rec = StepRecord(
                    tool_name=step.tool_name,
                    order=step.order,
                    envelope={
                        "status": "error",
                        "message": str(exc),
                        "errors": [{"code": CODE_ORCH_DISPATCH, "message": str(exc)}],
                    },
                    started_at=t0,
                    finished_at=_utc_now(),
                )
                state.record_step(err_rec)
                tool_summaries.append(_synthetic_dispatch_summary(step.order, step.tool_name))
                errors.append(
                    OrchestrationError(
                        code=CODE_ORCH_DISPATCH,
                        message=f"MCP dispatch failed for {step.tool_name}",
                        source_tool=step.tool_name,
                        detail=str(exc),
                    )
                )
                logger.error(
                    "[%s] step_end order=%d tool=%s dispatch_failed type=%s msg=%r",
                    state.run_id,
                    step.order,
                    step.tool_name,
                    type(exc).__name__,
                    str(exc),
                )
                aborted = True
                break

            env_dict = mcp_tools.to_json_dict(env)
            state.record_step(
                StepRecord(
                    tool_name=step.tool_name,
                    order=step.order,
                    envelope=env_dict,
                    started_at=t0,
                    finished_at=_utc_now(),
                )
            )
            tool_summaries.append(_summary_from_envelope(step.order, step.tool_name, env))
            ts = tool_summaries[-1]
            logger.info(
                "[%s] step_end order=%d tool=%s label=%r %s",
                state.run_id,
                step.order,
                step.tool_name,
                step.label,
                tool_summary_line(ts),
            )
            if env.status == ToolStatus.error and env.errors:
                logger.warning(
                    "[%s] mcp_error order=%d code=%s msg=%r",
                    state.run_id,
                    step.order,
                    env.errors[0].code,
                    env.errors[0].message,
                )
            elif env.status == ToolStatus.no_data:
                logger.info(
                    "[%s] mcp_no_data order=%d tool=%s message=%r",
                    state.run_id,
                    step.order,
                    step.tool_name,
                    env.message,
                )
            _merge_artifact_paths(artifact_paths, env)
            rp = _report_path_from_env(env)
            if rp:
                final_report_path = rp

            st = env.status

            if step.tool_name == TOOL_RESOLVE_COMPANY:
                tkr = str(step.tool_input.get("ticker", ""))
                if st == ToolStatus.success:
                    resolve_ok.add(tkr)
                    rc = _resolved_from_resolve_success(env)
                    if rc and rc.cik not in seen_cik:
                        seen_cik.add(rc.cik)
                        resolved_companies.append(rc)
                elif st == ToolStatus.error:
                    resolve_fail.add(tkr)
                    detail = env.errors[0].detail if env.errors else None
                    msg = env.errors[0].message if env.errors else env.message
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_RESOLVE_TICKER_FAILED,
                            message=f"resolve_company failed for {tkr}",
                            source_tool=TOOL_RESOLVE_COMPANY,
                            detail=msg if detail is None else f"{msg}; {detail}",
                        )
                    )

                done_resolve = len(resolve_ok) + len(resolve_fail)
                if planned_resolve_tickers and done_resolve == len(planned_resolve_tickers):
                    if not resolve_ok and resolve_fail:
                        errors.append(
                            OrchestrationError(
                                code=CODE_ORCH_ALL_RESOLVE_FAILED,
                                message="resolve_company failed for every planned ticker.",
                                source_tool=TOOL_RESOLVE_COMPANY,
                            )
                        )
                        return _emit(
                            status=OrchestrationRunStatus.error,
                            message="All ticker resolutions failed; cannot continue.",
                        )
                    if resolve_ok and resolve_fail:
                        warnings.append(
                            OrchestrationWarning(
                                code=CODE_ORCH_PARTIAL_RESOLVE,
                                message="Some tickers failed to resolve; continuing with successful symbols.",
                                source_tool=TOOL_RESOLVE_COMPANY,
                                detail=f"ok={sorted(resolve_ok)} failed={sorted(resolve_fail)}",
                            )
                        )
                continue

            if step.tool_name == TOOL_FETCH_COMPANY_DATA:
                fetch_mcp_statuses.append(env.status.value)
                tkr = str(step.tool_input.get("ticker", ""))
                if st == ToolStatus.no_data:
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_FETCH_TICKER_NO_DATA,
                            message=f"No usable SEC data for ticker {tkr}; other symbols may still proceed.",
                            source_tool=TOOL_FETCH_COMPANY_DATA,
                            detail="fetch_company_data returned no_data for this symbol.",
                        )
                    )
                if st == ToolStatus.error and env.errors:
                    e0 = env.errors[0]
                    errors.append(
                        OrchestrationError(
                            code=e0.code,
                            message=e0.message,
                            source_tool=TOOL_FETCH_COMPANY_DATA,
                            mcp_error_code=e0.code,
                            detail=e0.detail,
                        )
                    )
                continue

            if step.tool_name == TOOL_BUILD_PANEL:
                if st == ToolStatus.no_data:
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_BUILD_PANEL_NO_DATA,
                            message=env.message or "Empty panel",
                            source_tool=TOOL_BUILD_PANEL,
                        )
                    )
                    return _emit(
                        status=OrchestrationRunStatus.no_data,
                        message="build_panel returned no_data; stopping.",
                    )
                if st == ToolStatus.error and env.errors:
                    e0 = env.errors[0]
                    errors.append(
                        OrchestrationError(
                            code=e0.code,
                            message=e0.message,
                            source_tool=TOOL_BUILD_PANEL,
                            mcp_error_code=e0.code,
                            detail=e0.detail,
                        )
                    )
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_DOWNSTREAM_SKIPPED,
                            message="compute_features, detect_anomalies, and generate_report were skipped after build_panel failed.",
                            source_tool=TOOL_BUILD_PANEL,
                        )
                    )
                    break
                continue

            if step.tool_name == TOOL_COMPUTE_FEATURES:
                if st == ToolStatus.error and env.errors:
                    e0 = env.errors[0]
                    errors.append(
                        OrchestrationError(
                            code=CODE_ORCH_COMPUTE_FEATURES_FAILED,
                            message=e0.message,
                            source_tool=TOOL_COMPUTE_FEATURES,
                            mcp_error_code=e0.code,
                            detail=e0.detail,
                        )
                    )
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_DOWNSTREAM_SKIPPED,
                            message="detect_anomalies and generate_report were skipped after compute_features failed.",
                            source_tool=TOOL_COMPUTE_FEATURES,
                        )
                    )
                    break
                continue

            if step.tool_name == TOOL_DETECT_ANOMALIES:
                if st == ToolStatus.success:
                    data = env.data or {}
                    ac = data.get("anomaly_count")
                    if ac == 0:
                        warnings.append(
                            OrchestrationWarning(
                                code=CODE_ORCH_WARN_ZERO_ANOMALIES,
                                message="Anomaly detection returned zero flagged rows.",
                                source_tool=TOOL_DETECT_ANOMALIES,
                            )
                        )
                if st == ToolStatus.error and env.errors:
                    e0 = env.errors[0]
                    errors.append(
                        OrchestrationError(
                            code=e0.code,
                            message=e0.message,
                            source_tool=TOOL_DETECT_ANOMALIES,
                            mcp_error_code=e0.code,
                            detail=e0.detail,
                        )
                    )
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_DOWNSTREAM_SKIPPED,
                            message="generate_report was skipped after detect_anomalies failed.",
                            source_tool=TOOL_DETECT_ANOMALIES,
                        )
                    )
                    break
                continue

            if step.tool_name == TOOL_GENERATE_REPORT:
                if st == ToolStatus.success and final_report_path is None:
                    final_report_path = _report_path_from_env(env)
                if st == ToolStatus.error and env.errors:
                    e0 = env.errors[0]
                    errors.append(
                        OrchestrationError(
                            code=e0.code,
                            message=e0.message,
                            source_tool=TOOL_GENERATE_REPORT,
                            mcp_error_code=e0.code,
                            detail=e0.detail,
                        )
                    )
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_REPORT_FAILED,
                            message="Report generation failed; anomaly and feature artifacts remain available.",
                            source_tool=TOOL_GENERATE_REPORT,
                            detail=e0.message,
                        )
                    )
                if st == ToolStatus.no_data:
                    warnings.append(
                        OrchestrationWarning(
                            code=CODE_ORCH_REPORT_FAILED,
                            message="Report generation returned no_data; prior steps produced usable artifacts where applicable.",
                            source_tool=TOOL_GENERATE_REPORT,
                            detail=env.message,
                        )
                    )
                continue

            if step.tool_name == TOOL_RUN_PIPELINE:
                if st == ToolStatus.no_data:
                    return _emit(
                        status=OrchestrationRunStatus.no_data,
                        message="run_pipeline returned no_data.",
                    )
                if st == ToolStatus.error and env.errors:
                    e0 = env.errors[0]
                    errors.append(
                        OrchestrationError(
                            code=e0.code,
                            message=e0.message,
                            source_tool=TOOL_RUN_PIPELINE,
                            mcp_error_code=e0.code,
                            detail=e0.detail,
                        )
                    )
                    return _emit(
                        status=OrchestrationRunStatus.error,
                        message="run_pipeline failed.",
                    )
                continue

        if aborted:
            return _emit(
                status=OrchestrationRunStatus.error,
                message="Orchestration aborted after dispatch failure.",
            )

        st_final, msg_final = _classify_post_loop(errors, warnings, tool_summaries, artifact_paths)
        return _emit(status=st_final, message=msg_final)
