"""
Compact stdout summary for orchestration runs (CLI).

Reads artifact CSVs only for counts and top-N rows — no full report dump.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

# --- layout -----------------------------------------------------------------

_SEP = "─" * 52
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DATA_README = _REPO_ROOT / "data" / "README.md"

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


def _roots_touched(artifact_paths: dict[str, str]) -> dict[str, Path]:
    """Which top-level ``data/*`` roots appear in this run's paths."""
    found: dict[str, Path] = {}
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
) -> list[str]:
    """
    Build human-readable lines (no trailing newlines on items — join with \\n).
    """
    lines: list[str] = []
    tk = " ".join(str(t).strip().upper() for t in tickers) or "—"
    lines.append(_SEP)
    lines.append(" Run digest")
    lines.append(_SEP)
    lines.append(f"  status:   {status}")
    lines.append(f"  tickers:  {tk}")
    lines.append(f"  run_id:   {run_id}")
    lines.append(f"  plan:     {plan_code}")
    if one_line_summary:
        lines.append(f"  summary:  {_truncate(one_line_summary, 140)}")
    lines.append("")

    lines.append(" Output layout")
    lines.append(
        "   data/raw/        — SEC JSON cache (live runs)"
    )
    lines.append(
        "   data/processed/  — panel.csv, features.csv (normalized inputs)"
    )
    lines.append(
        "   data/artifacts/  — anomalies, unified findings, report.md, … (pipeline output)"
    )
    lines.append(
        "   data/evaluation/   — benchmark suites only (not main pipeline)"
    )
    if _DATA_README.is_file():
        lines.append(f"   (details: {_DATA_README})")

    roots = _roots_touched(artifact_paths)
    if roots:
        lines.append(" Roots touched this run:")
        for key in ("processed", "artifacts", "raw", "evaluation"):
            if key in roots:
                lines.append(f"   • {key:12}  {roots[key]}")

    lines.append("")
    lines.append(" Primary files (this run)")
    printed = False
    report_p = (final_report_path or "").strip() or artifact_paths.get("report_md", "")
    if report_p:
        lines.append(f"   {'Report (Markdown)':22}  {report_p}")
        printed = True
    for key, label in _PRIMARY_ARTIFACT_LABELS:
        if key == "report_md":
            continue
        pth = artifact_paths.get(key)
        if pth and str(pth).strip():
            lines.append(f"   {label:22}  {pth}")
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

    lines.append(" Counts")
    lines.append(f"   unified findings rows:  {n_uf}")
    lines.append(f"   anomaly table rows:     {n_an}")
    cos_bits = f"   companies touched:      {len(cos)}"
    if cos:
        shown = sorted(cos)[:8]
        labs = [ticker_by_cik.get(c, f"CIK {c}") for c in shown]
        tail = " …" if len(cos) > 8 else ""
        cos_bits += f"  ({', '.join(labs)}{tail})"
    lines.append(cos_bits)

    if uf is not None and not uf.empty and "finding_type" in uf.columns:
        vc = uf["finding_type"].astype(str).value_counts()
        parts = [f"{k}={int(v)}" for k, v in vc.head(6).items()]
        if parts:
            lines.append(f"   finding types:           {', '.join(parts)}")

    lines.append("")
    lines.append(f" Top {top_findings_n} findings (unified, severity order)")

    if uf is None or uf.empty:
        lines.append("   (no unified_findings.csv or empty)")
    else:
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

    lines.append(_SEP)
    return lines


def print_run_digest_stdout(
    *,
    out: Any,
    tickers: list[str],
    top_findings_n: int = 5,
) -> None:
    """Print digest for an :class:`~edgar_project.orchestration.schemas.OrchestrationOutput` instance."""
    summary = (getattr(out, "final_summary", None) or getattr(out, "message", None) or "").strip()
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
    )
    print("\n".join(lines))
