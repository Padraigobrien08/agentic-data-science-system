---
phase: 10-live-hybrid-execution-hardening
plan: 03
subsystem: observability
tags: [health, metrics, evaluation, ops]
requires: ["10-02"]
provides:
  - "DB-backed evaluation dependency observability shared by JSON and Prometheus health surfaces"
  - "Explicit SEC and storage degradation slices on `/health` and `/v1/worker/health`"
  - "Operator docs for following degraded evaluation signals into canonical child runs"
affects: [backend, observability, api, docs, tests]
tech-stack:
  added: []
  patterns: ["shared dependency observability helper", "truthful degraded-state metrics", "ops-to-run navigation"]
key-files:
  created:
    - backend/observability/evaluation_validation.py
    - .planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md
  modified:
    - backend/api/routes/health.py
    - backend/api/routes/metrics.py
    - backend/observability/metrics.py
    - backend/schemas/health.py
    - tests/test_backend_health.py
    - README.md
key-decisions:
  - "Evaluation dependency truth is computed once from recent live/hybrid case rows and reused by both JSON and Prometheus surfaces."
  - "Unknown evaluation dependency state is treated as degraded, not silently healthy."
  - "Storage failure evidence stays separate from degradation class taxonomy by flowing through explicit `storage_error_code` metadata and dedicated gauges."
patterns-established:
  - "Health and metrics surfaces should share one DB-backed helper for new dependency slices."
  - "Operator docs should point degraded health signals back into canonical run APIs instead of bespoke debug paths."
requirements-completed: [EVAL-02, OPS-01]
duration: 15min
completed: 2026-04-18
---

# Phase 10: Live/Hybrid Execution Hardening Summary

**Evaluation dependency observability and operator follow-through**

## Performance

- **Duration:** 15 min
- **Completed:** 2026-04-18T20:05:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added a shared DB-backed helper that reads recent live/hybrid case results and computes SEC vs storage dependency health.
- Extended `/health`, `/v1/worker/health`, and `/metrics` with explicit evaluation dependency truth instead of leaving operators to infer it from case messages.
- Documented the operator path from degraded evaluation signals to `latest_analysis_run_id` and `/v1/runs/{run_id}`.

## Task Commits

1. **Task 1-2: Evaluation dependency health and metrics truthfulness** - pending commit

**Plan metadata:** pending summary commit

## Files Created/Modified

- `backend/observability/evaluation_validation.py` - shared evaluation dependency observability contract
- `backend/api/routes/health.py` - JSON health responses now include evaluation dependency state and degrade when it is unknown or unhealthy
- `backend/api/routes/metrics.py` - metrics scrape refreshes evaluation gauges alongside worker queue gauges
- `backend/observability/metrics.py` - added evaluation dependency Prometheus gauges and unknown-state handling
- `backend/schemas/health.py` - added `EvaluationDependencyHealth` to both public health payloads
- `tests/test_backend_health.py` - regressions for SEC degradation, storage degradation, and observability-read failure
- `README.md` - operator note for jumping from degraded evaluation state to canonical child runs

## Decisions Made

- No separate evaluation-specific status page was introduced; the existing health and metrics surfaces now carry the needed operator breadcrumb.
- `recent_degraded_case_count` counts SEC- or storage-evidenced live/hybrid case rows from the shared helper rather than all non-`none` degradation classes.

## Deviations from Plan

- `tests/test_evaluation_live_hybrid_execution.py` did not need additional Wave 3 edits because Wave 2 already covered `artifact_storage_unavailable` child-run evidence and stayed green under the new health slice.

## Issues Encountered

- None.

## User Setup Required

None.

## Next Phase Readiness

- Phase 10 can now be closed once the broader verification sweep passes and roadmap/state are updated.
- Future ops or UI work can consume the new evaluation dependency helper instead of re-deriving SEC/storage degradation rules.

## Self-Check

- `python3 -m pytest tests/test_backend_health.py tests/test_evaluation_live_hybrid_execution.py -q --tb=short`

---
*Phase: 10-live-hybrid-execution-hardening*
*Completed: 2026-04-18*
