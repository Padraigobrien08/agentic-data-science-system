---
phase: 02-worker-resilience
plan: 02
subsystem: worker
tags: [worker-resilience, retries, attempt-history, api, pytest, sql]
requires: [02-01]
provides:
  - Durable one-row-per-attempt execution history on a single `analysis_run_id`
  - Additive `/v1/runs/{run_id}/status` history without removing `latest_execution_job`
  - Regression coverage for retry, reclaim, and cancelled-run visibility
affects: [02-03, backend, worker, api, metrics]
tech-stack:
  added: []
  patterns: [durable attempt rows, additive status history, same-run retry visibility]
key-files:
  created: [.planning/phases/02-worker-resilience/02-worker-resilience-02-SUMMARY.md]
  modified: [backend/config/settings.py, backend/models/run_execution_job.py, backend/repositories/run_execution_job_repository.py, backend/services/run_queue_service.py, backend/services/run_lifecycle_service.py, backend/schemas/run_lifecycle.py, backend/api/routes/runs.py, backend/worker/loop.py, tests/test_worker_job_lifecycle.py, tests/test_async_run_queue.py, tests/test_run_lifecycle_api.py, tests/test_run_lifecycle_production.py]
key-decisions:
  - "Treat `RunExecutionJob` as one durable row per attempt, starting at attempt `1`, instead of mutating one row through retries."
  - "Keep retries and stale-lease recovery on the same `analysis_run_id`, but preserve prior failed/cancelled rows for operator auditability."
  - "Extend `/v1/runs/{run_id}/status` additively by keeping `latest_execution_job` and adding ordered `execution_job_history`."
patterns-established:
  - "Retry visibility pattern: latest attempt remains easy to poll while full attempt history stays attached to the run."
  - "Reclaim/retry pattern: transient failure or stale-running reclaim finalizes the old row and creates the next pending row only when attempts remain."
requirements-completed: [WORK-02]
duration: 10min
completed: 2026-04-16
---

# Phase 2 Plan 02: Durable Attempt History Summary

**Retries and stale reclaims now preserve explicit attempt history on the same run instead of mutating a single job row**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-16T07:41:45Z
- **Completed:** 2026-04-16T07:51:53Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Converted background execution jobs to durable per-attempt rows so initial enqueue starts at attempt `1`, fresh claims preserve that attempt number, and transient retries or stale-running reclaims insert the next pending row instead of rewriting history.
- Updated retry lifecycle assembly and the run status API so one `analysis_run_id` now exposes both the latest execution job and ordered `execution_job_history`.
- Added regressions covering inclusive final-attempt claimability, durable failed-row retention, newest-first status history, and cancelled-run status without automatic pending replacement.

## Task Commits

1. **Task 1 + Task 2 tests**
   `32bef83` (`test`) durable attempt-history and status-history regressions
2. **Task 1 + Task 2 implementation**
   `2a0ceb7` (`feat`) durable attempt rows, retry/reclaim persistence, and additive status history

## Files Created/Modified

- `backend/models/run_execution_job.py` - Reframes execution jobs as 1-based durable attempt rows.
- `backend/config/settings.py` - Documents `run_job_max_attempts` as a per-run attempt ceiling.
- `backend/services/run_queue_service.py` - Seeds initial queued execution at attempt `1`.
- `backend/repositories/run_execution_job_repository.py` - Preserves attempt numbers on claim, creates next pending rows on retry/reclaim, and keeps queue observability aligned with the same inclusive comparator.
- `backend/services/run_lifecycle_service.py` - Retries onto the same run with new pending rows and assembles latest-plus-history status views.
- `backend/schemas/run_lifecycle.py` and `backend/api/routes/runs.py` - Add ordered `execution_job_history` while keeping `latest_execution_job`.
- `tests/test_worker_job_lifecycle.py`, `tests/test_async_run_queue.py`, `tests/test_run_lifecycle_api.py`, and `tests/test_run_lifecycle_production.py` - Lock the durable attempt and cancelled-run visibility semantics.

## Decisions Made

- Kept the status contract additive so existing pollers can keep using `latest_execution_job` while operators gain full attempt visibility.
- Used the same `attempt_count <= max_attempts` rule for both claimability and queue observability so health/metrics can remain truthful to repository behavior.
- Treated cancelled runs as terminal for all auto-retry branches; only explicit manual retry can create a new pending row after cancellation.

## Deviations from Plan

None.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- Plan `02-03` can now focus entirely on proof: Postgres claim concurrency, history regressions, and health/metrics truthfulness.
- The status API and repository already expose the durable semantics needed for the final verification wave.
- No blockers identified for Phase 2 Plan `02-03`.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/02-worker-resilience/02-worker-resilience-02-SUMMARY.md`.
- Task commits verified in git history: `32bef83`, `2a0ceb7`.
- Verification passed: `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py tests/test_run_lifecycle_production.py -q`.

---
*Phase: 02-worker-resilience*
*Completed: 2026-04-16*
