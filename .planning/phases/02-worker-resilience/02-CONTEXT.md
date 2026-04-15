# Phase 2: Worker Resilience - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Make background execution robust when jobs run long, retry, or are reclaimed after worker interruption. This phase covers how the DB-backed worker lease is maintained during active execution, how stale or expired leases recover, how retries remain auditable on the same run identity, and how cancellation behaves while work is in flight.

It does not include a new queue backend, large-scale worker parallelism redesign, CI expansion, or broader observability/security hardening outside what is necessary to make worker lease and retry behavior correct and truthful.

</domain>

<decisions>
## Implementation Decisions

### Lease ownership
- **D-01:** A worker that has claimed a job should actively renew its lease with a heartbeat while it still owns that job. Static long leases are not the default strategy.

### Stale lease recovery
- **D-02:** When a lease expires, the system should automatically requeue the same persisted run for another attempt up to the configured attempt limit rather than requiring manual retry or creating a new run identity.

### Retry visibility
- **D-03:** Retries should stay attached to the same `analysis_run_id`, but each attempt must remain clearly visible through job history and status/operator surfaces rather than being silent.

### Cancellation semantics
- **D-04:** Cancellation during active execution is best-effort at explicit safe checkpoints. A cancelled run is terminal and must never auto-retry.

### the agent's Discretion
- Exact heartbeat cadence and how close to lease expiry renewal should happen
- Whether lease renewal is driven by a dedicated periodic callback, worker-loop helper, or execution-context helper, as long as long-running active jobs keep the lease fresh
- Exact API/status payload expansion needed to surface attempt history clearly while preserving the current run-centric UX

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — overall hardening intent, brownfield constraints, and trust-first project posture
- `.planning/REQUIREMENTS.md` — `WORK-01` and `WORK-02` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 2 goal, planned breakdown, and success criteria
- `.planning/STATE.md` — current project position and active focus after Phase 1 completion

### Existing architecture and risk context
- `.planning/phases/01-run-isolation/01-CONTEXT.md` — prior-phase decision that `analysis_run_id` remains the canonical persisted run identity and retries should stay on the run-scoped workspace contract
- `.planning/codebase/CONCERNS.md` — documented worker-lease fragility, retry risk, and observability gaps that this phase must address
- `.planning/codebase/ARCHITECTURE.md` — current backend/worker/orchestration layering and where queue ownership lives
- `.planning/codebase/TESTING.md` — current worker and queue test coverage baseline

### Runtime and deployment context
- `docs/local-stack.md` — documented API/worker stack and expected worker deployment model

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/models/run_execution_job.py` — already defines the durable queue row shape with `attempt_count`, `claimed_at`, and `lease_expires_at`
- `backend/repositories/run_execution_job_repository.py` — already centralizes claim/reclaim rules and queue observability snapshots, making it the natural seam for lease-renewal and stale-lease recovery behavior
- `backend/worker/loop.py` — already owns the claim → execute → finalize lifecycle, making it the correct place to wire active heartbeat behavior and retry finalization
- `backend/services/run_lifecycle_service.py` and `backend/schemas/run_lifecycle.py` — already expose retry/cancel/status views that can be extended for operator-visible attempt history
- `backend/observability/metrics.py` and `backend/api/routes/health.py` — already publish queue state, stale-lease counts, and worker liveness signals that can be kept aligned with the new lease semantics

### Established Patterns
- The system uses one `analysis_run_id` as the canonical persisted run record, with separate `RunExecutionJob` rows tracking queue attempts around that run
- Claim logic already distinguishes fresh pending work from stale running work and currently resets stale jobs back to `pending` when the run was mid-execution
- Retry policy is currently type-based via `backend/worker/failure_classification.py`, with transient failures requeued on the same job row until `run_job_max_attempts`
- Cancellation is already modeled as terminal on the run and checked at explicit boundaries inside `EdgarPipelineExecutionService`

### Integration Points
- `backend/repositories/run_execution_job_repository.py::claim_next_runnable` — claim/reclaim/expiry transition contract
- `backend/worker/loop.py::process_next_job` and `_finalize_job_after_attempt` — where active ownership, renewal, and retry finalization connect
- `backend/services/edgar_pipeline_execution_service.py` — explicit cancellation checkpoints during long-running pipeline work
- `backend/api/routes/health.py`, `backend/observability/metrics.py`, and run status APIs — surfaces that must reflect lease state and retries truthfully

</code_context>

<specifics>
## Specific Ideas

- User accepted the recommended defaults for all identified gray areas:
  - active heartbeat renewal while a worker owns a job
  - automatic requeue of the same run after lease expiry up to attempt limits
  - retries remain on the same run but each attempt stays visible in status/history
  - best-effort cancellation at explicit safe checkpoints, with cancelled runs never auto-retried

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-worker-resilience*
*Context gathered: 2026-04-15*
