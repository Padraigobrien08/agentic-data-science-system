"""
Deterministic analytical-quality checks on unified findings and anomaly outputs.

Uses containment, counts, and ranges — not exact row equality.
"""

from __future__ import annotations

import pandas as pd

from .schemas import ExpectedFindings


def run_analytical_findings_checks(
    unified: pd.DataFrame,
    anomalies: pd.DataFrame | None,
    exp: ExpectedFindings,
    *,
    case_id: str = "",
) -> tuple[dict[str, bool], list[str]]:
    """
    Run optional analytical checks defined on ``ExpectedFindings``.

    Returns ``(checks, failure_messages)``.
    """
    checks: dict[str, bool] = {}
    failures: list[str] = []
    pfx = f"{case_id}: " if case_id else ""

    if unified is None:
        unified = pd.DataFrame()

    top_n = max(1, int(exp.top_n))

    # --- Top slice: metrics / CIKs must appear in the first N rows (pipeline sort order) ---
    head = unified.head(top_n) if not unified.empty else unified
    for m in exp.top_must_include_metrics:
        if head.empty or "metric" not in head.columns:
            checks[f"analytical_top_metric::{m}"] = False
            failures.append(
                f"{pfx}top_{top_n}_findings: no unified findings or missing 'metric' column; "
                f"expected metric {m!r} in top slice"
            )
            continue
        ok = bool((head["metric"].astype(str) == str(m)).any())
        checks[f"analytical_top_metric::{m}"] = ok
        if not ok:
            got = head["metric"].astype(str).tolist()
            failures.append(
                f"{pfx}top_{top_n}_findings: expected metric {m!r} in top slice; "
                f"got metrics (in order) {got!r}"
            )

    for cik in exp.top_must_include_ciks:
        if head.empty or "cik" not in head.columns:
            checks[f"analytical_top_cik::{cik}"] = False
            failures.append(
                f"{pfx}top_{top_n}_findings: no unified findings or missing 'cik' column; "
                f"expected cik {cik} in top slice"
            )
            continue
        cik_series = pd.to_numeric(head["cik"], errors="coerce")
        want = int(cik)
        ok = bool((cik_series == want).any())
        checks[f"analytical_top_cik::{cik}"] = ok
        if not ok:
            raw = head["cik"].tolist()
            parsed = cik_series.tolist()
            failures.append(
                f"{pfx}top_{top_n}_findings: expected cik {cik} in top slice; "
                f"got raw cik values (in order) {raw!r} (parsed numeric {parsed!r})"
            )

    # --- Overlap metadata (unified findings) ---
    if exp.min_rows_with_overlap_ge_threshold is not None:
        thr = int(exp.overlap_ge_threshold)
        need = int(exp.min_rows_with_overlap_ge_threshold)
        if unified.empty or "overlap_count" not in unified.columns:
            checks["analytical_overlap_row_count"] = False
            failures.append(
                f"{pfx}overlap check: unified findings empty or missing overlap_count column"
            )
        else:
            oc = pd.to_numeric(unified["overlap_count"], errors="coerce").fillna(0).astype(int)
            cnt = int((oc >= thr).sum())
            ok = cnt >= need
            checks["analytical_overlap_row_count"] = ok
            if not ok:
                failures.append(
                    f"{pfx}overlap check: expected at least {need} row(s) with overlap_count>={thr}; found {cnt}"
                )

    needles = exp.overlap_sources_one_row_must_include_substrings
    if needles:
        if unified.empty or "overlap_sources" not in unified.columns:
            checks["analytical_overlap_sources_substrings"] = False
            failures.append(
                f"{pfx}overlap_sources check: unified findings empty or missing overlap_sources column"
            )
        else:
            def row_has_all(val: object) -> bool:
                s = str(val)
                return all(n in s for n in needles)

            ok = bool(unified["overlap_sources"].map(row_has_all).any())
            checks["analytical_overlap_sources_substrings"] = ok
            if not ok:
                sample = unified["overlap_sources"].astype(str).head(10).tolist()
                failures.append(
                    f"{pfx}overlap_sources check: no row contains all substrings "
                    f"{needles!r}; sample values {sample!r}"
                )

    # --- Caveat substrings: unified findings ---
    for sub, minimum in exp.unified_caveat_substring_min_row_counts.items():
        min_n = int(minimum)
        if unified.empty or "caveat_codes" not in unified.columns:
            checks[f"analytical_unified_caveat::{sub}"] = False
            failures.append(
                f"{pfx}unified caveat {sub!r}: no rows or missing caveat_codes column "
                f"(need >= {min_n} rows containing substring)"
            )
            continue
        ser = unified["caveat_codes"].astype(str)
        cnt = int(ser.str.contains(sub, regex=False).sum())
        ok = cnt >= min_n
        checks[f"analytical_unified_caveat::{sub}"] = ok
        if not ok:
            failures.append(
                f"{pfx}unified caveat {sub!r}: expected at least {min_n} row(s) with substring in caveat_codes; "
                f"found {cnt}"
            )

    # --- Caveat substrings: anomalies table ---
    anom = anomalies if anomalies is not None and not anomalies.empty else None
    for sub, minimum in exp.anomaly_caveat_substring_min_row_counts.items():
        min_n = int(minimum)
        if anom is None or "caveat_codes" not in anom.columns:
            checks[f"analytical_anomaly_caveat::{sub}"] = False
            failures.append(
                f"{pfx}anomaly caveat {sub!r}: no anomaly rows or missing caveat_codes column "
                f"(need >= {min_n} rows containing substring)"
            )
            continue
        ser = anom["caveat_codes"].astype(str)
        cnt = int(ser.str.contains(sub, regex=False).sum())
        ok = cnt >= min_n
        checks[f"analytical_anomaly_caveat::{sub}"] = ok
        if not ok:
            failures.append(
                f"{pfx}anomaly caveat {sub!r}: expected at least {min_n} row(s) with substring in caveat_codes; "
                f"found {cnt}"
            )

    return checks, failures
