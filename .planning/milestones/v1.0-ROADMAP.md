# Roadmap: Agentic Data Science System Hardening

## Overview

This roadmap turns an already-valuable EDGAR analysis platform into a dependable multi-user product by first removing shared execution-path ambiguity, then hardening worker semantics, tightening security defaults, expanding automated verification, and finally addressing storage and operational scaling limits. Each phase is scoped around a distinct trust boundary so the system becomes safer and more observable without destabilizing the deterministic analysis core that already works.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Run Isolation** - Remove shared artifact-path and cwd assumptions from the execution flow
- [x] **Phase 2: Worker Resilience** - Make queued execution lease-safe and retry-safe under overlap and failure
- [x] **Phase 3: Secure Defaults** - Enforce safe deployment defaults for auth, registration, metrics, and persisted payloads
- [x] **Phase 4: CI Coverage** - Gate the documented stack and key user flows with automated verification
- [x] **Phase 5: Storage and Ops** - Improve storage efficiency, retention policy, and operational truthfulness (completed 2026-04-17)

## Phase Details

### Phase 1: Run Isolation
**Goal**: Introduce explicit per-run workspaces and artifact-path contracts so every execution is isolated from other runs.
**Depends on**: Nothing (first phase)
**Requirements**: [EXEC-01, EXEC-02, EXEC-03]
**Success Criteria** (what must be TRUE):
  1. User can trigger overlapping runs without processed files or artifacts being overwritten across runs
  2. Generated reports and artifacts are resolved from explicit run-scoped paths instead of repo-global defaults
  3. Operator can rerun or resume a run without relying on cwd mutation or implicit repo-root path discovery
**Plans**: 4 plans

Plans:
- [x] 01-01: Define run-scoped workspace and artifact-path contracts across `src/`, `edgar_project/`, and `backend/`
- [x] 01-02: Refactor deterministic writers, readers, and orchestration to pass explicit paths end-to-end
- [x] 01-03: Migrate backend, CLI, direct entrypoints, and deployment docs to the shared run-workspace contract
- [x] 01-04: Add regression coverage for overlapping runs, artifact ownership, and no-cwd entrypoints

### Phase 2: Worker Resilience
**Goal**: Make background execution robust when jobs run long, retry, or are reclaimed after worker interruption.
**Depends on**: Phase 1
**Requirements**: [WORK-01, WORK-02]
**Success Criteria** (what must be TRUE):
  1. Long-running jobs renew or safely expire leases without causing duplicate execution
  2. Retries and worker restarts preserve run correctness and idempotency
  3. Queue semantics remain correct when the worker is interrupted and resumed
**Plans**: 3 plans

Plans:
- [x] 02-01: Add claim-token heartbeat and lease-loss fencing to worker execution
- [x] 02-02: Convert retries and stale reclaims into durable per-attempt run history
- [x] 02-03: Add SQLite and Postgres regressions for heartbeat, recovery, and status history

### Phase 3: Secure Defaults
**Goal**: Eliminate insecure production defaults and reduce exposure of sensitive operational data.
**Depends on**: Phase 2
**Requirements**: [SECU-01, SECU-02, SECU-03]
**Success Criteria** (what must be TRUE):
  1. Production-like startup fails when unsafe built-in secrets are still configured
  2. Open self-service registration is disabled by default outside explicit opt-in scenarios
  3. Metrics and sensitive stored payload fields are protected, redacted, or explicitly gated
**Plans**: 3 plans

Plans:
- [x] 03-01: Enforce secure configuration validation for JWT secrets and registration posture
- [x] 03-02: Reduce sensitive payload exposure in APIs, persistence, and metrics surfaces
- [x] 03-03: Add security-focused tests and operator-facing configuration guidance

### Phase 4: CI Coverage
**Goal**: Align automated verification with the documented product stack and critical user journeys.
**Depends on**: Phase 3
**Requirements**: [QUAL-01, QUAL-02, QUAL-03]
**Success Criteria** (what must be TRUE):
  1. Pull requests validate the documented Postgres, API, worker, and frontend integration path
  2. Authenticated frontend flows, artifact delivery, and trace navigation are exercised automatically
  3. Concurrency and lease-safety regressions fail CI before they reach users
**Plans**: 3 plans

Plans:
- [x] 04-01: Expand CI to cover the documented multi-service stack
- [x] 04-02: Add frontend integration or browser-level tests for authenticated run workflows
- [x] 04-03: Add concurrency and artifact-collision regression suites to CI

### Phase 5: Storage and Ops
**Goal**: Make storage and observability behave truthfully and scale with sustained usage.
**Depends on**: Phase 4
**Requirements**: [OPER-01, OPER-02, OPER-03]
**Success Criteria** (what must be TRUE):
  1. Health and metrics endpoints signal dependency failures explicitly instead of reporting misleading zero state
  2. Artifact ingestion handles large files without unnecessary full-memory copies
  3. Operators can bound retained run and model payload history with a documented policy that preserves required auditability
**Plans**: 4 plans

Plans:
- [x] 05-01: Make `/v1/worker/health` and `/metrics` expose explicit degraded queue state
- [x] 05-02: Add streamed local object-store ingest for pipeline artifact copies
- [x] 05-03: Add retention schema, policy settings, and the explicit maintenance workflow
- [x] 05-04: Add retention-aware artifact delivery semantics and operator documentation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Run Isolation | 4/4 | Completed | 2026-04-15 |
| 2. Worker Resilience | 3/3 | Completed | 2026-04-16 |
| 3. Secure Defaults | 3/3 | Completed | 2026-04-16 |
| 4. CI Coverage | 3/3 | Completed | 2026-04-17 |
| 5. Storage and Ops | 4/4 | Complete   | 2026-04-17 |
