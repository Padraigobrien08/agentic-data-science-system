"""
Explicit, configurable size limits for LLM user payloads (critic/report and shared builders).

All truncation is **deterministic** (stable ordering, head-of-list keeps highest-priority rows
where scores exist). ``ContextBudget.from_settings`` maps :class:`~backend.config.settings.Settings`.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from backend.config.settings import Settings


@dataclass(frozen=True)
class ContextBudget:
    """Defaults match previous module-level constants (behavior-stable when unset)."""

    # --- intent / planning user payloads ---
    max_user_request_chars: int = 8_000

    # --- critic & report shared (llm_context) ---
    max_goal_excerpt_chars: int = 600
    max_intent_rules_matched: int = 16
    max_template_rules_matched: int = 12
    max_plan_alignment_findings: int = 12
    max_resolved_companies: int = 24
    max_tool_result_rows: int = 32
    max_step_rows: int = 48
    max_warn_err_samples: int = 5
    max_warn_err_message_chars: int = 240
    max_run_message_chars: int = 1_000
    max_final_summary_chars: int = 2_000
    max_tool_result_artifact_keys: int = 12
    max_slim_row_keys: int = 14
    # artifact_coverage role lists (sorted; keep head — stable hash order)
    max_coverage_roles: int = 0  # 0 = unlimited

    # --- report: critic JSON embedded in context ---
    max_critic_issue_items: int = 24
    max_critic_text_field_chars: int = 8_000

    # --- artifact summarizers (per-file) ---
    max_read_bytes: int = 2_000_000
    max_anomaly_rows: int = 15
    max_unified_findings_rows: int = 12
    max_deterioration_rows: int = 12
    max_findings_summary_rows: int = 24
    max_caveat_sample_rows: int = 200
    max_caveat_token_types: int = 40
    max_caveat_detail_rows: int = 8
    max_generic_csv_rows: int = 20
    max_panel_feature_rows: int = 4
    max_panel_trim_chars: int = 80
    max_cell_chars: int = 120
    max_anomaly_category_buckets: int = 12
    max_markdown_preview_lines: int = 100
    max_markdown_chars: int = 10_000
    max_markdown_headings: int = 20
    max_trustworthiness_chars: int = 4_000
    max_generic_column_names: int = 30
    max_generic_row_columns: int = 12
    # Cap how many artifact roles appear in the critic/report bundle (plan order = priority).
    max_artifact_summary_roles: int = 0  # 0 = unlimited
    max_artifact_index_entries: int = 0  # 0 = unlimited (trim tail of index)

    @classmethod
    def from_settings(cls, s: Settings) -> ContextBudget:
        """Build from ``EDGAR_BACKEND_AGENT_CONTEXT_*`` fields (see :class:`Settings`)."""
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            attr = f"agent_context_{f.name}"
            if hasattr(s, attr):
                kwargs[f.name] = getattr(s, attr)
        return cls(**kwargs)


def _trunc_str(s: str | None, max_len: int, *, meta: dict[str, Any], key: str) -> str:
    if not s:
        return ""
    t = s.strip()
    if len(t) <= max_len:
        return t
    meta["truncated"] = True
    meta[key] = True
    return t[: max_len - 1].rstrip() + "…"


def clip_critic_for_report_llm(
    critic: dict[str, Any],
    budget: ContextBudget,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Deterministically bound critic prose/lists for the report phase.

    Returns ``(clipped_critic, truncation_meta)``.
    """
    meta: dict[str, Any] = {"truncated": False}
    out = dict(critic)
    issues = out.get("issues")
    if isinstance(issues, list) and budget.max_critic_issue_items >= 0:
        n = budget.max_critic_issue_items
        if len(issues) > n:
            out["issues"] = issues[:n]
            meta["truncated"] = True
            meta["issues_omitted_count"] = len(issues) - n
    for fld in ("findings_assessment", "caveat_coverage", "trustworthiness_notes"):
        v = out.get(fld)
        if isinstance(v, str) and len(v) > budget.max_critic_text_field_chars:
            out[fld] = _trunc_str(v, budget.max_critic_text_field_chars, meta=meta, key=f"{fld}_truncated")
    return out, meta


def clip_sorted_role_list(roles: list[str], max_items: int) -> tuple[list[str], dict[str, Any]]:
    """Stable sort then take head. ``max_items`` 0 means unlimited."""
    s = sorted(roles)
    if max_items <= 0 or len(s) <= max_items:
        return s, {"truncated": False}
    return s[:max_items], {
        "truncated": True,
        "omitted_count": len(s) - max_items,
    }
