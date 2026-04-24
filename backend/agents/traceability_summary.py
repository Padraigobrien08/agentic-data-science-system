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

from edgar_project.orchestration.planning_transparency import build_planning_transparency
from edgar_project.orchestration.schemas import InterpretedGoal, OrchestrationOutput

from backend.agents.llm_phase_status import PHASE_DEGRADED, PHASE_FAILED, PHASE_SUCCESS
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService

TRACEABILITY_CONTRACT_VERSION = "1"

_MAX_INTENT_SUMMARY = 280
_MAX_CAVEAT_ITEMS = 12
_MAX_TAKEAWAY_PREVIEW = 5
_MAX_ARTIFACT_REFS = 24
_MAX_NARRATIVE_SECTIONS = 3
_MAX_CONFIDENCE_EXPLAINER_ITEMS = 4


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


def _safe_text(value: Any, *, max_len: int = 360) -> str:
    return _trunc(str(value), max_len) if isinstance(value, str) and value.strip() else ""


def _build_narrative_sections(
    *,
    whats_happening: str,
    why_we_think_that: str,
    what_weakens_claim: str,
) -> list[dict[str, str]]:
    rows = [
        ("What's happening", whats_happening),
        ("Why we think that", why_we_think_that),
        ("What weakens the claim", what_weakens_claim),
    ]
    sections: list[dict[str, str]] = []
    for heading, body in rows:
        clean = _safe_text(body)
        if not clean:
            continue
        sections.append({"heading": heading, "body": clean})
        if len(sections) >= _MAX_NARRATIVE_SECTIONS:
            break
    return sections


def _fallback_thesis_from_report(
    *,
    report_res: dict[str, Any],
    blocking_caveats: list[str],
) -> str:
    takeaways = [str(x).strip() for x in (report_res.get("key_takeaways") or []) if str(x).strip()]
    if takeaways:
        return _trunc(takeaways[0], 320)
    if blocking_caveats:
        return "The run completed, but the evidence is too limited to support a full narrative answer."
    return "The run completed, but the report phase did not produce a usable narrative preview."


def _build_report_narrative_preview(
    *,
    report_patch: dict[str, Any],
    blocking_caveats: list[str],
) -> dict[str, Any]:
    phase_status = str(report_patch.get("phase_status") or "")
    report_res = report_patch.get("result") if isinstance(report_patch.get("result"), dict) else {}
    thesis = _safe_text(report_res.get("narrative_thesis"))
    sections = _build_narrative_sections(
        whats_happening=_safe_text(report_res.get("narrative_whats_happening")),
        why_we_think_that=_safe_text(report_res.get("narrative_why_we_think_that")),
        what_weakens_claim=_safe_text(report_res.get("narrative_what_weakens_claim")),
    )
    if phase_status == PHASE_SUCCESS and thesis and sections:
        return {
            "mode": "full",
            "thesis": thesis,
            "sections": sections,
            "fallback_reason": None,
        }

    fallback_reason = (
        "limited_evidence"
        if phase_status == PHASE_SUCCESS
        else "report_unavailable"
    )
    weakens = blocking_caveats[0] if blocking_caveats else ""
    if not weakens:
        weakens = (
            "The report phase could not support a full narrative answer with the currently summarized evidence."
            if fallback_reason == "limited_evidence"
            else "The report phase did not return enough structured narrative detail to support a full answer."
        )
    partial_sections = _build_narrative_sections(
        whats_happening="",
        why_we_think_that="",
        what_weakens_claim=weakens,
    )
    return {
        "mode": "partial",
        "thesis": _fallback_thesis_from_report(
            report_res=report_res,
            blocking_caveats=blocking_caveats,
        ),
        "sections": partial_sections,
        "fallback_reason": fallback_reason,
    }


def _dedupe_trimmed(items: list[str], *, max_items: int = _MAX_CONFIDENCE_EXPLAINER_ITEMS) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = _safe_text(item, max_len=280)
        if not clean:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
        if len(out) >= max_items:
            break
    return out


def _build_confidence_explainer(
    *,
    critic_patch: dict[str, Any],
    report_patch: dict[str, Any],
    blocking_caveats: list[str],
    critic_summary_roles: list[str],
    plan_alignment_findings: list[dict[str, Any]],
) -> dict[str, list[str]]:
    critic_res = critic_patch.get("result") if isinstance(critic_patch.get("result"), dict) else {}
    report_res = report_patch.get("result") if isinstance(report_patch.get("result"), dict) else {}
    supports: list[str] = []
    weakens: list[str] = []
    limits: list[str] = []

    findings_assessment = _safe_text(critic_res.get("findings_assessment"))
    if findings_assessment:
        supports.append(findings_assessment)

    takeaways = [str(x).strip() for x in (report_res.get("key_takeaways") or []) if str(x).strip()]
    if takeaways:
        supports.append(_trunc(takeaways[0], 280))

    if critic_summary_roles:
        supports.append(
            f"The critic reviewed summarized evidence from {len(critic_summary_roles)} artifact role(s)."
        )

    for issue in blocking_caveats:
        if issue.casefold() == "overall_confidence: low":
            continue
        weakens.append(issue)

    caveat_coverage = _safe_text(critic_res.get("caveat_coverage"))
    if caveat_coverage:
        weakens.append(caveat_coverage)

    trustworthiness_notes = _safe_text(critic_res.get("trustworthiness_notes"))
    if trustworthiness_notes:
        limits.append(trustworthiness_notes)

    for finding in plan_alignment_findings:
        detail = _safe_text(finding.get("detail"), max_len=240)
        if detail:
            limits.append(detail)

    if not critic_summary_roles:
        limits.append("The critic did not have summarized artifact roles loaded for this run.")

    if report_patch.get("phase_status") != PHASE_SUCCESS:
        limits.append("The report phase did not complete successfully, so confidence is based on critic and traceability output only.")

    return {
        "supports": _dedupe_trimmed(supports),
        "weakens": _dedupe_trimmed(weakens),
        "limits": _dedupe_trimmed(limits),
    }


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
    critic_summary_roles: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Returns ``(full_traceability, critic_run_step_meta, report_run_step_meta)``.

    Prompt text is intentionally omitted; references are structural (roles, indices, tool names).
    """
    ig = interpreted_goal
    pt = ig.plan_template
    plan_part = f" / plan_template={pt.template_id.value}" if pt else ""
    intent_summary = (
        f"Template {ig.code.value}{plan_part}"
        + (f" ({ig.intent.value})" if ig.intent else "")
        + f": {_trunc(ig.description, _MAX_INTENT_SUMMARY)}"
    )
    planning_tx = build_planning_transparency(ig)

    tool_names = [str(s.get("tool_name", "")) for s in selected_tools if s.get("tool_name")]
    planning_summary = (
        f"Planner ({planning_source}) selected {len(selected_tools)} step(s): "
        f"{' → '.join(tool_names) if tool_names else '—'}"
    )
    rationale_planning = (
        "Rule-based planner mapped analysis_goal + tickers to a named plan template and MCP sequence."
        if planning_source == "deterministic_rules"
        else "LLM planning agent emitted an allowlisted tool sequence validated before any execution."
    )

    blocking, conf = _blocking_caveats_from_critic_patch(critic_patch)
    c_phase = critic_patch.get("phase_status")
    critic_ran = c_phase in (PHASE_SUCCESS, PHASE_DEGRADED)
    critic_failed = c_phase == PHASE_FAILED
    critic_po = critic_patch.get("phase_output")
    plan_align: list[Any] = []
    plan_align_codes: list[str] = []
    if isinstance(critic_po, dict):
        raw_pa = critic_po.get("plan_alignment_findings")
        if isinstance(raw_pa, list):
            plan_align = [x for x in raw_pa if isinstance(x, dict)][:12]
            plan_align_codes = [str(x.get("code", "")) for x in plan_align if x.get("code")]
    critic_decision = (
        f"Critic reviewed structured orchestration summary and {len(critic_summary_roles)} "
        f"artifact summary role(s): {', '.join(critic_summary_roles[:8])}"
        + ("…" if len(critic_summary_roles) > 8 else "")
        if critic_summary_roles
        else "Critic had no on-disk artifact summaries for configured roles (paths missing or empty)."
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
            "Report model consumed compact JSON (report_llm_v1): run/request/interpreted_goal, critic "
            "structured fields, tool_scope, warnings/errors samples, artifact_coverage, and compact artifact_summaries. "
            "System prompt text is not duplicated here."
        )
    else:
        report_rationale = (
            f"Report not generated: {report_patch.get('reason', 'skipped')}."
        )
    narrative_answer = _build_report_narrative_preview(
        report_patch=report_patch,
        blocking_caveats=blocking,
    )
    confidence_explainer = _build_confidence_explainer(
        critic_patch=critic_patch,
        report_patch=report_patch,
        blocking_caveats=blocking,
        critic_summary_roles=critic_summary_roles,
        plan_alignment_findings=plan_align,
    )

    full: dict[str, Any] = {
        "contract_version": TRACEABILITY_CONTRACT_VERSION,
        "intent": {
            "decision_summary": intent_summary,
            "planning_transparency": planning_tx,
        },
        "planning": {
            "decision_summary": planning_summary,
            "selected_tools": list(selected_tools),
            "rationale_summary": rationale_planning,
            "planning_transparency": planning_tx,
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
            "confidence_explainer": confidence_explainer,
            "ran": critic_ran,
            "artifact_summary_roles_used": list(critic_summary_roles),
            "plan_alignment_findings": plan_align,
            "plan_alignment_codes": plan_align_codes,
        },
        "report": {
            "phase_status": report_patch.get("phase_status"),
            "rationale_summary": report_rationale,
            "key_takeaways_preview": takeaways,
            "narrative_answer": narrative_answer,
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
        "artifact_summary_roles_used": critic_summary_roles[:12],
        "decision_summary": _trunc(critic_decision, 400),
        "plan_alignment_codes": plan_align_codes[:12],
        "traceability_doc": "Full cross-phase record: meta_json.ai_agents.traceability",
    }
    report_step_meta = {
        "rationale_summary": _trunc(report_rationale, 400),
        "key_takeaways_preview": takeaways[:3],
        "narrative_answer_mode": narrative_answer["mode"],
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
