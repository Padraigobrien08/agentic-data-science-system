"""
Typed transparency slices for Sprint 3 UX — derived from ``meta_json`` / ``phase_output`` / artifacts.

Used by :func:`GET /v1/runs/{id}` and :func:`GET /v1/runs/{id}/steps` when ``include_transparency=true``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from backend.models.artifact import Artifact
from backend.schemas.llm_usage import LlmRunUsageSummaryWire


def _as_dict(meta_json: dict | list | None) -> dict[str, Any] | None:
    return meta_json if isinstance(meta_json, dict) else None


def _parse_uuid(val: Any) -> UUID | None:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    if isinstance(val, str):
        try:
            return UUID(val.strip())
        except ValueError:
            return None
    return None


def _parse_uuid_list(raw: Any) -> list[UUID]:
    if not isinstance(raw, list):
        return []
    out: list[UUID] = []
    for x in raw:
        u = _parse_uuid(x)
        if u is not None:
            out.append(u)
    return out


def _parse_role_to_uuid_map(raw: Any) -> dict[str, UUID]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, UUID] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        u = _parse_uuid(v)
        if u is not None:
            out[k] = u
    return out


def _parse_string_list(raw: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
            if limit is not None and len(out) >= limit:
                break
    return out


class RunTransparencySummary(BaseModel):
    """Cross-run audit fields extracted without requiring clients to parse ``meta_json``."""

    evidence_artifact_ids: list[UUID] = Field(
        default_factory=list,
        description="UUIDs from ``ai_agents.traceability.evidence_artifact_ids`` when set; "
        "otherwise all artifact IDs registered for this run (ingest order).",
    )
    evidence_artifacts_by_role: dict[str, UUID] = Field(
        default_factory=dict,
        description="``role_key`` → artifact id from traceability enrichment when present.",
    )
    prompt_versions: dict[str, str] | None = Field(
        None,
        description="``meta_json.ai_agents.prompt_versions`` (agent role → template version).",
    )
    model_call_count: int = Field(
        0,
        ge=0,
        description="Count of ``model_calls`` rows for this analysis run (see also GET .../model-calls).",
    )
    llm_usage: LlmRunUsageSummaryWire | None = Field(
        None,
        description="Per-phase token/latency/cost rollup when computed (see GET .../llm-usage).",
    )
    report_key_takeaways_preview: list[str] = Field(
        default_factory=list,
        description="Safe report-preview takeaways from ``ai_agents.traceability.report.key_takeaways_preview``.",
    )
    critic_blocking_caveats: list[str] = Field(
        default_factory=list,
        description="Safe critic caveats from ``ai_agents.traceability.critic.blocking_caveats``.",
    )
    critic_overall_confidence: str | None = Field(
        None,
        description="Critic confidence label from ``ai_agents.traceability.critic.overall_confidence``.",
    )
    critic_phase_status: str | None = Field(
        None,
        description="Critic phase status from ``ai_agents.traceability.critic.phase_status``.",
    )
    report_phase_status: str | None = Field(
        None,
        description="Report phase status from ``ai_agents.traceability.report.phase_status``.",
    )
    narrative_answer: "NarrativeAnswerPreview | None" = Field(
        None,
        description="Safe narrative preview from ``ai_agents.traceability.report.narrative_answer``.",
    )


class NarrativeAnswerSectionPreview(BaseModel):
    """One bounded prose block in the safe narrative preview."""

    heading: str
    body: str


class NarrativeAnswerPreview(BaseModel):
    """Chat-safe narrative answer contract derived from traceability."""

    mode: str
    thesis: str
    sections: list[NarrativeAnswerSectionPreview] = Field(default_factory=list)
    fallback_reason: str | None = None


def _parse_narrative_answer(raw: Any) -> NarrativeAnswerPreview | None:
    if not isinstance(raw, dict):
        return None
    thesis = raw.get("thesis")
    if not isinstance(thesis, str) or not thesis.strip():
        return None
    mode = raw.get("mode")
    if not isinstance(mode, str) or not mode.strip():
        return None
    sections: list[NarrativeAnswerSectionPreview] = []
    for item in raw.get("sections") or []:
        if not isinstance(item, dict):
            continue
        heading = item.get("heading")
        body = item.get("body")
        if not isinstance(heading, str) or not heading.strip():
            continue
        if not isinstance(body, str) or not body.strip():
            continue
        sections.append(NarrativeAnswerSectionPreview(heading=heading.strip(), body=body.strip()))
    fallback_reason = raw.get("fallback_reason")
    return NarrativeAnswerPreview(
        mode=mode.strip(),
        thesis=thesis.strip(),
        sections=sections,
        fallback_reason=fallback_reason.strip() if isinstance(fallback_reason, str) and fallback_reason.strip() else None,
    )


def build_run_transparency_summary(
    meta_json: dict | list | None,
    *,
    model_call_count: int,
    artifacts: list[Artifact],
    llm_usage: LlmRunUsageSummaryWire | None = None,
) -> RunTransparencySummary:
    meta = _as_dict(meta_json)
    prompt_versions: dict[str, str] | None = None
    evidence_ids: list[UUID] | None = None
    by_role: dict[str, UUID] | None = None
    report_key_takeaways_preview: list[str] = []
    critic_blocking_caveats: list[str] = []
    critic_overall_confidence: str | None = None
    critic_phase_status: str | None = None
    report_phase_status: str | None = None
    narrative_answer: NarrativeAnswerPreview | None = None

    if meta:
        ai = meta.get("ai_agents")
        if isinstance(ai, dict):
            pv = ai.get("prompt_versions")
            if isinstance(pv, dict):
                prompt_versions = {str(k): str(v) for k, v in pv.items() if isinstance(k, str) and v is not None}
                if not prompt_versions:
                    prompt_versions = None
            tr = ai.get("traceability")
            if isinstance(tr, dict):
                if "evidence_artifact_ids" in tr:
                    evidence_ids = _parse_uuid_list(tr.get("evidence_artifact_ids"))
                if "evidence_artifacts_by_role" in tr:
                    by_role = _parse_role_to_uuid_map(tr.get("evidence_artifacts_by_role"))
                critic = tr.get("critic")
                if isinstance(critic, dict):
                    critic_blocking_caveats = _parse_string_list(
                        critic.get("blocking_caveats"),
                        limit=6,
                    )
                    oc = critic.get("overall_confidence")
                    critic_overall_confidence = str(oc).strip() if isinstance(oc, str) and str(oc).strip() else None
                    cps = critic.get("phase_status")
                    critic_phase_status = str(cps).strip() if isinstance(cps, str) and str(cps).strip() else None
                report = tr.get("report")
                if isinstance(report, dict):
                    report_key_takeaways_preview = _parse_string_list(
                        report.get("key_takeaways_preview"),
                        limit=8,
                    )
                    narrative_answer = _parse_narrative_answer(report.get("narrative_answer"))
                    rps = report.get("phase_status")
                    report_phase_status = str(rps).strip() if isinstance(rps, str) and str(rps).strip() else None

    if evidence_ids is None:
        evidence_ids = [a.id for a in artifacts]
    if by_role is None:
        by_role = {a.role_key: a.id for a in artifacts}

    return RunTransparencySummary(
        evidence_artifact_ids=evidence_ids,
        evidence_artifacts_by_role=by_role,
        prompt_versions=prompt_versions,
        model_call_count=model_call_count,
        llm_usage=llm_usage,
        report_key_takeaways_preview=report_key_takeaways_preview,
        critic_blocking_caveats=critic_blocking_caveats,
        critic_overall_confidence=critic_overall_confidence,
        critic_phase_status=critic_phase_status,
        report_phase_status=report_phase_status,
        narrative_answer=narrative_answer,
    )


class RunStepOutputSummary(BaseModel):
    """Compact view of ``RunStep.meta_json.phase_output`` (and skip flags) for UI tables."""

    phase_status: str | None = Field(None, description="LLM phase outcome when present on step meta.")
    skipped: bool | None = Field(None, description="True when phase_output indicates a skipped phase.")
    skip_reason: str | None = Field(None, description="Reason string when skipped or failed early.")
    issue_count: int | None = Field(None, description="Critic structured issue count.")
    overall_confidence: str | None = Field(None, description="Critic overall_confidence when present.")
    key_takeaway_count: int | None = Field(None, description="Report phase_output key_takeaways length.")
    markdown_char_count: int | None = Field(None, description="Report markdown length from phase_output.")
    step_count: int | None = Field(None, description="Planning-style step_count when present on phase_output.")
    artifact_roles: list[str] = Field(
        default_factory=list,
        description="``role`` keys from phase_output.artifact_refs when present.",
    )
    weak_evidence_signals: list[str] = Field(
        default_factory=list,
        description="Critic-style hints from ``phase_output.weak_evidence_signals`` when present.",
    )


def _output_summary_from_phase_output(po: dict[str, Any]) -> RunStepOutputSummary:
    skipped = bool(po.get("skipped")) if "skipped" in po else None
    reason = po.get("reason")
    skip_reason = str(reason) if isinstance(reason, str) else None
    ps = po.get("phase_status")
    phase_status = str(ps) if isinstance(ps, str) else None

    issue_count: int | None = None
    raw_ic = po.get("issue_count")
    if isinstance(raw_ic, int):
        issue_count = raw_ic

    oc = po.get("overall_confidence")
    overall_confidence = str(oc) if isinstance(oc, str) else None

    kt = po.get("key_takeaways")
    key_takeaway_count = len(kt) if isinstance(kt, list) else None

    mcc = po.get("markdown_char_count")
    markdown_char_count = int(mcc) if isinstance(mcc, int) else None

    sc = po.get("step_count")
    step_count = int(sc) if isinstance(sc, int) else None

    roles: list[str] = []
    refs = po.get("artifact_refs")
    if isinstance(refs, list):
        for r in refs:
            if isinstance(r, dict):
                role = r.get("role")
                if isinstance(role, str) and role:
                    roles.append(role)

    weak_signals: list[str] = []
    wes = po.get("weak_evidence_signals")
    if isinstance(wes, list):
        for x in wes:
            if isinstance(x, str) and x.strip():
                weak_signals.append(x.strip())

    return RunStepOutputSummary(
        phase_status=phase_status,
        skipped=skipped,
        skip_reason=skip_reason,
        issue_count=issue_count,
        overall_confidence=overall_confidence,
        key_takeaway_count=key_takeaway_count,
        markdown_char_count=markdown_char_count,
        step_count=step_count,
        artifact_roles=roles,
        weak_evidence_signals=weak_signals,
    )


class RunStepTransparencyView(BaseModel):
    """Slim step-level audit row; large blobs stay in ``meta_json`` when ``include_payloads`` is used."""

    trace: str | None = Field(
        None,
        description="Executor lane discriminator, e.g. ``mcp_executor``, ``critic_agent``, ``report_agent``.",
    )
    phase: str | None = Field(None, description="Optional ``phase`` tag from step meta (e.g. ``llm``).")
    model_call_id: UUID | None = Field(None, description="Linked ``ModelCall.id`` when persisted on the step.")
    output_summary: RunStepOutputSummary | None = Field(
        None,
        description="Structured subset of ``meta_json.phase_output`` for MCP/LLM steps.",
    )
    linked_artifact_ids: list[UUID] = Field(
        default_factory=list,
        description="Artifact rows whose ``run_step_id`` points at this step.",
    )


def build_run_step_transparency(
    meta_json: dict | list | None,
    linked_artifact_ids: list[UUID],
) -> RunStepTransparencyView:
    meta = _as_dict(meta_json)
    trace: str | None = None
    phase: str | None = None
    model_call_id: UUID | None = None
    output_summary: RunStepOutputSummary | None = None

    if meta:
        t = meta.get("trace")
        trace = str(t) if isinstance(t, str) else None
        p = meta.get("phase")
        phase = str(p) if isinstance(p, str) else None
        model_call_id = _parse_uuid(meta.get("model_call_id"))
        po = meta.get("phase_output")
        if isinstance(po, dict) and po:
            output_summary = _output_summary_from_phase_output(po)

    return RunStepTransparencyView(
        trace=trace,
        phase=phase,
        model_call_id=model_call_id,
        output_summary=output_summary,
        linked_artifact_ids=list(linked_artifact_ids),
    )
