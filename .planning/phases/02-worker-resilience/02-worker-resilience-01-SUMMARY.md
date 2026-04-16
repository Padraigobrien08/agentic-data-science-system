---
phase: 02-worker-resilience
plan: 01
subsystem: worker
tags: [worker-resilience, leases, heartbeat, orchestration, pytest, sql]
requires: []
provides:
  - Claim-token fencing for queued job claims, renewals, and terminal finalization
  - Background lease heartbeat that aborts stale workers before persistence boundaries
  - Regression coverage for lease renewal and ownership-loss abort behavior
affects: [02-02, backend, worker, orchestration, metrics]
tech-stack:
  added: []
  patterns: [claim-token ownership fence, background lease heartbeat, orchestration execution checkpoints]
key-files:
  created: [alembic/versions/006_run_job_claim_token.py, backend/worker/lease.py, tests/test_worker_lease_heartbeat.py]
  modified: [backend/models/run_execution_job.py, backend/repositories/run_execution_job_repository.py, backend/services/exceptions.py, backend/services/edgar_pipeline_execution_service.py, backend/agents/traceable_analysis_pipeline.py, backend/worker/loop.py, edgar_project/orchestration/agent.py, edgar_project/orchestration/executor.py, tests/test_worker_job_lifecycle.py]
key-decisions:
  - "Use a per-claim `claim_token` compare-and-set fence so renew/finalize logic stays safe after the claim transaction releases row locks."
  - "Run a background lease heartbeat from the worker with explicit execution checkpoints, instead of stretching the static lease window."
  - "Treat `WorkerLeaseLostError` as a rollback-only ownership loss, not as a generic pipeline failure that should persist stale run error state."
patterns-established:
  - "Worker ownership pattern: claimed rows can only be renewed, requeued, or finalized when the current `claim_token` still matches."
  - "Execution checkpoint pattern: worker-owned runs check lease ownership before orchestration dispatch and before every persistence boundary."
requirements-completed: [WORK-01]
duration: 17min
completed: 2026-04-16
---

# Phase 2 Plan 01: Lease Heartbeat and Ownership Fencing Summary

**Worker claims now carry explicit ownership tokens and active heartbeats so stale executors stop before writing stale results**

## Performance

- **Duration:** 17 min
- **Started:** 2026-04-16T07:23:40Z
- **Completed:** 2026-04-16T07:40:32Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Added claim-token fencing to queued job claims so stale workers can no longer renew or finalize a job after ownership changes.
- Introduced `WorkerLeaseGuard` plus worker/execution-service/orchestration checkpoints so long-running runs renew leases in the background and abort cleanly on ownership loss.
- Added focused heartbeat regressions and kept the Wave 1 verification command green across both the existing job lifecycle coverage and the new lease-loss path.

## Task Commits

Each task was committed atomically through its TDD and implementation steps:

1. **Task 1: Add claim-token ownership fencing to queued job claims**
   `ae9ea7a` (`test`) failing claim-token ownership regressions
   `c867ae9` (`feat`) claim-token fencing for claim, renew, and finalize paths
2. **Task 2: Heartbeat active worker leases and abort safely on ownership loss**
   `a0cdc55` (`test`) heartbeat renewal and lease-loss regressions
   `4157303` (`feat`) background lease guard, checkpoint wiring, and rollback-on-lease-loss handling

## Files Created/Modified

- `alembic/versions/006_run_job_claim_token.py` - Adds the nullable `claim_token` column for compare-and-set worker ownership.
- `backend/models/run_execution_job.py` - Documents claim-token ownership and the current attempt counter semantics.
- `backend/repositories/run_execution_job_repository.py` - Adds claim-token generation, renew/finalize fencing, and guarded requeue updates.
- `backend/services/exceptions.py` - Introduces `WorkerLeaseLostError`.
- `backend/worker/lease.py` - Implements the background `WorkerLeaseGuard`.
- `backend/worker/loop.py` - Starts and stops the lease guard, passes checkpoints into execution, and treats lost ownership as a non-mutating finalize outcome.
- `backend/services/edgar_pipeline_execution_service.py` - Wires execution checkpoints through worker-owned execution and rolls back on lease loss instead of persisting stale error state.
- `backend/agents/traceable_analysis_pipeline.py`, `edgar_project/orchestration/agent.py`, and `edgar_project/orchestration/executor.py` - Thread lease checkpoints into orchestration/tool-dispatch boundaries.
- `tests/test_worker_job_lifecycle.py` - Locks the claim-token renew/finalize contract around queued claims and stale queued reclaims.
- `tests/test_worker_lease_heartbeat.py` - Covers lease renewal during delayed execution and ownership-loss aborts during orchestration.

## Decisions Made

- Kept the lease heartbeat interval derived from the lease duration but exposed a test-only override seam through the guard constructor so regressions can run quickly.
- Added a guarded `requeue_if_owned()` repository path for the pre-Phase-2 retry model instead of letting stale workers push the same row back to `pending`.
- Rolled back `execute_analysis_run()` on `WorkerLeaseLostError` so the stale worker never commits a misleading `error` run state after ownership is gone.

## Deviations from Plan

None.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- Plan `02-02` can now build on explicit claim-token fencing instead of introducing retry-history changes against an unfenced worker loop.
- The orchestration path already exposes checkpoint hooks, so the next wave can focus on durable attempt rows and status history rather than lease mechanics.
- No blockers identified for Phase 2 Plan `02-02`.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/02-worker-resilience/02-worker-resilience-01-SUMMARY.md`.
- Task commits verified in git history: `ae9ea7a`, `c867ae9`, `a0cdc55`, `4157303`.
- Verification passed: `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_worker_lease_heartbeat.py -q`.

---
*Phase: 02-worker-resilience*
*Completed: 2026-04-16*
