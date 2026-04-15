# Phase 02: Worker Resilience - Research

**Researched:** 2026-04-15
**Domain:** DB-backed background worker leasing, retry safety, and cancellation truthfulness
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** A worker that has claimed a job should actively renew its lease with a heartbeat while it still owns that job. Static long leases are not the default strategy.
- **D-02:** When a lease expires, the system should automatically requeue the same persisted run for another attempt up to the configured attempt limit rather than requiring manual retry or creating a new run identity.
- **D-03:** Retries should stay attached to the same `analysis_run_id`, but each attempt must remain clearly visible through job history and status/operator surfaces rather than being silent.
- **D-04:** Cancellation during active execution is best-effort at explicit safe checkpoints. A cancelled run is terminal and must never auto-retry.

### Claude's Discretion
- Exact heartbeat cadence and how close to lease expiry renewal should happen
- Whether lease renewal is driven by a dedicated periodic callback, worker-loop helper, or execution-context helper, as long as long-running active jobs keep the lease fresh
- Exact API/status payload expansion needed to surface attempt history clearly while preserving the current run-centric UX

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WORK-01 | Worker renews or safely expires job leases so long-running jobs do not execute twice after delays or restarts | Heartbeat + ownership token/fencing, compare-and-set finalize, stale-lease reclaim rules, and Postgres `SKIP LOCKED` validation |
| WORK-02 | Background execution remains idempotent when retries, worker restarts, or transient failures occur | Same `analysis_run_id`, immutable attempt history, cancelled-runs-never-retry rule, reclaim-to-new-attempt semantics, and regression coverage for restart/retry races |
</phase_requirements>

## Summary

The current codebase already has the right brownfield seams for this phase: [run_execution_job_repository.py](/Users/padraigobrien/agentic_data_science_system/backend/repositories/run_execution_job_repository.py), [loop.py](/Users/padraigobrien/agentic_data_science_system/backend/worker/loop.py), [run_lifecycle_service.py](/Users/padraigobrien/agentic_data_science_system/backend/services/run_lifecycle_service.py), and [edgar_pipeline_execution_service.py](/Users/padraigobrien/agentic_data_science_system/backend/services/edgar_pipeline_execution_service.py). The queue is already DB-backed, claims already use `FOR UPDATE SKIP LOCKED` on PostgreSQL, lease expiry already exists in schema, and cancellation is already modeled as best-effort checkpoints. The planner should preserve that architecture and harden it rather than replace it.

The main planning risk is that the current worker commits the claim transaction before executing the pipeline. PostgreSQL row locks are therefore gone before long-running work starts, which means lease safety depends entirely on persisted lease semantics after claim. A heartbeat alone is not enough: renew and finalize operations must be fenced by an ownership token so a stale worker cannot refresh or complete a reclaimed job. This is the core requirement to satisfy `WORK-01`.

The second planning risk is operator truthfulness. Automatic retries currently mutate the same `RunExecutionJob` row back to `pending`, which hides prior attempts. That conflicts with `D-03`. The planner should preserve `analysis_run_id` as the canonical run identity, but change attempt recording so each retry/reclaim remains visible while still attaching to the same run. Current worker-focused tests pass (`20 passed in 7.48s`), but they do not yet cover heartbeat renewal, ownership loss, or real Postgres concurrent-claim behavior.

**Primary recommendation:** Keep the existing Postgres + SQLAlchemy queue, add fenced lease heartbeats plus compare-and-set finalization, and make automatic retries produce durable attempt history on the same `analysis_run_id`.

## Preserve vs Change

- Preserve the existing DB-backed queue, `analysis_run_id` as the canonical persisted run identity, and the repository/worker/service layering.
- Preserve best-effort cancellation at explicit safe checkpoints; do not attempt thread kills or signal-based preemption.
- Preserve current status/health routes as additive contracts, not breaking rewrites.
- Change lease handling from static lease only to active heartbeat with ownership fencing.
- Change automatic retry/reclaim semantics so attempt history is durable and visible.
- Change validation from SQLite-only confidence to mixed SQLite plus Postgres concurrency proof for queue behavior.

## Standard Stack

### Core

| Library / Surface | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL locking clause | PostgreSQL 18 current docs | Multi-worker atomic claims and stale-row avoidance | Official docs explicitly say `SKIP LOCKED` can be used for queue-like tables |
| SQLAlchemy `Select.with_for_update()` | 2.0.49 current docs | Express `FOR UPDATE SKIP LOCKED` claims and guarded updates | Official first-class support for PostgreSQL lock variants |
| Existing `RunExecutionJob` + `AnalysisRun` model | repo current | Durable run identity plus queue/attempt persistence | Brownfield-safe; already matches current backend APIs and worker design |
| `pytest` | 8.4.2 installed, repo `>=8.0` | Worker lifecycle regression testing | Already established for backend integration and worker tests |

### Supporting

| Library / Surface | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Alembic | 1.14.0 installed, repo `>=1.14.0` | Add claim-token/history fields and any status metadata | Required for schema changes in this phase |
| `prometheus-client` | repo `>=0.21.0` | Queue and worker truthfulness metrics | Use for new attempt/heartbeat/lost-lease metrics only |
| Existing run status APIs | repo current | Preserve run-centric UX while surfacing attempt truth | Use additive response fields rather than breaking route rewrites |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing Postgres queue + SQLAlchemy | Redis/Celery/RQ/SQS | Too invasive for a hardening phase; breaks brownfield safety and observability continuity |
| Row-level locking + durable lease token | Advisory locks | Advisory locks are useful, but less aligned with durable queue-row inspection and current schema-driven operator surfaces |
| Immutable attempt history on the same run | Reusing one mutable queue row forever | Smaller migration, but hides attempt history and weakens operator truthfulness |

**Installation:**

```bash
# No new dependency is recommended for Phase 2.
# Use the existing backend stack from requirements-backend.txt / requirements-dev.txt.
```

**Version verification:** Verified against current official docs and local environment on 2026-04-15:
- SQLAlchemy 2.0 docs current release: `2.0.49` (released 2026-04-03)
- PostgreSQL current docs: `18.3` current supported version line (docs banner dated 2026-02-26)
- `pytest`: `8.4.2` installed locally
- Alembic: `1.14.0` installed locally

## Architecture Patterns

### Recommended Project Structure

```text
backend/
├── repositories/
│   └── run_execution_job_repository.py   # claim, heartbeat, reclaim, finalize CAS
├── worker/
│   ├── loop.py                           # claim -> execute -> finalize
│   └── lease.py                          # new ownership-token + heartbeat helper
├── services/
│   ├── edgar_pipeline_execution_service.py
│   └── run_lifecycle_service.py
├── schemas/
│   └── run_lifecycle.py                  # additive attempt-history/status fields
├── observability/
│   └── metrics.py                        # lease freshness and retry counters
└── api/routes/
    └── runs.py                           # preserve current status route, extend additively

tests/
├── test_worker_job_lifecycle.py          # SQLite lifecycle coverage
├── test_run_lifecycle_production.py      # cancel/retry/reclaim semantics
└── test_worker_job_lifecycle_postgres.py # new Postgres concurrency / fencing suite
```

### Pattern 1: Fenced Lease Ownership

**What:** Each successful claim writes a fresh ownership token (`claim_token`, `lease_token`, or equivalent). Every heartbeat, reclaim-sensitive update, and finalize path must include that token in its `WHERE` clause.

**When to use:** Any mutation that occurs after the claim transaction is committed.

**Why:** PostgreSQL row locks are released at transaction end. The current worker closes the claim session before the pipeline starts, so long-running safety must come from persisted lease ownership, not from the original row lock.

**Example:**

```python
# Source: SQLAlchemy docs + PostgreSQL locking docs + current repository pattern
stmt = (
    select(RunExecutionJob.id)
    .where(RunExecutionJob.status == RunExecutionJobStatus.pending)
    .order_by(RunExecutionJob.created_at.asc())
    .limit(1)
    .with_for_update(skip_locked=True)
)
```

### Pattern 2: Immutable Attempt History on the Same Run

**What:** Keep one `analysis_run_id`, but record each retryable execution attempt durably instead of rewriting the same queue row back to `pending`.

**When to use:** Manual retry, transient failure retry, or reclaim after lease expiry when the pipeline had already moved the run to `running`.

**Recommendation:** Prefer one durable job row per attempt. If the planner chooses a separate attempt table instead, the same rule applies: automatic retries must not erase prior attempt evidence.

**Important exception:** If a stale lease is reclaimed while the run is still `queued`, the prior worker never actually started pipeline execution. Extending the same attempt is acceptable there because no new attempt became externally meaningful.

### Pattern 3: Safe Checkpoint Heartbeat + Cancellation Probe

**What:** Centralize a helper such as `touch_or_abort()` that both renews the lease and re-checks run cancellation.

**When to use:** At minimum:
- after claim and before heavy work starts
- immediately before invoking the long-running orchestration pipeline
- immediately after orchestration returns
- before output payload persistence
- before artifact ingestion
- before terminal status/finalize writes

**Recommendation:** Start with execution-service checkpoints. Only push deeper into `src/` or orchestration internals if real stage durations exceed roughly half the configured lease window.

### Pattern 4: Additive Operator Truth Surfaces

**What:** Keep current run-centric APIs, but add attempt-history visibility rather than replacing the UX with job-centric endpoints.

**When to use:** `GET /v1/runs/{run_id}/status` and any operator/admin surfaces that already display queue state.

**Recommendation:** Preserve `latest_execution_job`, add either:
- a bounded `execution_job_history` list, or
- a lightweight `attempt_summary` plus a dedicated history route if payload size becomes awkward.

### Anti-Patterns to Avoid

- **Heartbeat by job id only:** A reclaimed stale worker could keep extending a lease it no longer owns.
- **Finalize by job id only:** A late-finishing worker could mark a superseded attempt completed after another worker already reclaimed or retried it.
- **Resetting the same job row to `pending` after every failure:** This destroys attempt history and violates `D-03`.
- **Treating SQLite as proof of PostgreSQL concurrency behavior:** SQLite can validate service logic, but not `SKIP LOCKED` semantics under concurrent claims.
- **Auto-retrying cancelled runs:** `D-04` makes cancellation terminal.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-worker claim arbitration | App-level mutexes or in-memory locks | PostgreSQL row locks with `SKIP LOCKED` via SQLAlchemy | Durable, inspectable, and already aligned with the current queue |
| Post-claim ownership | Blind heartbeat updates | Compare-and-set heartbeat/finalize guarded by claim token | Prevents stale workers from extending or completing reclaimed jobs |
| Attempt audit trail | Log-only retry traces | Durable job/attempt rows tied to `analysis_run_id` | Operator truth must survive process death and log rotation |
| Mid-flight cancellation | Thread kill or signal interruption | Explicit safe checkpoints in the execution service | The deterministic pipeline is synchronous and not designed for preemption |
| Retry identity | New run IDs per retry | Same `analysis_run_id` with durable attempt history | Matches locked decision `D-02`/`D-03` and existing run-centric UX |

**Key insight:** Once the claim transaction commits, the database lock is gone. From that point onward, lease correctness depends on persisted ownership state, not on the original `FOR UPDATE` lock.

## Common Pitfalls

### Pitfall 1: Heartbeat Without Fencing

**What goes wrong:** A worker that lost its lease can still renew or finalize the job.

**Why it happens:** The worker currently executes after claim commit, so the claim lock does not protect the long-running section.

**How to avoid:** Store a fresh claim token on every claim and require it on every heartbeat/finalize update.

**Warning signs:** Heartbeat updates succeed after a reclaim test, or two workers both believe they own the same run.

### Pitfall 2: Retry History Hidden by In-Place Row Reuse

**What goes wrong:** Operators see only the latest row state and cannot tell how many times a run actually retried.

**Why it happens:** The current transient-failure path mutates one `RunExecutionJob` row back to `pending`.

**How to avoid:** Make automatic retries durable as new attempt records or explicit attempt children.

**Warning signs:** `attempt_count` rises but there is still only one historical job row for the run.

### Pitfall 3: Cancellation and Retry Race

**What goes wrong:** A cancelled run gets requeued after a transient failure or stale-lease recovery path.

**Why it happens:** Retry logic reasons about exception type and attempt limits, but cancellation must override both.

**How to avoid:** Check `AnalysisRun.status == cancelled` before every retry scheduling branch and inside the heartbeat/checkpoint helper.

**Warning signs:** `RunExecutionJob.status == pending` appears for a cancelled run.

### Pitfall 4: False Confidence From SQLite-Only Tests

**What goes wrong:** Claim/reclaim logic appears correct locally but fails under real Postgres multi-worker contention.

**Why it happens:** SQLite does not validate PostgreSQL `SKIP LOCKED` behavior or row-lock timing.

**How to avoid:** Add a Postgres-backed concurrency suite for claim ordering, stale-finalizer fencing, and reclaim races.

**Warning signs:** No test creates two sessions/workers against Postgres for the same queue.

### Pitfall 5: Duplicate Execution Now Corrupts the Same Run Workspace

**What goes wrong:** Two workers executing the same `analysis_run_id` race inside the same run-scoped workspace.

**Why it happens:** Phase 1 intentionally keyed run workspaces by `analysis_run_id`; duplicate execution now targets the same durable workspace.

**How to avoid:** Treat lease ownership as a run-integrity boundary, not just a queue nicety.

**Warning signs:** The same run id emits overlapping artifact writes or inconsistent persisted artifacts.

## Code Examples

Verified patterns from official sources and current code:

### PostgreSQL Queue Claim With `SKIP LOCKED`

```python
# Source: https://docs.sqlalchemy.org/en/20/core/selectable.html
stmt = (
    select(RunExecutionJob.id)
    .where(RunExecutionJob.status == RunExecutionJobStatus.pending)
    .order_by(RunExecutionJob.created_at.asc())
    .limit(1)
    .with_for_update(skip_locked=True)
)
```

### Ownership-Checked Heartbeat

```python
# Source: inference from current repository + PostgreSQL transaction semantics
updated = session.execute(
    update(RunExecutionJob)
    .where(
        RunExecutionJob.id == job_id,
        RunExecutionJob.status == RunExecutionJobStatus.running,
        RunExecutionJob.claim_token == claim_token,
    )
    .values(lease_expires_at=lease_end)
)
if int(updated.rowcount or 0) != 1:
    raise LeaseLostError("worker no longer owns this job")
```

### Retry Scheduling That Preserves Run Identity

```python
# Source: recommended adaptation of current run_lifecycle/worker design
if transient and run.status != AnalysisRunStatus.cancelled and attempts_remaining:
    current_job.status = RunExecutionJobStatus.failed
    enqueue_new_pending_job(analysis_run_id=run.id, attempt_number=current_job.attempt_number + 1)
    transition_run_back_to_queued(run.id)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static long lease | Short renewable lease plus heartbeat while the worker still owns the job | Current best practice for queue-like Postgres tables; PostgreSQL current docs still position `SKIP LOCKED` for queue consumers | Long jobs stop relying on oversized lease windows |
| Blind post-claim updates | Ownership-fenced heartbeat/finalize (`claim_token` / CAS) | Inference from PostgreSQL transaction semantics and the current worker architecture | Prevents stale workers from extending or completing reclaimed jobs |
| Mutable single-row retry state | Immutable attempt history on the same `analysis_run_id` | Required by `D-03` and current operator-truth goal | Makes retries auditable without changing run identity |
| SQLite-only queue confidence | SQLite service tests plus Postgres concurrency regression | Needed because the documented stack is Postgres-backed | Prevents queue bugs that only appear under real row locking |

**Deprecated/outdated:**
- Static lease sizing as the primary protection mechanism: too fragile for long-running jobs.
- Requeue-by-row-reset as the only retry record: not sufficient once attempt visibility is a requirement.
- Finalize-by-primary-key only: unsafe after reclaim becomes possible.

## Open Questions

1. **Should automatic retries create new `RunExecutionJob` rows or a separate `RunExecutionAttempt` table?**
   - What we know: current mutable-row retries hide history, and `D-03` requires visible attempts.
   - What's unclear: whether the cleanest brownfield move is to repurpose `RunExecutionJob` as immutable-per-attempt or introduce a child table.
   - Recommendation: prefer immutable `RunExecutionJob` rows per attempt unless existing API/schema coupling makes that too disruptive.

2. **How deep do heartbeat checkpoints need to go into the deterministic pipeline?**
   - What we know: current checkpoints in [edgar_pipeline_execution_service.py](/Users/padraigobrien/agentic_data_science_system/backend/services/edgar_pipeline_execution_service.py) are coarse but already aligned with cancellation semantics.
   - What's unclear: whether any single orchestration or deterministic stage can exceed a safe fraction of the lease window.
   - Recommendation: start at execution-service boundaries, then add deeper stage checkpoints only if profiling shows real lease-pressure gaps.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Local backend execution and tests | ✓ (below target) | 3.11.0 | Use Docker Compose backend/runtime for Python 3.12 parity, or install Python 3.12 locally |
| `pytest` | Worker regression suite | ✓ | 8.4.2 | — |
| Alembic | Schema migration for lease/history fields | ✓ | 1.14.0 | — |
| Docker Compose | Postgres-backed validation path | ✓ | v5.1.1 | — |
| PostgreSQL CLI (`psql`, `pg_isready`) | Direct local DB smoke/debug | ✗ | — | Use `docker compose exec db ...` against the Compose Postgres service |

**Missing dependencies with no fallback:**
- None identified.

**Missing dependencies with fallback:**
- Local Python is below the repo's documented Python 3.12+ target; use Compose or install 3.12 for parity-sensitive validation.
- `psql` / `pg_isready` are not installed locally; Compose provides an operational fallback for Postgres checks.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` 8.4.2 installed locally, repo baseline `>=8.0` |
| Config file | [`pytest.ini`](/Users/padraigobrien/agentic_data_science_system/pytest.ini) |
| Quick run command | `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_run_lifecycle_production.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py -q` |
| Full suite command | `python3 -m pytest tests/ -q --tb=short` |

**Current baseline:** `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_run_lifecycle_production.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py -q` passed locally on 2026-04-15 (`20 passed in 7.48s`).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WORK-01 | Claimed jobs renew lease while active, lose ownership safely, and do not double-finalize after reclaim | integration + Postgres concurrency | `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_worker_job_lifecycle_postgres.py -q` | ❌ Wave 0 |
| WORK-02 | Retries, restarts, stale-lease recovery, and cancellation remain idempotent on the same run id | integration | `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_run_lifecycle_production.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py -q` | ✅ partially |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_run_lifecycle_production.py -q`
- **Per wave merge:** `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_run_lifecycle_production.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py -q`
- **Phase gate:** full worker slice plus new Postgres concurrency coverage green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_worker_job_lifecycle_postgres.py` — concurrent `SKIP LOCKED` claim behavior against real Postgres
- [ ] `tests/test_worker_lease_heartbeat.py` — long-running heartbeat renewal and lost-ownership abort/finalize behavior
- [ ] `tests/test_worker_attempt_history.py` — automatic retry/reclaim creates durable attempt history on the same run
- [ ] Shared Postgres fixture or Compose-backed helper for worker queue concurrency tests

## Sources

### Primary (HIGH confidence)

- Current repository code:
  - [run_execution_job_repository.py](/Users/padraigobrien/agentic_data_science_system/backend/repositories/run_execution_job_repository.py)
  - [loop.py](/Users/padraigobrien/agentic_data_science_system/backend/worker/loop.py)
  - [run_lifecycle_service.py](/Users/padraigobrien/agentic_data_science_system/backend/services/run_lifecycle_service.py)
  - [edgar_pipeline_execution_service.py](/Users/padraigobrien/agentic_data_science_system/backend/services/edgar_pipeline_execution_service.py)
  - [run_lifecycle.py](/Users/padraigobrien/agentic_data_science_system/backend/schemas/run_lifecycle.py)
  - [test_worker_job_lifecycle.py](/Users/padraigobrien/agentic_data_science_system/tests/test_worker_job_lifecycle.py)
  - [test_run_lifecycle_production.py](/Users/padraigobrien/agentic_data_science_system/tests/test_run_lifecycle_production.py)
- SQLAlchemy 2.0 docs: https://docs.sqlalchemy.org/en/20/core/selectable.html
  - Verified `Select.with_for_update(skip_locked=True)` support and current release metadata
- PostgreSQL current `SELECT` docs: https://www.postgresql.org/docs/current/sql-select.html
  - Verified `NOWAIT | SKIP LOCKED` locking clause and queue-like-table guidance
- PostgreSQL current explicit locking docs: https://www.postgresql.org/docs/current/explicit-locking.html
  - Verified row locks are held until transaction end and released at transaction end

### Secondary (MEDIUM confidence)

- [docs/local-stack.md](/Users/padraigobrien/agentic_data_science_system/docs/local-stack.md) — documented Postgres-backed runtime and worker deployment
- [CONCERNS.md](/Users/padraigobrien/agentic_data_science_system/.planning/codebase/CONCERNS.md) — current queue/lease/test risks
- [TESTING.md](/Users/padraigobrien/agentic_data_science_system/.planning/codebase/TESTING.md) — current test architecture and gaps

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses current official PostgreSQL and SQLAlchemy docs plus the repo's existing architecture
- Architecture: HIGH - Directly grounded in current worker/repository/service code and validated against official lock semantics
- Pitfalls: HIGH - Supported by current code paths, existing concerns, and worker test coverage limits

**Research date:** 2026-04-15
**Valid until:** 2026-05-15
