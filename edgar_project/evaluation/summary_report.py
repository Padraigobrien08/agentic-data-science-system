"""
Human-readable benchmark run summaries for local dev and CI.

Keeps console and markdown output concise; full detail remains in ``*_results.json``.
"""

from __future__ import annotations

from typing import Any

from .schemas import EvaluationResult, EvaluationStatus, EvaluationSummary, ValidationDegradationClass


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


def degradation_counts(results: list[EvaluationResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        key = result.degradation_class.value
        if key == ValidationDegradationClass.none.value:
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


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
    degraded = degradation_counts(results)
    if degraded:
        counts = ", ".join(f"{name}={count}" for name, count in sorted(degraded.items()))
        lines.append(f"  degradation:    {counts}")
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

    routed = [
        r
        for r in results
        if r.status != EvaluationStatus.passed or r.degradation_class != ValidationDegradationClass.none
    ]
    if routed:
        lines.append("")
        lines.append("Cases needing follow-up:")
        for r in routed:
            reason = failure_reason_short(r.message)
            lines.append(
                f"  • [{r.status.value} / {r.degradation_class.value}] {r.case_id}: {reason}"
            )
    else:
        lines.append("")
        lines.append("No failed, skipped, or degraded cases.")

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
    degraded = degradation_counts(results)
    if degraded:
        counts = ", ".join(f"`{name}`: {count}" for name, count in sorted(degraded.items()))
        rows.append(f"- **Degradation counts:** {counts}")
    rows.extend(
        [
            "",
            "## Case outcomes",
            "",
            "| case_id | status | degradation | time (s) | note |",
            "|---|---:|---|---:|---|",
        ]
    )
    for r in results:
        t = f"{r.elapsed_seconds:.4f}" if r.elapsed_seconds is not None else "—"
        note = ""
        if r.status in {EvaluationStatus.failed, EvaluationStatus.error}:
            note = failure_reason_short(r.message).replace("|", "\\|")
        elif r.status == EvaluationStatus.skipped:
            note = failure_reason_short(r.message).replace("|", "\\|")
        rows.append(
            f"| `{r.case_id}` | {r.status.value} | {r.degradation_class.value} | {t} | {note} |"
        )

    failed = [r for r in results if r.status in {EvaluationStatus.failed, EvaluationStatus.error}]
    if failed:
        rows.extend(["", "## Failure detail (short)", ""])
        for r in failed:
            rows.append(f"### `{r.case_id}` ({r.status.value} / {r.degradation_class.value})")
            rows.append("")
            rows.append(f"```\n{r.message}\n```")
            rows.append("")

    rows.append("")
    rows.append("_Full JSON: see `*_results.json` and `*_summary.json` next to this file._")
    rows.append("")
    return "\n".join(rows)


def summary_json_blob(summary: EvaluationSummary, results: list[EvaluationResult]) -> dict[str, Any]:
    """Structured dict for writing ``*_summary.json`` (includes brief failure list)."""
    payload = summary.model_dump(mode="json")
    payload["degradation_counts"] = degradation_counts(results)
    degradation_by_case = {r.case_id: r.degradation_class.value for r in results}
    for brief in payload.get("failed_case_briefs", []):
        case_id = brief.get("case_id")
        brief["degradation_class"] = degradation_by_case.get(case_id, ValidationDegradationClass.none.value)
    return payload
