"""
Concise, auditable planning transparency (no chain-of-thought).

Derived deterministically from :class:`~edgar_project.orchestration.schemas.InterpretedGoal`
for persistence on runs and trace UI.
"""

from __future__ import annotations

from typing import Any

from edgar_project.orchestration.schemas import InterpretedGoal

_MAX_RATIONALE = 900
_MAX_EXCERPT = 400


def _trunc(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _dedupe_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        x = str(x).strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def build_planning_transparency(interpreted_goal: InterpretedGoal | None) -> dict[str, Any]:
    """
    Structured fields for critique and UI:

    * ``planning_rationale_summary`` — short prose stitched from rule ids (not model CoT).
    * ``orchestration_intent`` — coarse :class:`~edgar_project.orchestration.schemas.OrchestrationIntent`
      from ``intent.py`` (contrasts with ``goal_code``, which reflects the chosen template).
    * ``emphasized`` / ``deemphasized`` — what the plan foregrounds vs down-ranks.
    * Flat preference mirrors for machine consumers alongside ``selected_signal_preferences``.
    """
    if interpreted_goal is None:
        return {
            "contract_version": "1",
            "present": False,
        }

    ig = interpreted_goal
    pt = ig.plan_template
    prefs = ig.goal_preferences

    sel_prefs: dict[str, Any] | None = None
    if prefs is not None:
        sel_prefs = {
            "primary_analysis_mode": prefs.primary_analysis_mode.value,
            "preferred_signal_style": prefs.preferred_signal_style.value,
            "directional_focus": prefs.directional_focus.value,
            "time_focus": prefs.time_focus.value,
            "peer_requirement": prefs.peer_requirement.value,
            "priority_metrics": [m.value for m in prefs.priority_metrics],
            "preference_rules_matched": list(prefs.preference_rules_matched),
        }

    emphasized: list[str] = []
    deemphasized: list[str] = []

    if pt is not None:
        emphasized.extend(str(x) for x in pt.report_emphasis if str(x).strip())
        if pt.persistence_filtering_required:
            deemphasized.append(
                "Isolated one-off spikes when not corroborated by multi-period stress."
            )
        if not pt.peer_analysis_mandatory:
            deemphasized.append(
                "Peer-relative ranking as optional context unless findings warrant it."
            )

    if prefs is not None:
        pss = prefs.preferred_signal_style.value
        if pss == "persistent":
            emphasized.append("Sustained multi-period patterns over single-quarter noise.")
            deemphasized.append("One-quarter-only anomaly reads unless extreme.")
        elif pss == "one_off":
            emphasized.append("Point-in-time outliers and |z|-style highlights.")
            deemphasized.append("Slow trend-only narratives unless clearly material.")

        df = prefs.directional_focus.value
        if df == "negative":
            emphasized.append("Downside moves, margin pressure, and cash strain.")
            deemphasized.append("Upside-only storytelling unless risk-relevant.")
        elif df == "positive":
            emphasized.append("Strengths, growth, and constructive signals.")
            deemphasized.append("Minor negative blips unless material.")

    emphasized = _dedupe_preserve(emphasized)[:12]
    deemphasized = _dedupe_preserve(deemphasized)[:12]

    rationale_parts: list[str] = []
    rationale_parts.append(
        f"Classified the request as «{ig.code.value}» using deterministic rules on the goal text."
    )
    if ig.intent is not None:
        rationale_parts.append(
            f"Coarse orchestration intent is «{ig.intent.value}» (intent.py); "
            "template choice also uses goal_preferences when intent is anomaly_analysis."
        )
    if ig.intent_rules_matched:
        joined = ", ".join(ig.intent_rules_matched[:10])
        suffix = "…" if len(ig.intent_rules_matched) > 10 else ""
        rationale_parts.append(f"Intent cues matched: {joined}{suffix}.")
    if pt is not None:
        rationale_parts.append(
            f"Selected plan template «{pt.template_id.value}» "
            f"({pt.mcp_execution_profile} MCP execution profile)."
        )
        if pt.template_rules_matched:
            rationale_parts.append(
                "Template selection rules: "
                + ", ".join(pt.template_rules_matched[:8])
                + ("…" if len(pt.template_rules_matched) > 8 else "")
                + "."
            )
    if prefs is not None and prefs.preference_rules_matched:
        rationale_parts.append(
            "Preference extraction rules: "
            + ", ".join(prefs.preference_rules_matched[:10])
            + ("…" if len(prefs.preference_rules_matched) > 10 else "")
            + "."
        )

    planning_rationale_summary = _trunc(" ".join(rationale_parts), _MAX_RATIONALE)

    return {
        "contract_version": "1",
        "present": True,
        "planning_rationale_summary": planning_rationale_summary,
        "plan_template_id": pt.template_id.value if pt is not None else None,
        "goal_code": ig.code.value,
        "orchestration_intent": ig.intent.value if ig.intent is not None else None,
        "intent_rules_matched": list(ig.intent_rules_matched),
        "selected_signal_preferences": sel_prefs,
        "priority_metrics": list(sel_prefs["priority_metrics"]) if sel_prefs else [],
        "directional_focus": sel_prefs["directional_focus"] if sel_prefs else None,
        "preferred_signal_style": sel_prefs["preferred_signal_style"] if sel_prefs else None,
        "peer_requirement": sel_prefs["peer_requirement"] if sel_prefs else None,
        "time_focus": sel_prefs["time_focus"] if sel_prefs else None,
        "primary_analysis_mode": sel_prefs["primary_analysis_mode"] if sel_prefs else None,
        "what_we_understood": _trunc(ig.description, _MAX_EXCERPT),
        "user_goal_echo_excerpt": _trunc(ig.user_goal_text, 280),
        "emphasized": emphasized,
        "deemphasized": deemphasized,
    }
