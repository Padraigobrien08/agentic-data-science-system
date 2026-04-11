"""
Deterministic plan-vs-goal alignment checks for the critic phase.

Produces typed findings (no re-planning, no LLM). Safe to persist alongside LLM critic output.
"""

from __future__ import annotations

from typing import Any

from edgar_project.mcp.schemas import ARTIFACT_KEY_DETERIORATION_FOCUS
from edgar_project.orchestration.schemas import (
    DirectionalFocus,
    InterpretedGoal,
    PlanTemplateId,
    PreferredSignalStyle,
    PrimaryAnalysisMode,
    PeerRequirement,
)

_MAX_FINDINGS = 8

_SEVERITY_HIGH = "high"
_SEVERITY_WARNING = "warning"
_SEVERITY_INFO = "info"


def _finding(code: str, severity: str, detail: str) -> dict[str, Any]:
    return {"code": code, "severity": severity, "detail": detail[:640]}


def _text_hints_deterioration_or_persistent(analysis_goal: str) -> bool:
    t = analysis_goal.lower()
    return any(
        k in t
        for k in (
            "deteriorat",
            "declin",
            "persistent",
            "sustain",
            "weaken",
            "worsen",
            "downward",
            "multi-period",
            "multi period",
            "trend",
        )
    )


def _text_hints_peer(analysis_goal: str) -> bool:
    t = analysis_goal.lower()
    return "peer" in t or "versus" in t or " vs " in t or "relative" in t


def compute_plan_alignment_findings(
    interpreted_goal: InterpretedGoal,
    *,
    analysis_goal: str,
    artifact_paths: dict[str, str],
) -> list[dict[str, Any]]:
    """
    High-value alignment checks only.

    Codes:
      * ``plan_goal_mismatch`` — stated analytical objective vs chosen template/profile.
      * ``weak_alignment_with_persistent_signal_request`` — user wants sustained patterns; plan is point-anomaly-first.
      * ``missing_directional_focus`` — directional lens unlikely to be foregrounded by the chosen plan shape.
      * ``missing_priority_metric_coverage`` — stated metric priorities or deterioration bundle may be under-emphasized.
    """
    out: list[dict[str, Any]] = []
    ig = interpreted_goal
    prefs = ig.goal_preferences
    pt = ig.plan_template
    paths = artifact_paths or {}

    if pt is None:
        out.append(
            _finding(
                "plan_goal_mismatch",
                _SEVERITY_WARNING,
                "No plan template snapshot on interpreted_goal; cannot verify goal–plan alignment.",
            )
        )
        return out[:_MAX_FINDINGS]

    tid = pt.template_id

    # --- preference-based checks (primary) ---
    if prefs is not None:
        pam = prefs.primary_analysis_mode
        pss = prefs.preferred_signal_style
        df = prefs.directional_focus
        pm = list(prefs.priority_metrics)
        peer_req = prefs.peer_requirement

        if pam == PrimaryAnalysisMode.deterioration:
            if tid not in (PlanTemplateId.trend_deterioration, PlanTemplateId.mixed_trend_and_anomaly):
                out.append(
                    _finding(
                        "plan_goal_mismatch",
                        _SEVERITY_HIGH,
                        f"primary_analysis_mode={pam.value} (deterioration) but template={tid.value}. "
                        f"Expected trend_deterioration or mixed_trend_and_anomaly for multi-period "
                        f"deterioration workflows.",
                    )
                )

        if pam == PrimaryAnalysisMode.trend and tid == PlanTemplateId.anomaly_unusual_changes:
            out.append(
                _finding(
                    "plan_goal_mismatch",
                    _SEVERITY_HIGH,
                    f"primary_analysis_mode={pam.value} (trends) but template={tid.value} "
                    f"(granular anomaly screen). Prefer run_pipeline templates for trend-first bundles.",
                )
            )

        if pam == PrimaryAnalysisMode.peer_comparison and tid != PlanTemplateId.peer_comparison:
            out.append(
                _finding(
                    "plan_goal_mismatch",
                    _SEVERITY_HIGH,
                    f"primary_analysis_mode={pam.value} but template={tid.value} "
                    f"(expected peer_comparison).",
                )
            )

        if peer_req == PeerRequirement.required and tid != PlanTemplateId.peer_comparison:
            out.append(
                _finding(
                    "plan_goal_mismatch",
                    _SEVERITY_WARNING,
                    f"peer_requirement={peer_req.value} but template={tid.value} (not peer_comparison).",
                )
            )

        if pss == PreferredSignalStyle.persistent and tid == PlanTemplateId.anomaly_unusual_changes:
            out.append(
                _finding(
                    "weak_alignment_with_persistent_signal_request",
                    _SEVERITY_WARNING,
                    f"preferred_signal_style={pss.value} with template={tid.value} "
                    f"(granular, point-in-time). Trend-first run_pipeline templates better match "
                    f"sustained-pattern asks unless the user explicitly wanted a z-score screen.",
                )
            )

        if df in (DirectionalFocus.negative, DirectionalFocus.positive) and tid == PlanTemplateId.anomaly_unusual_changes:
            out.append(
                _finding(
                    "missing_directional_focus",
                    _SEVERITY_WARNING,
                    f"directional_focus={df.value} but template={tid.value} surfaces large moves in "
                    f"both directions first — downstream narrative may need explicit directional framing.",
                )
            )

        if len(pm) > 0 and tid == PlanTemplateId.anomaly_unusual_changes:
            metrics_s = ",".join(x.value for x in pm[:5])
            out.append(
                _finding(
                    "missing_priority_metric_coverage",
                    _SEVERITY_INFO,
                    f"priority_metrics=[{metrics_s}] with template={tid.value}: per-metric ordering in "
                    f"the narrative is not guaranteed on the granular path.",
                )
            )

    # Deterioration-oriented runs should surface deterioration_focus in artifact paths when pipeline completed.
    wants_det_artifact = False
    if prefs is not None and prefs.primary_analysis_mode == PrimaryAnalysisMode.deterioration:
        wants_det_artifact = True
    if not wants_det_artifact and _text_hints_deterioration_or_persistent(analysis_goal):
        wants_det_artifact = True
    if (
        wants_det_artifact
        and tid in (PlanTemplateId.trend_deterioration, PlanTemplateId.mixed_trend_and_anomaly)
        and ARTIFACT_KEY_DETERIORATION_FOCUS not in paths
    ):
        out.append(
            _finding(
                "missing_priority_metric_coverage",
                _SEVERITY_WARNING,
                "Deterioration-oriented plan expects deterioration_focus_csv in artifact paths; "
                "it is missing from the merged orchestration map (ingest or pipeline gap).",
            )
        )

    # --- lightweight text fallback when preferences are thin ---
    if prefs is None or prefs.primary_analysis_mode == PrimaryAnalysisMode.mixed:
        if _text_hints_deterioration_or_persistent(analysis_goal) and tid == PlanTemplateId.anomaly_unusual_changes:
            out.append(
                _finding(
                    "plan_goal_mismatch",
                    _SEVERITY_WARNING,
                    "Goal text suggests deterioration or persistent trends, but execution used the "
                    "anomaly-only granular plan (anomaly_unusual_changes).",
                )
            )
        if _text_hints_peer(analysis_goal) and tid != PlanTemplateId.peer_comparison:
            out.append(
                _finding(
                    "plan_goal_mismatch",
                    _SEVERITY_INFO,
                    "Goal text mentions peers or relative comparison, but the selected template is not peer_comparison.",
                )
            )

    # Dedupe by code+detail (first wins)
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in out:
        key = (str(row.get("code", "")), str(row.get("detail", ""))[:120])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:_MAX_FINDINGS]
