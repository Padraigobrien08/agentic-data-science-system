---
phase: 05-storage-and-ops
plan: 01
subsystem: observability
tags: [observability, metrics, health, fastapi, prometheus, pytest]
requires:
  - phase: 02-worker-resilience
    provides: DB-backed worker queue snapshot semantics shared by health and metrics
  - phase: 03-secure-defaults
    provides: ops-token protection for `/metrics` and `/v1/worker/health`
provides:
  - Shared worker queue observability helper for JSON and Prometheus surfaces
  - Explicit degraded worker-health JSON contract with known-vs-unknown queue state
  - Prometheus queue observability gauges that expose dependency failure instead of zero-fill
affects: [backend, api, observability, worker, metrics]
tech-stack:
  added: []
  patterns:
    - shared queue observability helper reused by `/v1/worker/health` and `/metrics`
    - unknown worker queue state encoded as nullable JSON and `NaN` Prometheus gauges
key-files:
  created:
    - backend/observability/worker_queue.py
    - .planning/phases/05-storage-and-ops/05-storage-and-ops-01-SUMMARY.md
  modified:
    - backend/api/routes/health.py
    - backend/schemas/health.py
    - backend/observability/metrics.py
    - tests/test_backend_health.py
key-decisions:
  - "Use one DB-backed worker queue observability helper so JSON and Prometheus surfaces cannot drift on degraded-state truth."
  - "Represent unknown queue state as nullable booleans/counts in JSON and `NaN` gauges in Prometheus instead of synthetic zeroes."
patterns-established:
  - "Operational truthfulness pattern: worker-health and Prometheus refreshes share one queue observability result object."
  - "Dependency-failure pattern: emit explicit degraded/up signals alongside unknown-state payload values instead of collapsing failures into empty-state metrics."
requirements-completed: [OPER-01]
duration: 4min
completed: 2026-04-17
---

# Phase 05 Plan 01: Storage and Ops Summary

**Shared queue observability now drives degraded worker-health JSON and truthful Prometheus unknown-state gauges**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-17T21:01:18Z
- **Completed:** 2026-04-17T21:05:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `backend/observability/worker_queue.py` so DB-backed queue reads now return one shared success/degraded contract for operator surfaces.
- Expanded `WorkerHealthResponse` and `/v1/worker/health` to report explicit degraded database state, `queue_state_known`, and nullable unknown queue values instead of synthetic zeroes.
- Refactored `backend/observability/metrics.py` to reuse the shared helper, publish `edgar_worker_queue_observability_up` and `edgar_worker_queue_observability_last_error_unixtime`, and emit `NaN` when queue state is unknown.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create one degraded-state queue observability contract for worker health** - `07d1467` (test), `687e2be` (feat boundary after shared-index spillover)
2. **Task 2: Make Prometheus queue metrics expose degraded-state truth instead of zero-fill** - `0c9aa3c` (test), `50bf4d9` (feat)

**Plan metadata:** recorded in the final docs commit after summary/state updates.

## Files Created/Modified

- `backend/observability/worker_queue.py` - Shared queue observability result object and DB-backed helper used by JSON and Prometheus paths.
- `backend/api/routes/health.py` - Maps the shared helper into explicit degraded worker-health responses.
- `backend/schemas/health.py` - Adds `status`, `database`, `queue_state_known`, and nullable queue-state fields to the worker-health schema.
- `backend/observability/metrics.py` - Reuses the shared helper, adds observability health gauges, and emits `NaN` for unknown queue state.
- `tests/test_backend_health.py` - Locks degraded worker-health JSON and degraded queue metrics behavior in one focused regression module.

## Decisions Made

- Reused one helper for worker-health JSON and Prometheus refreshes so queue observability logic remains canonical.
- Kept worker-health degradation additive by extending the schema rather than changing route auth or endpoint shape.
- Treated unknown queue state as first-class operational truth instead of allowing the old zero-fill behavior to masquerade as an empty queue.

## Deviations from Plan

None - implementation scope matched the plan exactly.

## Issues Encountered

- Shared-index contention from parallel plan executors caused part of the Task 1 implementation to land in concurrent commits `3f6d340` and `e03ca09` before the Task 1 feature-boundary commit. I did not rewrite shared history; instead I recorded the task boundary with `687e2be` and verified the final file state with the plan’s targeted pytest command.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `OPER-01` is now satisfied for the worker queue observability surface, and the shared helper gives later observability work one canonical truth source.
- The remaining Phase 5 plans can build on explicit degraded-state semantics without reopening queue-health behavior.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/05-storage-and-ops/05-storage-and-ops-01-SUMMARY.md`.
- Task/boundary commits verified in git history: `07d1467`, `687e2be`, `0c9aa3c`, `50bf4d9`.
- Verification passed: `python3 -m pytest tests/test_backend_health.py -q --tb=short`.

---
*Phase: 05-storage-and-ops*
*Completed: 2026-04-17*
