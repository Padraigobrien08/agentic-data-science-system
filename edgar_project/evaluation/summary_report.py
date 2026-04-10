"""
Human-readable benchmark run summaries for local dev and CI.

Keeps console and markdown output concise; full detail remains in ``*_results.json``.
"""

from __future__ import annotations

from typing import Any

from .schemas import EvaluationResult, EvaluationStatus, EvaluationSummary


def failure_reason_short(message: str, *, max_len: int = 200) -> str:
    """
    Compress a failure ``message`` for tables and console lines.

    Uses the first semicolon-separated clause (typical first check failure), then truncates.
    """
    if not message or message.strip() == "passed":
        return message.strip() or "(no message)"
    chunk = message.split(";")[0].strip()
    if len(chunk) > max_len:
        return chunk[: max_len - 3].rstrip() + "..."
    return chunk


def total_elapsed_seconds(results: list[EvaluationResult]) -> float:
    return float(sum((r.elapsed_seconds or 0.0) for r in results))


def format_benchmark_cli_summary(
    summary: EvaluationSummary,
    results: list[EvaluationResult],
    *,
    results_json_path: str,
    summary_json_path: str | None = None,
) -> str:
    """
    Short stdout block for ``edgar_project.cli evaluate`` — counts, failing IDs, paths.

    Full per-case messages stay in ``results_json_path``.
    """
    lines: list[str] = [
        "Benchmark results",
        f"  suite:          {summary.suite_id}",
        f"  cases:          {summary.total_cases}",
        f"  passed:         {summary.passed_cases}",
        f"  failed:         {summary.failed_cases}",
        f"  skipped:        {summary.skipped_cases}",
        f"  errors:         {summary.error_cases}",
    ]
    failing = [
        r.case_id
        for r in results
        if r.status in {EvaluationStatus.failed, EvaluationStatus.error}
    ]
    if failing:
        lines.append(f"  failing cases:  {', '.join(failing)}")
    else:
        lines.append("  failing cases:  (none)")
    lines.append(f"  details (JSON): {results_json_path}")
    if summary_json_path:
        lines.append(f"  summary (JSON): {summary_json_path}")
    return "\n".join(lines)


def format_console_report(summary: EvaluationSummary, results: list[EvaluationResult]) -> str:
    """Multi-line string suitable for printing to stdout (CI logs)."""
    lines: list[str] = []
    sep = "=" * 60
    lines.append(sep)
    lines.append(f"Benchmark suite: {summary.suite_id}")
    lines.append(sep)
    lines.append(
        f"Cases: {summary.total_cases} total | "
        f"{summary.passed_cases} passed | "
        f"{summary.failed_cases} failed | "
        f"{summary.skipped_cases} skipped | "
        f"{summary.error_cases} errors"
    )
    if summary.total_elapsed_seconds is not None:
        lines.append(f"Case CPU time (sum): {summary.total_elapsed_seconds:.3f}s")
    if summary.generated_at:
        lines.append(f"Finished (UTC): {summary.generated_at}")

    non_ok = [r for r in results if r.status not in {EvaluationStatus.passed, EvaluationStatus.skipped}]
    if non_ok:
        lines.append("")
        lines.append("Non-passing cases:")
        for r in non_ok:
            reason = failure_reason_short(r.message)
            lines.append(f"  • [{r.status.value}] {r.case_id}: {reason}")
    else:
        lines.append("")
        lines.append("No failed or errored cases.")

    lines.append(sep)
    return "\n".join(lines)


def render_markdown_report(summary: EvaluationSummary, results: list[EvaluationResult]) -> str:
    """Git-friendly markdown artifact for a benchmark run."""
    rows: list[str] = [
        f"# Benchmark: `{summary.suite_id}`",
        "",
        f"- **Finished (UTC):** {summary.generated_at or '—'}",
        f"- **Total cases:** {summary.total_cases}",
        f"- **Passed:** {summary.passed_cases} · **Failed:** {summary.failed_cases} · "
        f"**Skipped:** {summary.skipped_cases} · **Errors:** {summary.error_cases}",
    ]
    if summary.total_elapsed_seconds is not None:
        rows.append(f"- **Sum of case times:** {summary.total_elapsed_seconds:.3f}s")
    rows.extend(["", "## Case outcomes", "", "| case_id | status | time (s) | note |", "|---|---:|---:|---|"])
    for r in results:
        t = f"{r.elapsed_seconds:.4f}" if r.elapsed_seconds is not None else "—"
        note = ""
        if r.status in {EvaluationStatus.failed, EvaluationStatus.error}:
            note = failure_reason_short(r.message).replace("|", "\\|")
        elif r.status == EvaluationStatus.skipped:
            note = failure_reason_short(r.message).replace("|", "\\|")
        rows.append(f"| `{r.case_id}` | {r.status.value} | {t} | {note} |")

    failed = [r for r in results if r.status in {EvaluationStatus.failed, EvaluationStatus.error}]
    if failed:
        rows.extend(["", "## Failure detail (short)", ""])
        for r in failed:
            rows.append(f"### `{r.case_id}` ({r.status.value})")
            rows.append("")
            rows.append(f"```\n{r.message}\n```")
            rows.append("")

    rows.append("")
    rows.append("_Full JSON: see `*_results.json` and `*_summary.json` next to this file._")
    rows.append("")
    return "\n".join(rows)


def summary_json_blob(summary: EvaluationSummary) -> dict[str, Any]:
    """Structured dict for writing ``*_summary.json`` (includes brief failure list)."""
    return summary.model_dump(mode="json")
