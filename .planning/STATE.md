---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to Execute Phase 04
stopped_at: Phase 04 plans validated
last_updated: "2026-04-16T22:33:48Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 13
  completed_plans: 10
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Every EDGAR run must produce trustworthy, isolated, auditable results that the user can inspect without ambiguity.
**Current focus:** Phase 04 — ci-coverage

## Current Position

Phase: 04 (ci-coverage) — PLANNED
Next: `$gsd-execute-phase 4`

## Performance Metrics

**Velocity:**

- Total plans completed: 10
- Average duration: 10 min
- Total execution time: 1.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-run-isolation | 4 | 38min | 10min |
| 02-worker-resilience | 3 | 44min | 15min |
| 03-secure-defaults | 3 | 22min | 7min |

**Recent Trend:**

- Last 5 plans: 02-worker-resilience-02 (10min), 02-worker-resilience-03 (17min), 03-secure-defaults-01 (6min), 03-secure-defaults-02 (7min), 03-secure-defaults-03 (9min)
- Trend: Stable

| Phase 01-run-isolation P01 | 14min | 3 tasks | 12 files |
| Phase 01-run-isolation P02 | 20min | 2 tasks | 15 files |
| Phase 01-run-isolation P03 | 3min | 2 tasks | 10 files |
| Phase 01-run-isolation P04 | 1min | 2 tasks | 7 files |
| Phase 02 P01 | 17min | 2 tasks | 12 files |
| Phase 02 P02 | 10min | 2 tasks | 12 files |
| Phase 02 P03 | 17min | 2 tasks | 5 files |
| Phase 03-secure-defaults P01 | 6min | 2 tasks | 11 files |
| Phase 03-secure-defaults P02 | 7min | 2 tasks | 14 files |
| Phase 03-secure-defaults P03 | 9min | 2 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Initialization: Treat the repo as a brownfield hardening effort, not a greenfield rebuild
- Initialization: Prioritize run isolation and trust boundaries before feature expansion
- Initialization: Keep planning docs in git so architecture and operations decisions remain auditable
- [Phase 01-run-isolation]: Model run isolation with a frozen RunWorkspace contract that keeps manual_validation_csv as an explicit shared input.
- [Phase 01-run-isolation]: Expose run_workspace as a serialized orchestration context payload before runtime adoption changes land.
- [Phase 01-run-isolation]: Keep remaining shared-path report behavior behind an explicit MCP legacy flag instead of a hidden zero-arg fallback.
- [Phase 01-run-isolation]: Normal Phase 1 execution now resolves writers, reports, and trustworthiness lookups from explicit workspace paths instead of repo-global defaults.
- [Phase 01-run-isolation]: The orchestration executor injects upstream artifact paths and run_workspace payloads into later MCP steps when the planner leaves path placeholders empty.
- [Phase 01-run-isolation]: Persisted backend runs now store one `analysis_run_id`-anchored workspace payload across execution context, run metadata, and ingested artifact provenance.
- [Phase 01-run-isolation]: CLI, `main.py`, and deployment docs now treat `data/runs/<run_scoped_id>` or `/var/lib/edgar/run_workspaces` as the normal execution root and avoid cwd mutation.
- [Phase 01-run-isolation]: Overlap safety is now locked by a real dual-workspace artifact-write regression instead of a skipped seed.
- [Phase 01-run-isolation]: Shared artifact footer/default-path expectations remain covered only through explicit legacy opt-in tests; normal regressions use run-scoped paths.
- [Phase 02-worker-resilience]: Active jobs should renew their lease with a heartbeat instead of relying on static long leases.
- [Phase 02-worker-resilience]: Lease expiry should automatically requeue the same persisted run up to attempt limits rather than creating a new run identity.
- [Phase 02-worker-resilience]: Retry attempts should remain attached to the same run but stay explicitly visible in job/status history.
- [Phase 02-worker-resilience]: Cancellation during active execution is best-effort at safe checkpoints and cancelled runs never auto-retry.
- [Phase 02-worker-resilience]: Worker ownership is now fenced by per-claim `claim_token` compare-and-set checks instead of relying only on row-lock timing.
- [Phase 02-worker-resilience]: Long-running worker attempts now renew leases in the background and check ownership before orchestration dispatch and persistence boundaries.
- [Phase 02-worker-resilience]: `WorkerLeaseLostError` now rolls back in-flight execution state instead of persisting a stale run error after ownership is gone.
- [Phase 02-worker-resilience]: Execution job history is now one durable row per attempt, starting at attempt `1`, instead of a single mutable retry row.
- [Phase 02-worker-resilience]: Transient retry and stale-running reclaim now preserve the failed attempt row and create the next pending row only when attempts remain.
- [Phase 02-worker-resilience]: `/v1/runs/{run_id}/status` keeps `latest_execution_job` for compatibility and adds ordered `execution_job_history` for operator truthfulness.
- [Phase 02-worker-resilience]: Cancelled runs now surface cancelled execution history and never auto-create a replacement pending attempt.
- [Phase 02-worker-resilience]: Postgres claim/reclaim locking is now verified with isolated temporary databases instead of relying on SQLite-only confidence.
- [Phase 02-worker-resilience]: `/v1/worker/health` and `/metrics` are now pinned to the same claimability and stale-lease truth conditions by regression tests.
- [Phase 02-worker-resilience]: Attempt history is now regression-covered across transient retry, stale-running reclaim, manual retry, and lease-loss finalize reporting.
- [Phase 03-secure-defaults]: Built-in JWT secrets must fail startup unless an explicit insecure-dev override is enabled.
- [Phase 03-secure-defaults]: Registration is planned to be closed by default, with first-admin onboarding moved to an explicit bootstrap route.
- [Phase 03-secure-defaults]: `/metrics` and `/v1/worker/health` are planned to require a dedicated ops token, while raw payload/meta expansions are planned to require privileged access and sanitized artifact provenance.
- [Phase 03-secure-defaults]: Reject the built-in JWT secret by exact value unless EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true is set explicitly.
- [Phase 03-secure-defaults]: Close self-service registration by default and require a dedicated X-EDGAR-Bootstrap-Token flow for the first admin.
- [Phase 03-secure-defaults]: Persist is_admin on users now so later Phase 3 plans can gate privileged payload and ops access without redesigning auth.
- [Phase 03-secure-defaults]: Keep owner-scoped run and artifact routes summary-first, but require admin privilege before honoring raw payload or meta expansion flags.
- [Phase 03-secure-defaults]: Require the documented compose stack to source JWT, bootstrap, and ops secrets from .env instead of shipping insecure fallbacks.
- [Phase 03-secure-defaults]: Keep the register page available, but make its copy and error handling point users to the operator-controlled bootstrap path when registration is closed.
- [Phase 04-ci-coverage]: Add a PR-required full-stack gate for the documented Postgres + API + worker + web stack alongside the current faster CI jobs rather than replacing them.
- [Phase 04-ci-coverage]: CI should validate the secure-default bootstrap-admin and ops-token flows instead of weakening auth for tests.
- [Phase 04-ci-coverage]: Authenticated frontend run-answer, trace, and artifact-delivery paths should be covered by a narrow browser-level flow.
- [Phase 04-ci-coverage]: Collision, lease, and Postgres queue regressions should be promoted into PR-required targeted test slices for faster failure isolation.
- [Phase 04-ci-coverage]: The CI plan splits into a secure-default full-stack Compose gate, a seeded Playwright browser path, and a separate Postgres regression workflow instead of one monolithic integration job.
- [Phase 04-ci-coverage]: The full-stack smoke flow must use fixed admin credentials so bootstrap reruns remain login-capable after `409 Bootstrap already completed`.
- [Phase 04-ci-coverage]: Required merge gating needs an explicit GitHub branch-protection/ruleset checkpoint; PR-triggered workflows alone are not enough.

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 4 CI coverage is now planned; the next open trust boundary is implementing the new workflows, Playwright fixture path, and required-check checkpoint without destabilizing the current stack
- The separate `.gitignore` and `.planning/config.json` edits remain outside the planning commits and should stay untouched during Phase 4 execution unless intentionally incorporated

## Session Continuity

Last session: 2026-04-16T22:33:48Z
Stopped at: Phase 04 plans validated
Resume file: .planning/phases/04-ci-coverage/04-ci-coverage-01-PLAN.md
