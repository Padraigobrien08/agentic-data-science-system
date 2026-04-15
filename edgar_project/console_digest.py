"""
Compact stdout summary for orchestration runs (CLI).

Reads artifact CSVs only for counts and top-N rows — no full report dump.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from edgar_project.orchestration.constants import (
    TOOL_BUILD_PANEL,
    TOOL_COMPUTE_FEATURES,
    TOOL_DETECT_ANOMALIES,
    TOOL_FETCH_COMPANY_DATA,
    TOOL_GENERATE_REPORT,
    TOOL_RESOLVE_COMPANY,
    TOOL_RUN_PIPELINE,
)

# --- layout -----------------------------------------------------------------

_SEP = "─" * 52
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DATA_README = _REPO_ROOT / "data" / "README.md"

_ARROW = " → "

# InterpretedGoalCode.value → short CLI plan label (digest only; spaces for readability).
_CLI_PLAN_LABELS: dict[str, str] = {
    "anomaly_unusual_changes": "anomaly analysis",
    "anomaly_for_companies": "anomaly analysis",
    "full_pipeline": "anomaly analysis",
    "trend_deterioration": "trend / deterioration pipeline",
    "mixed_trend_and_anomaly": "mixed trend + anomaly pipeline",
    "peer_comparison": "peer report",
    "resolve_only": "resolve only",
    "fetch_raw": "fetch raw",
    "planning_failed": "planning failed",
}

_TOOL_CLI_LABELS: dict[str, str] = {
    TOOL_RESOLVE_COMPANY: "resolve",
    TOOL_FETCH_COMPANY_DATA: "fetch",
    TOOL_BUILD_PANEL: "panel",
    TOOL_COMPUTE_FEATURES: "features",
    TOOL_DETECT_ANOMALIES: "anomalies",
    TOOL_GENERATE_REPORT: "report",
    TOOL_RUN_PIPELINE: "pipeline",
}

_PRIMARY_ARTIFACT_LABELS: tuple[tuple[str, str], ...] = (
    ("report_md", "Report (Markdown)"),
    ("unified_findings_csv", "Unified findings"),
    ("anomalies_csv", "Anomalies"),
    ("panel_csv", "Panel (processed)"),
    ("features_csv", "Features (processed)"),
    ("trend_break_signals_csv", "Trend-break signals"),
    ("peer_signals_csv", "Peer signals"),
    ("data_quality_csv", "Data quality summary"),
    ("metric_coverage_summary_csv", "Metric coverage"),
    ("manual_validation_csv", "Manual validation candidates"),
)

_FILE_LABEL_W = max(len(lbl) for _, lbl in _PRIMARY_ARTIFACT_LABELS) + 1


def _find_data_subdir(path: Path, sub: str) -> Path | None:
    """Return .../data/<sub> if ``path`` lies under that directory."""
    try:
        path = path.resolve()
    except OSError:
        return None
    for d in path.parents:
        if d.name == sub and len(d.parts) >= 2 and d.parent.name == "data":
            return d
    return None


def _find_run_workspace_root(path: Path) -> Path | None:
    """Return .../data/runs/<run_scoped_id> when ``path`` lies under a run workspace."""
    try:
        path = path.resolve()
    except OSError:
        return None
    for d in path.parents:
        if d.name not in {"processed", "artifacts"}:
            continue
        run_root = d.parent
        if run_root.parent.name == "runs" and run_root.parent.parent.name == "data":
            return run_root.resolve()
    return None


def _roots_touched(artifact_paths: dict[str, str]) -> dict[str, Path]:
    """Which top-level ``data/*`` roots appear in this run's paths."""
    found: dict[str, Path] = {}
    for p in artifact_paths.values():
        if not p or not str(p).strip():
            continue
        hit = _find_run_workspace_root(Path(p))
        if hit is not None:
            found["run_workspace"] = hit
            break
    order = ("raw", "processed", "artifacts", "evaluation")
    for sub in order:
        for p in artifact_paths.values():
            if not p or not str(p).strip():
                continue
            hit = _find_data_subdir(Path(p), sub)
            if hit is not None:
                found[sub] = hit.resolve()
                break
    return found


def _cli_plan_label(plan_code: str) -> str:
    return _CLI_PLAN_LABELS.get(plan_code, plan_code)


def _tool_name_to_cli_label(tool_name: str) -> str:
    return _TOOL_CLI_LABELS.get(tool_name, tool_name)


def _ordered_tool_names_from_run(
    step_statuses: list[Any] | None,
    tool_call_sequence: list[Any] | None,
) -> list[str]:
    """Prefer full planned order (``step_statuses``); else tools actually run."""
    entries: list[tuple[int, str]] = []
    src = step_statuses if step_statuses else tool_call_sequence
    if not src:
        return []
    for e in src:
        try:
            entries.append((int(e.order), str(e.tool_name)))
        except (TypeError, ValueError, AttributeError):
            continue
    entries.sort(key=lambda x: x[0])
    return [t for _, t in entries]


def format_cli_steps_summary(
    *,
    step_statuses: list[Any] | None = None,
    tool_call_sequence: list[Any] | None = None,
) -> str | None:
    """
    Map MCP tool names to short labels, preserve order, collapse repeated stages
    (e.g. per-ticker resolve/fetch) for a single readable chain.
    """
    names = _ordered_tool_names_from_run(step_statuses, tool_call_sequence)
    if not names:
        return None
    labels = [_tool_name_to_cli_label(n) for n in names]
    collapsed: list[str] = []
    for lb in labels:
        if not collapsed or collapsed[-1] != lb:
            collapsed.append(lb)
    return _ARROW.join(collapsed)


# Run digest header: label column so values align in narrow terminals.
_KV_LABEL_W = 11


def _digest_kv(label: str, value: str) -> str:
    """One key/value line with aligned values (label includes trailing colon)."""
    return f"  {label:<{_KV_LABEL_W}} {value}"


def _truncate(s: str, max_len: int) -> str:
    t = " ".join(s.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _cik_label(cik: Any, ticker_by_cik: dict[int, str]) -> str:
    try:
        k = int(float(cik))
    except (TypeError, ValueError):
        return str(cik)
    t = ticker_by_cik.get(k)
    return f"{t} (CIK {k})" if t else f"CIK {k}"


def _ticker_map_from_resolved(resolved: list[Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for c in resolved:
        try:
            out[int(c.cik)] = str(c.ticker).strip().upper()
        except (TypeError, ValueError, AttributeError):
            continue
    return out


def _distinct_metric_count(uf: pd.DataFrame | None, an: pd.DataFrame | None) -> int:
    """Distinct non-empty ``metric`` values across unified findings and anomalies."""
    names: set[str] = set()
    for df in (uf, an):
        if df is None or df.empty or "metric" not in df.columns:
            continue
        ser = df["metric"].dropna().astype(str).str.strip()
        names.update(m for m in ser if m)
    return len(names)


def _read_csv_if_exists(path_str: str | None) -> pd.DataFrame | None:
    if not path_str or not str(path_str).strip():
        return None
    p = Path(path_str)
    if not p.is_file():
        return None
    try:
        return pd.read_csv(p)
    except Exception:
        return None


def _ticker_symbol(cik: Any, ticker_by_cik: dict[int, str]) -> str:
    try:
        k = int(float(cik))
    except (TypeError, ValueError):
        return str(cik)
    return ticker_by_cik.get(k, f"CIK {k}")


def _pick_anomaly_display_z(row: pd.Series) -> tuple[float | None, str]:
    """
    Return (z to print, context) where context is ``history`` (self zscore) or ``peers`` (LOO z_score_peer).
    Uses whichever has larger absolute value when both exist.
    """
    z1 = pd.to_numeric(row.get("zscore"), errors="coerce")
    z2 = pd.to_numeric(row.get("z_score_peer"), errors="coerce") if "z_score_peer" in row.index else float("nan")
    a1 = abs(float(z1)) if pd.notna(z1) else 0.0
    a2 = abs(float(z2)) if pd.notna(z2) else 0.0
    if a1 == 0 and a2 == 0:
        return None, "history"
    if a2 > a1 and pd.notna(z2):
        return float(z2), "peers"
    if pd.notna(z1):
        return float(z1), "history"
    if pd.notna(z2):
        return float(z2), "peers"
    return None, "history"


def _format_anomaly_fallback_lines(
    an: pd.DataFrame,
    ticker_by_cik: dict[int, str],
    *,
    top_n: int,
) -> list[str]:
    """Compact lines for digest when unified findings are empty."""
    if an.empty or "cik" not in an.columns:
        return ["   (anomalies file empty or missing cik column)"]

    work = an.copy()
    if "zscore" in work.columns:
        z1 = pd.to_numeric(work["zscore"], errors="coerce").abs()
    else:
        z1 = pd.Series(0.0, index=work.index)
    if "z_score_peer" in work.columns:
        z2 = pd.to_numeric(work["z_score_peer"], errors="coerce").abs()
    else:
        z2 = pd.Series(0.0, index=work.index)
    work["_abs_rank"] = pd.concat([z1, z2], axis=1).max(axis=1, skipna=True).fillna(0.0)
    work = work.sort_values("_abs_rank", ascending=False, kind="mergesort").head(max(1, top_n))

    lines: list[str] = []
    for i, (_, row) in enumerate(work.iterrows(), start=1):
        sym = _ticker_symbol(row.get("cik"), ticker_by_cik)
        period = row.get("period", "")
        metric = row.get("metric", "")
        z_val, z_src = _pick_anomaly_display_z(row)
        if z_val is None:
            lines.append(f"   {i}. {sym}  {period}  {metric}  (no z-score)")
            continue
        z_s = f"{z_val:.3g}"
        dr = str(row.get("direction", "")).strip().lower()
        if dr in ("high", "up"):
            hl = "high"
        elif dr in ("low", "down"):
            hl = "low"
        else:
            hl = "high" if z_val > 0 else "low"
        ctx = "self-history" if z_src == "history" else "peer LOO"
        lines.append(f"   {i}. {sym}  {period}  {metric}  z={z_s}  ({hl} vs {ctx})")
    return lines


def _digest_interpretation_sentence(
    *,
    n_uf: int,
    n_an: int,
    uf: pd.DataFrame | None,
    an: pd.DataFrame | None,
    uf_ciks: set[int],
    an_ciks: set[int],
) -> str:
    """
    Single deterministic line: what the unified/anomaly counts imply (no LLM).
    """
    if n_uf > 0 and uf is not None:
        x = len(uf_ciks)
        if "metric" in uf.columns:
            ser = uf["metric"].dropna().astype(str).str.strip()
            y = int(ser[ser != ""].nunique())
        else:
            y = 0
        cx = "company" if x == 1 else "companies"
        my = "metric" if y == 1 else "metrics"
        rw = "row" if n_uf == 1 else "rows"
        return f"{n_uf} combined finding {rw} across {x} {cx} and {y} distinct {my}."

    if n_an > 0 and an is not None:
        x = len(an_ciks)
        cx = "company" if x == 1 else "companies"
        rw = "row" if n_an == 1 else "rows"
        return f"No combined findings; {n_an} anomaly {rw} across {x} {cx}."

    return "No combined findings and no anomaly rows under current thresholds."


def _empty_unified_note_lines(*, n_an: int) -> list[str]:
    """
    When unified findings are empty: run is OK; absence reflects thresholds, not a crash.
    """
    out = [
        " Note",
        "   No combined findings met the current thresholds (self-history + peer rules).",
    ]
    if n_an > 0:
        out.append("   Run finished OK — strongest per-metric anomalies are listed below.")
    else:
        out.append("   Run finished OK — no anomaly rows in artifacts.")
    return out


def format_run_digest(
    *,
    status: str,
    tickers: list[str],
    run_id: str,
    plan_code: str,
    one_line_summary: str,
    final_report_path: str | None,
    artifact_paths: dict[str, str],
    resolved_companies: list[Any],
    top_findings_n: int = 5,
    step_statuses: list[Any] | None = None,
    tool_call_sequence: list[Any] | None = None,
) -> list[str]:
    """
    Build human-readable lines (no trailing newlines on items — join with \\n).
    """
    lines: list[str] = []
    tk = " ".join(str(t).strip().upper() for t in tickers) or "—"
    lines.append(_SEP)
    lines.append(" Run summary")
    lines.append(_SEP)
    lines.append(_digest_kv("status:", status))
    lines.append(_digest_kv("tickers:", tk))
    lines.append(_digest_kv("run_id:", run_id))
    lines.append(_digest_kv("plan:", _cli_plan_label(plan_code)))
    steps_line = format_cli_steps_summary(
        step_statuses=step_statuses,
        tool_call_sequence=tool_call_sequence,
    )
    if steps_line:
        lines.append(_digest_kv("steps:", steps_line))
    if one_line_summary:
        lines.append(_digest_kv("summary:", _truncate(one_line_summary, 120)))
    lines.append("")

    lines.append(" Where outputs go")
    lines.append("   data/raw/                            — SEC cache (live fetch)")
    lines.append("   data/runs/<run_scoped_id>/processed — panel & features")
    lines.append("   data/runs/<run_scoped_id>/artifacts — anomalies, combined findings, report")
    lines.append("   data/evaluation/                     — benchmarks only (not this pipeline)")
    if _DATA_README.is_file():
        lines.append(f"   More: {_DATA_README}")

    roots = _roots_touched(artifact_paths)
    if roots:
        lines.append(" Roots touched this run:")
        if "run_workspace" in roots:
            lines.append(f"   • {'run workspace':12}  {roots['run_workspace']}")
        for key in ("processed", "artifacts", "raw", "evaluation"):
            if key in roots:
                lines.append(f"   • {key:12}  {roots[key]}")

    lines.append("")
    lines.append(" Key files (this run)")
    printed = False
    report_p = (final_report_path or "").strip() or artifact_paths.get("report_md", "")
    if report_p:
        lines.append(f"   {'Report (Markdown)':<{_FILE_LABEL_W}} {report_p}")
        printed = True
    for key, label in _PRIMARY_ARTIFACT_LABELS:
        if key == "report_md":
            continue
        pth = artifact_paths.get(key)
        if pth and str(pth).strip():
            lines.append(f"   {label:<{_FILE_LABEL_W}} {pth}")
            printed = True
    if not printed:
        lines.append("   (no artifact paths in response)")

    lines.append("")

    ticker_by_cik = _ticker_map_from_resolved(resolved_companies)

    uf_path = artifact_paths.get("unified_findings_csv")
    an_path = artifact_paths.get("anomalies_csv")
    uf = _read_csv_if_exists(uf_path)
    an = _read_csv_if_exists(an_path)

    n_uf = int(len(uf)) if uf is not None else 0
    n_an = int(len(an)) if an is not None else 0

    uf_ciks: set[int] = set()
    if uf is not None and "cik" in uf.columns:
        for x in uf["cik"].dropna().unique():
            try:
                uf_ciks.add(int(float(x)))
            except (TypeError, ValueError):
                pass
    an_ciks: set[int] = set()
    if an is not None and "cik" in an.columns:
        for x in an["cik"].dropna().unique():
            try:
                an_ciks.add(int(float(x)))
            except (TypeError, ValueError):
                pass
    cos = uf_ciks | an_ciks
    n_metrics = _distinct_metric_count(uf, an)

    _cl = 22  # label column (counts + key files)
    lines.append(" Counts")
    lines.append(f"   {'combined findings:':<{_cl}} {n_uf}")
    lines.append(f"   {'raw anomalies:':<{_cl}} {n_an}")
    lines.append(f"   {'companies:':<{_cl}} {len(cos)}")
    lines.append(f"   {'metrics (distinct):':<{_cl}} {n_metrics}")

    lines.append("")
    if uf is not None and not uf.empty:
        lines.append(f" Top {top_findings_n} combined findings (severity order)")
        head = uf.head(top_findings_n)
        for i, (_, row) in enumerate(head.iterrows(), start=1):
            cik = row.get("cik", "")
            metric = row.get("metric", "")
            ftype = row.get("finding_type", "")
            direction = row.get("direction", "")
            score = row.get("score_adjusted", row.get("score_raw", ""))
            expl = row.get("explanation_summary", "")
            who = _cik_label(cik, ticker_by_cik)
            try:
                sc_f = float(score)
                score_s = f"{sc_f:.4g}"
            except (TypeError, ValueError):
                score_s = str(score)
            ov_s = ""
            ov = row.get("overlap_count", "")
            if pd.notna(ov):
                try:
                    if int(float(ov)) >= 2:
                        ov_s = f" overlap={int(float(ov))}"
                except (TypeError, ValueError):
                    pass
            expl_s = _truncate(str(expl), 96) if pd.notna(expl) and str(expl).strip() else ""
            lines.append(
                f"   {i}. {who}  {metric}  [{ftype}]  {direction}  score={score_s}{ov_s}"
            )
            if expl_s:
                lines.append(f"      {expl_s}")
    else:
        lines.append(f" Top {top_findings_n} anomalies (by |z|)")
        if an is None or an.empty:
            lines.append("   (no rows in combined findings or anomalies)")
        else:
            lines.extend(_format_anomaly_fallback_lines(an, ticker_by_cik, top_n=top_findings_n))

    if n_uf == 0:
        lines.append("")
        lines.extend(_empty_unified_note_lines(n_an=n_an))

    lines.append("")
    lines.append(
        f"   {_digest_interpretation_sentence(n_uf=n_uf, n_an=n_an, uf=uf, an=an, uf_ciks=uf_ciks, an_ciks=an_ciks)}"
    )

    lines.append(_SEP)
    return lines


def print_run_digest_stdout(
    *,
    out: Any,
    tickers: list[str],
    top_findings_n: int = 5,
) -> None:
    """Print digest for an :class:`~edgar_project.orchestration.schemas.OrchestrationOutput` instance."""
    summary = (getattr(out, "message", None) or "").strip()
    lines = format_run_digest(
        status=str(getattr(out.status, "value", out.status)),
        tickers=tickers,
        run_id=str(getattr(out, "run_id", "")),
        plan_code=str(out.interpreted_goal.code.value),
        one_line_summary=summary,
        final_report_path=getattr(out, "final_report_path", None),
        artifact_paths=dict(getattr(out, "artifact_paths", {}) or {}),
        resolved_companies=list(getattr(out, "resolved_companies", []) or []),
        top_findings_n=top_findings_n,
        step_statuses=list(getattr(out, "step_statuses", None) or []),
        tool_call_sequence=list(getattr(out, "tool_call_sequence", None) or []),
    )
    print("\n".join(lines))
