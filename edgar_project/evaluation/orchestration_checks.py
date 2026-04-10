"""Lightweight checks on :class:`~edgar_project.orchestration.schemas.OrchestrationOutput`."""

from __future__ import annotations

from edgar_project.orchestration.schemas import OrchestrationOutput, OrchestrationRunStatus

from .schemas import ExpectedOrchestration


def validate_orchestration_output(
    out: OrchestrationOutput,
    exp: ExpectedOrchestration,
) -> tuple[dict[str, bool], list[str]]:
    """
    Compare orchestration output to expectations.

    Returns ``(checks, failure_messages)`` with human-readable failures.
    """
    checks: dict[str, bool] = {}
    failures: list[str] = []

    try:
        expected_status = OrchestrationRunStatus(exp.expected_run_status)
    except ValueError:
        checks["orch_expected_status_valid"] = False
        failures.append(
            f"invalid expected_run_status {exp.expected_run_status!r}; "
            f"expected one of {[s.value for s in OrchestrationRunStatus]}"
        )
        return checks, failures

    checks["orch_status_matches"] = out.status == expected_status
    if out.status != expected_status:
        failures.append(
            f"orchestration status: expected {expected_status.value!r}, got {out.status.value!r}; "
            f"message={out.message!r}"
        )

    for key in exp.required_artifact_keys:
        path = out.artifact_paths.get(key)
        ok = bool(path and str(path).strip())
        checks[f"orch_artifact_required::{key}"] = ok
        if not ok:
            failures.append(
                f"required artifact key {key!r} missing or empty in artifact_paths "
                f"(have keys: {sorted(out.artifact_paths.keys())})"
            )

    for key in exp.forbidden_artifact_keys:
        path = out.artifact_paths.get(key)
        ok = path is None or str(path).strip() == ""
        checks[f"orch_artifact_forbidden::{key}"] = ok
        if not ok:
            failures.append(f"artifact key {key!r} should be absent but got path {path!r}")

    if exp.final_report_path_non_null:
        rp = out.final_report_path
        ok = bool(rp and str(rp).strip())
        checks["orch_final_report_path_present"] = ok
        if not ok:
            failures.append(
                f"expected final_report_path to be set; got {out.final_report_path!r}"
            )

    if exp.final_report_path_null:
        ok = out.final_report_path is None or str(out.final_report_path).strip() == ""
        checks["orch_final_report_path_absent"] = ok
        if not ok:
            failures.append(
                f"expected final_report_path to be absent; got {out.final_report_path!r}"
            )

    seq = [t.tool_name for t in out.tool_call_sequence]
    for tool in exp.tools_must_not_appear_in_call_sequence:
        present = tool in seq
        checks[f"orch_tool_not_in_sequence::{tool}"] = not present
        if present:
            failures.append(
                f"tool {tool!r} must not appear in tool_call_sequence; sequence was {seq!r}"
            )

    warn_codes = {w.code for w in out.warnings}
    for code in exp.warning_codes_must_include:
        ok = code in warn_codes
        checks[f"orch_warning_code::{code}"] = ok
        if not ok:
            failures.append(
                f"expected warning code {code!r}; have {sorted(warn_codes)!r}"
            )

    if exp.warning_codes_include_any:
        ok = any(c in warn_codes for c in exp.warning_codes_include_any)
        checks["orch_warning_codes_include_any"] = ok
        if not ok:
            failures.append(
                "expected at least one warning code from "
                f"{exp.warning_codes_include_any!r}; have {sorted(warn_codes)!r}"
            )

    if exp.max_errors is not None:
        n = len(out.errors)
        ok = n <= exp.max_errors
        checks["orch_max_errors"] = ok
        if not ok:
            failures.append(f"errors: expected at most {exp.max_errors}, got {n}: {[e.code for e in out.errors]!r}")

    if exp.min_errors is not None:
        n = len(out.errors)
        ok = n >= exp.min_errors
        checks["orch_min_errors"] = ok
        if not ok:
            failures.append(f"errors: expected at least {exp.min_errors}, got {n}")

    return checks, failures
