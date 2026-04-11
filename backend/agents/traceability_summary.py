"""
Cross-phase decision summaries for run inspection (no chain-of-thought, no raw prompts).

Persisted under ``analysis_run.meta_json['ai_agents']['traceability']``. Optional enrichment
with artifact UUIDs runs after pipeline artifact ingest (:func:`enrich_traceability_artifact_ids`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from edgar_project.orchestration.schemas import InterpretedGoal, OrchestrationOutput

from backend.agents.llm_phase_status import PHASE_DEGRADED, PHASE_FAILED, PHASE_SUCCESS
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService

TRACEABILITY_CONTRACT_VERSION = "1"

_MAX_INTENT_SUMMARY = 280
_MAX_CAVEAT_ITEMS = 12
_MAX_TAKEAWAY_PREVIEW = 5
_MAX_ARTIFACT_REFS = 24


def _trunc(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _evidence_refs(artifact_paths: dict[str, str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for role, path_str in sorted(artifact_paths.items()):
        if not path_str or not str(path_str).strip():
            continue
        out.append({"role": role, "basename": Path(str(path_str)).name})
        if len(out) >= _MAX_ARTIFACT_REFS:
            break
    return out


def _blocking_caveats_from_critic_patch(patch: dict[str, Any]) -> tuple[list[str], str | None]:
    if patch.get("skipped"):
        caveats: list[str] = []
        r = patch.get("reason")
        if r:
            caveats.append(str(r))
        err = patch.get("error")
        if err:
            caveats.append(_trunc(str(err), 240))
        po = patch.get("phase_output")
        if isinstance(po, dict) and po.get("reason") and str(po["reason"]) not in caveats:
            caveats.insert(0, str(po["reason"]))
        return caveats[:_MAX_CAVEAT_ITEMS], None

    res = patch.get("result")
    if not isinstance(res, dict):
        return [], None
    issues = [str(x) for x in (res.get("issues") or []) if x][: _MAX_CAVEAT_ITEMS]
    conf = res.get("overall_confidence")
    if conf == "low":
        issues = ["overall_confidence: low"] + issues
    return issues[:_MAX_CAVEAT_ITEMS], str(conf) if isinstance(conf, str) else None


def build_runtime_traceability_bundle(
    *,
    interpreted_goal: InterpretedGoal,
    planning_source: str,
    selected_tools: list[dict[str, Any]],
    orch_out: OrchestrationOutput,
    mcp_step_count: int,
    base_idx: int,
    critic_patch: dict[str, Any],
    report_patch: dict[str, Any],
    critic_excerpt_roles: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Returns ``(full_traceability, critic_run_step_meta, report_run_step_meta)``.

    Prompt text is intentionally omitted; references are structural (roles, indices, tool names).
    """
    ig = interpreted_goal
    intent_summary = (
        f"Template {ig.code.value}"
        + (f" ({ig.intent.value})" if ig.intent else "")
        + f": {_trunc(ig.description, _MAX_INTENT_SUMMARY)}"
    )

    tool_names = [str(s.get("tool_name", "")) for s in selected_tools if s.get("tool_name")]
    planning_summary = (
        f"Planner ({planning_source}) selected {len(selected_tools)} step(s): "
        f"{' → '.join(tool_names) if tool_names else '—'}"
    )
    rationale_planning = (
        "Rule-based planner mapped analysis_goal + tickers to a fixed MCP tool sequence."
        if planning_source == "deterministic_rules"
        else "LLM planning agent emitted an allowlisted tool sequence validated before any execution."
    )

    blocking, conf = _blocking_caveats_from_critic_patch(critic_patch)
    c_phase = critic_patch.get("phase_status")
    critic_ran = c_phase in (PHASE_SUCCESS, PHASE_DEGRADED)
    critic_failed = c_phase == PHASE_FAILED
    critic_decision = (
        f"Critic reviewed structured orchestration summary and {len(critic_excerpt_roles)} "
        f"artifact excerpt role(s): {', '.join(critic_excerpt_roles[:8])}"
        + ("…" if len(critic_excerpt_roles) > 8 else "")
        if critic_excerpt_roles
        else "Critic had no on-disk artifact excerpts for configured roles (paths missing or empty)."
    )
    if critic_failed:
        critic_decision = f"Critic phase failed ({critic_patch.get('reason', 'critic_error')})."
    elif not critic_ran:
        critic_decision = (
            f"Critic did not produce a structured review ({critic_patch.get('reason', 'skipped')})."
        )

    report_ran = report_patch.get("phase_status") == PHASE_SUCCESS
    report_res = report_patch.get("result") if isinstance(report_patch.get("result"), dict) else {}
    takeaways = [str(x) for x in (report_res.get("key_takeaways") or []) if x][:_MAX_TAKEAWAY_PREVIEW]

    if report_ran:
        report_rationale = (
            "Report model consumed JSON-only inputs: orchestration_summary + critic structured fields "
            "(findings assessment, caveat coverage, trustworthiness notes, issues, confidence). "
            "System prompt text is not duplicated here."
        )
    else:
        report_rationale = (
            f"Report not generated: {report_patch.get('reason', 'skipped')}."
        )

    full: dict[str, Any] = {
        "contract_version": TRACEABILITY_CONTRACT_VERSION,
        "intent": {
            "decision_summary": intent_summary,
        },
        "planning": {
            "decision_summary": planning_summary,
            "selected_tools": list(selected_tools),
            "rationale_summary": rationale_planning,
        },
        "execution": {
            "decision_summary": (
                f"Executor ran {mcp_step_count} planned MCP step(s); "
                f"orchestration_status={orch_out.status.value}."
            ),
            "orchestration_message": _trunc(orch_out.message, 320),
        },
        "critic": {
            "phase_status": c_phase,
            "decision_summary": critic_decision,
            "blocking_caveats": blocking,
            "overall_confidence": conf,
            "ran": critic_ran,
            "excerpt_roles_used": list(critic_excerpt_roles),
        },
        "report": {
            "phase_status": report_patch.get("phase_status"),
            "rationale_summary": report_rationale,
            "key_takeaways_preview": takeaways,
            "ran": report_ran,
        },
        "step_indices": {
            "mcp_first": 0 if mcp_step_count else None,
            "mcp_last": mcp_step_count - 1 if mcp_step_count else None,
            "critic": base_idx,
            "report": base_idx + 1,
        },
        "evidence_artifact_refs": _evidence_refs(orch_out.artifact_paths),
    }

    critic_step_meta = {
        "blocking_caveats": blocking[:8],
        "overall_confidence": conf,
        "excerpt_roles_used": critic_excerpt_roles[:12],
        "decision_summary": _trunc(critic_decision, 400),
        "traceability_doc": "Full cross-phase record: meta_json.ai_agents.traceability",
    }
    report_step_meta = {
        "rationale_summary": _trunc(report_rationale, 400),
        "key_takeaways_preview": takeaways[:3],
        "traceability_doc": "Full cross-phase record: meta_json.ai_agents.traceability",
    }

    return full, critic_step_meta, report_step_meta


def enrich_traceability_artifact_ids(session: Session, analysis_run_id: UUID) -> None:
    """
    After artifacts are ingested, attach ``evidence_artifact_ids`` and ``evidence_artifacts_by_role``.

    Safe no-op if ``traceability`` is missing.
    """
    run_svc = AnalysisRunService(session)
    row = run_svc.require(analysis_run_id)
    meta = row.meta_json if isinstance(row.meta_json, dict) else {}
    ai = dict(meta.get("ai_agents") or {})
    tr = ai.get("traceability")
    if not isinstance(tr, dict):
        return

    arts = ArtifactService(session).list_for_analysis_run(analysis_run_id)
    by_role: dict[str, str] = {}
    for a in arts:
        by_role[a.role_key] = str(a.id)
    ids_ordered: list[str] = []
    seen: set[str] = set()
    for a in arts:
        sid = str(a.id)
        if sid not in seen:
            seen.add(sid)
            ids_ordered.append(sid)

    tr = {
        **tr,
        "evidence_artifact_ids": ids_ordered,
        "evidence_artifacts_by_role": by_role,
    }
    ai["traceability"] = tr
    run_svc.merge_meta_json(analysis_run_id, {"ai_agents": ai})
