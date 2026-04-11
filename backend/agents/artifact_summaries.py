"""
Deterministic, compact artifact summaries for critic/report LLM context.

Avoids raw multi-megabyte CSV/Markdown; exposes row counts, selection rules, and top-N rows.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_DATA_QUALITY,
    ARTIFACT_KEY_DETERIORATION_FOCUS,
    ARTIFACT_KEY_EXCLUSIONS,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD,
    ARTIFACT_KEY_MANUAL_VALIDATION,
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_PEER_SIGNALS,
    ARTIFACT_KEY_REPORT,
    ARTIFACT_KEY_TREND_BREAKS,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
)

# Read bounded bytes from disk before parsing (avoid loading huge files).
_MAX_READ_BYTES = 2_000_000

_TOP_ANOMALIES = 15
_TOP_UNIFIED = 12
_TOP_DETERIORATION = 12
_TOP_FINDINGS_SUMMARY = 24
_TOP_CAVEAT_ROWS = 200
_MAX_CAVEAT_TOKENS = 40
_TOP_GENERIC_ROWS = 20
_TOP_PANEL_FEATURE_ROWS = 4
_MAX_CELL_CHARS = 120
_MARKDOWN_PREVIEW_LINES = 100
_MAX_MARKDOWN_CHARS = 10_000

SUMMARIES_CONTRACT = "artifact_summaries_v1"


def _basename(path_str: str) -> str:
    return Path(path_str).name or path_str


def _read_bytes(path_str: str) -> bytes:
    p = Path(path_str)
    if not p.is_file():
        return b""
    try:
        return p.read_bytes()[:_MAX_READ_BYTES]
    except OSError:
        return b""


def _read_text(path_str: str) -> str:
    raw = _read_bytes(path_str)
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")


def _trim_cell(v: Any, max_len: int = _MAX_CELL_CHARS) -> str:
    s = "" if v is None else str(v).strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _parse_csv_rows(text: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV text into header + row dicts (all values strings)."""
    text = text.strip()
    if not text:
        return [], []
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if reader.fieldnames is None:
        return [], []
    headers = list(reader.fieldnames)
    rows: list[dict[str, str]] = []
    for row in reader:
        rows.append({k: (row.get(k) or "") for k in headers})
    return headers, rows


def _float_safe(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def summarize_anomalies_csv(path_str: str) -> dict[str, Any]:
    text = _read_text(path_str)
    headers, rows = _parse_csv_rows(text)
    total = len(rows)
    if not rows:
        return {
            "kind": "anomalies_csv",
            "path_basename": _basename(path_str),
            "csv_data_rows_total": 0,
            "rows_selected_for_summary": 0,
            "selection_rule": "none_empty",
            "top_rows": [],
        }

    def score_row(r: dict[str, str]) -> float:
        az = r.get("abs_z") or r.get("zscore") or "0"
        return abs(_float_safe(az))

    ranked = sorted(rows, key=score_row, reverse=True)[:_TOP_ANOMALIES]
    slim_cols = (
        "cik",
        "period",
        "metric",
        "direction",
        "anomaly_category",
        "zscore",
        "abs_z",
        "combined_score",
        "combined_signal_type",
        "caveat_codes",
    )
    top_rows: list[dict[str, str]] = []
    for r in ranked:
        out: dict[str, str] = {}
        for c in slim_cols:
            if c in (r or {}):
                out[c] = _trim_cell(r.get(c, ""))
        if not out and r:
            out = {k: _trim_cell(v) for k, v in list(r.items())[:10]}
        top_rows.append(out)

    by_cat: Counter[str] = Counter()
    for r in rows:
        by_cat[str(r.get("anomaly_category") or "?")] += 1

    return {
        "kind": "anomalies_csv",
        "path_basename": _basename(path_str),
        "csv_data_rows_total": total,
        "rows_selected_for_summary": len(top_rows),
        "selection_rule": "top_rows_by_max_abs_zscore_or_abs_z",
        "anomaly_category_counts": dict(by_cat.most_common(12)),
        "top_rows": top_rows,
    }


def _summarize_scored_table(
    path_str: str,
    *,
    kind: str,
    score_keys: tuple[str, ...],
    top_n: int,
) -> dict[str, Any]:
    text = _read_text(path_str)
    headers, rows = _parse_csv_rows(text)
    total = len(rows)
    if not rows:
        return {
            "kind": kind,
            "path_basename": _basename(path_str),
            "csv_data_rows_total": 0,
            "rows_selected_for_summary": 0,
            "selection_rule": "none_empty",
            "top_rows": [],
        }

    def sc(r: dict[str, str]) -> float:
        for k in score_keys:
            if k in r and r[k]:
                return abs(_float_safe(r[k]))
        return 0.0

    ranked = sorted(rows, key=sc, reverse=True)[:top_n]
    top_rows = [{k: _trim_cell(r.get(k, "")) for k in list(r.keys())[:14]} for r in ranked]
    return {
        "kind": kind,
        "path_basename": _basename(path_str),
        "csv_data_rows_total": total,
        "rows_selected_for_summary": len(top_rows),
        "selection_rule": f"top_rows_by_{score_keys[0]}",
        "top_rows": top_rows,
    }


def summarize_unified_findings_csv(path_str: str) -> dict[str, Any]:
    return _summarize_scored_table(
        path_str,
        kind="unified_findings_csv",
        score_keys=("score_adjusted", "score_raw", "combined_score"),
        top_n=_TOP_UNIFIED,
    )


def summarize_deterioration_focus_csv(path_str: str) -> dict[str, Any]:
    return _summarize_scored_table(
        path_str,
        kind="deterioration_focus_csv",
        score_keys=("combined_score", "score", "severity"),
        top_n=_TOP_DETERIORATION,
    )


def summarize_findings_summary_csv(path_str: str, *, variant: str) -> dict[str, Any]:
    text = _read_text(path_str)
    headers, rows = _parse_csv_rows(text)
    total = len(rows)
    if not rows:
        return {
            "kind": f"findings_summary_{variant}",
            "path_basename": _basename(path_str),
            "csv_data_rows_total": 0,
            "rows_selected_for_summary": 0,
            "selection_rule": "none_empty",
            "rows": [],
        }
    # Prefer high finding_count / high_severity if present
    def sc(r: dict[str, str]) -> float:
        return _float_safe(r.get("finding_count") or "0") + 2.0 * _float_safe(
            r.get("high_severity_count") or "0"
        )

    ranked = sorted(rows, key=sc, reverse=True)[:_TOP_FINDINGS_SUMMARY]
    out_rows = [{k: _trim_cell(r.get(k, "")) for k in r.keys()} for r in ranked]
    return {
        "kind": f"findings_summary_{variant}",
        "path_basename": _basename(path_str),
        "csv_data_rows_total": total,
        "rows_selected_for_summary": len(out_rows),
        "selection_rule": "top_by_finding_count_plus_severity",
        "rows": out_rows,
    }


def summarize_metric_caveats_csv(path_str: str, *, variant: str) -> dict[str, Any]:
    text = _read_text(path_str)
    headers, rows = _parse_csv_rows(text)
    total = len(rows)
    sample = rows[:_TOP_CAVEAT_ROWS]
    token_counts: Counter[str] = Counter()
    for r in sample:
        raw = str(r.get("caveat_codes") or r.get("caveat_code") or r.get("codes") or "")
        for part in re.split(r"[;,]", raw):
            t = part.strip()
            if t:
                token_counts[t] += 1
    top_tokens = dict(token_counts.most_common(_MAX_CAVEAT_TOKENS))
    return {
        "kind": f"metric_caveats_{variant}",
        "path_basename": _basename(path_str),
        "csv_data_rows_total": total,
        "rows_sampled_for_aggregation": len(sample),
        "selection_rule": "first_N_rows_for_token_counts",
        "caveat_token_counts_top": top_tokens,
        "sample_rows": [{k: _trim_cell(r.get(k, "")) for k in list(r.keys())[:10]} for r in sample[:8]],
    }


def summarize_panel_or_features_csv(path_str: str, *, kind: str) -> dict[str, Any]:
    text = _read_text(path_str)
    headers, rows = _parse_csv_rows(text)
    total = len(rows)
    preview = []
    for r in rows[:_TOP_PANEL_FEATURE_ROWS]:
        preview.append({k: _trim_cell(r.get(k, ""), 80) for k in list(r.keys())[:16]})
    return {
        "kind": kind,
        "path_basename": _basename(path_str),
        "csv_data_rows_total": total,
        "column_names": headers[:40],
        "rows_selected_for_summary": len(preview),
        "selection_rule": "first_N_rows_first_columns_trimmed",
        "sample_rows": preview,
    }


def summarize_report_md(path_str: str) -> dict[str, Any]:
    text = _read_text(path_str)
    if not text:
        return {
            "kind": "report_md",
            "path_basename": _basename(path_str),
            "selection_rule": "empty_or_unreadable",
            "markdown_preview": "",
            "heading_lines": [],
        }
    snippet = text[:_MAX_MARKDOWN_CHARS]
    lines = snippet.splitlines()
    preview_lines = lines[:_MARKDOWN_PREVIEW_LINES]
    headings = [ln.strip() for ln in preview_lines if ln.strip().startswith("#")]
    preview_text = "\n".join(preview_lines)
    if len(preview_text) > _MAX_MARKDOWN_CHARS:
        preview_text = preview_text[: _MAX_MARKDOWN_CHARS - 1] + "…"
    return {
        "kind": "report_md",
        "path_basename": _basename(path_str),
        "char_preview_total": len(snippet),
        "lines_in_preview": len(preview_lines),
        "selection_rule": "first_lines_and_markdown_headings",
        "heading_lines": headings[:20],
        "markdown_preview": preview_text,
    }


def summarize_generic_csv(path_str: str, *, kind: str) -> dict[str, Any]:
    text = _read_text(path_str)
    headers, rows = _parse_csv_rows(text)
    total = len(rows)
    sample = rows[:_TOP_GENERIC_ROWS]
    return {
        "kind": kind,
        "path_basename": _basename(path_str),
        "csv_data_rows_total": total,
        "rows_selected_for_summary": len(sample),
        "selection_rule": "first_N_rows",
        "column_names": headers[:30],
        "rows": [{k: _trim_cell(r.get(k, "")) for k in list(r.keys())[:12]} for r in sample],
    }


def summarize_text_trustworthiness(path_str: str, *, role: str) -> dict[str, Any]:
    text = _read_text(path_str)
    cap = 4_000
    prev = text[:cap]
    return {
        "kind": "text_excerpt",
        "artifact_role": role,
        "path_basename": _basename(path_str),
        "char_total_read": len(prev),
        "selection_rule": "utf8_prefix",
        "text_preview": prev,
        "truncated": len(text) > cap,
    }


_ROLE_HANDLERS: dict[str, Callable[[str], dict[str, Any]]] = {
    ARTIFACT_KEY_ANOMALIES: summarize_anomalies_csv,
    ARTIFACT_KEY_UNIFIED_FINDINGS: summarize_unified_findings_csv,
    ARTIFACT_KEY_DETERIORATION_FOCUS: summarize_deterioration_focus_csv,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY: lambda p: summarize_findings_summary_csv(p, variant="by_company"),
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC: lambda p: summarize_findings_summary_csv(p, variant="by_metric"),
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD: lambda p: summarize_findings_summary_csv(p, variant="by_period"),
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION: lambda p: summarize_metric_caveats_csv(p, variant="extraction"),
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL: lambda p: summarize_metric_caveats_csv(p, variant="panel"),
    ARTIFACT_KEY_REPORT: summarize_report_md,
    ARTIFACT_KEY_PANEL: lambda p: summarize_panel_or_features_csv(p, kind="panel_csv"),
    ARTIFACT_KEY_FEATURES: lambda p: summarize_panel_or_features_csv(p, kind="features_csv"),
    ARTIFACT_KEY_DATA_QUALITY: lambda p: summarize_generic_csv(p, kind="data_quality_csv"),
    ARTIFACT_KEY_EXCLUSIONS: lambda p: summarize_generic_csv(p, kind="exclusions_csv"),
    ARTIFACT_KEY_MANUAL_VALIDATION: lambda p: summarize_generic_csv(p, kind="manual_validation_csv"),
    ARTIFACT_KEY_PEER_SIGNALS: lambda p: summarize_generic_csv(p, kind="peer_signals_csv"),
    ARTIFACT_KEY_TREND_BREAKS: lambda p: summarize_generic_csv(p, kind="trend_break_signals_csv"),
}


def _index_entry(role: str, path_str: str, summary: dict[str, Any]) -> dict[str, Any]:
    rows_sel = (
        summary.get("rows_selected_for_summary")
        or summary.get("rows_sampled_for_aggregation")
        or summary.get("lines_in_preview")
    )
    return {
        "artifact_role": role,
        "path_basename": _basename(path_str),
        "summary_kind": summary.get("kind"),
        "csv_data_rows_total": summary.get("csv_data_rows_total"),
        "rows_selected_for_summary": rows_sel,
        "selection_rule": summary.get("selection_rule"),
    }


def build_artifact_summaries_for_llm(artifact_paths: dict[str, str]) -> dict[str, Any]:
    """
    Build deterministic summaries for known artifact roles (paths from orchestration).

    Returns a bundle suitable for ``critic_llm_v1`` / ``report_llm_v1`` payloads.
    """
    by_role: dict[str, Any] = {}
    index: list[dict[str, Any]] = []

    # Stable priority: same order as critic excerpt plan (high-signal first).
    from backend.agents.critic_artifact_keys import CRITIC_EXCERPT_PLAN

    ordered_roles = [r for r, _ in CRITIC_EXCERPT_PLAN]
    seen: set[str] = set()
    for role in ordered_roles:
        seen.add(role)
        path_str = artifact_paths.get(role)
        if not path_str:
            continue
        fn = _ROLE_HANDLERS.get(role)
        if fn is None:
            continue
        try:
            summary = fn(path_str)
        except Exception as exc:  # noqa: BLE001 — keep pipeline resilient
            summary = {
                "kind": "error",
                "path_basename": _basename(path_str),
                "error": str(exc)[:200],
            }
        by_role[role] = summary
        index.append(_index_entry(role, path_str, summary))

    # Trustworthiness and any extra roles not in plan
    for role, path_str in sorted(artifact_paths.items()):
        if role in by_role or role in seen:
            continue
        if "trustworthiness" in role.lower():
            summary = summarize_text_trustworthiness(path_str, role=role)
            by_role[role] = summary
            index.append(_index_entry(role, path_str, summary))

    return {
        "contract_version": SUMMARIES_CONTRACT,
        "by_role": by_role,
        "artifact_index": index,
    }


def audit_summaries_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Approximate size for persistence (no full JSON duplication)."""
    by_role = bundle.get("by_role") or {}
    approx = len(json.dumps(by_role, ensure_ascii=False))
    return {
        "contract_version": bundle.get("contract_version"),
        "roles_with_summaries": sorted(by_role.keys()),
        "approx_json_chars": approx,
    }
