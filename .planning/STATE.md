---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Chat-First Analysis Experience
status: Ready to plan Phase 14
stopped_at: Phase 14 context captured; ready to plan
last_updated: "2026-04-19T00:32:00Z"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-18)

**Core value:** Every EDGAR run must produce trustworthy, isolated, auditable results that the user can inspect without ambiguity.
**Current focus:** Plan Phase 14 of `v1.2 Chat-First Analysis Experience`, focused on making completed run answers first-class chat messages with stable run linkage.

## Current Position

Phase: 14
Plan: Not started
Milestone: `v1.2 Chat-First Analysis Experience`
Status: Ready to plan Phase 14
Last activity: 2026-04-19 — Captured Phase 14 context covering compact inline answer scope, in-place message upgrades, persisted-run history hydration, compact run linkage, and no implicit prior-run context carry-forward

## Performance Metrics

**Velocity:**

- Total plans completed: 35
- Average duration: 9 min
- Total execution time: 5.4 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-run-isolation | 4 | 38min | 10min |
| 02-worker-resilience | 3 | 44min | 15min |
| 03-secure-defaults | 3 | 22min | 7min |
| 04-ci-coverage | 3 | 42min | 14min |
| 05-storage-and-ops | 4 | 27min | 7min |
| 06-validation-boundaries-and-policy | 3 | 13min | 4min |
| 07-remote-artifact-storage-contract | 3 | 21min | 7min |
| 08-summary-first-large-trace-views | 3 | 29min | 10min |
| 09-evaluation-control-plane | 3 | 46min | 15min |
| 10-live-hybrid-execution-hardening | 3 | 45min | 15min |
| 11-milestone-audit-traceability-cleanup | 3 | 13min | 4min |
| 12-runtime-reliability-for-chat-delivery | 3 | 19min | 6min |
| 13-analyst-prompt-routing | 3 | 23min | 8min |

**Recent Trend:**

- Last 5 plans: 12-runtime-reliability-for-chat-delivery-02 (7min), 12-runtime-reliability-for-chat-delivery-03 (6min), 13-analyst-prompt-routing-01 (7min), 13-analyst-prompt-routing-02 (8min), 13-analyst-prompt-routing-03 (8min)
- Trend: Stable; runtime reliability is restored and the next bottleneck has moved to chat-native answer delivery rather than request routing.

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting the completed milestone:

- [Phase 6-validation-boundaries-and-policy]: Validation must stay policy-distinct from normal user work, even before later phases add child analysis-run linkage or richer evaluation workflows.
- [Phase 6-validation-boundaries-and-policy]: Validation outcomes must distinguish `product_regression`, `upstream_sec_degraded`, `stale_source`, and `policy_skipped`.
- [Phase 6-validation-boundaries-and-policy]: Fixture and mocked evaluation remain the default path; `live` and `hybrid` stay explicit operator-invoked and non-merge-blocking by default.
- [Phase 6-validation-boundaries-and-policy]: `live` and `hybrid` are judged on invariants and freshness windows, not exact-value equality.
- [Phase 7-remote-artifact-storage-contract]: Standard AWS S3 semantics are the canonical remote-storage contract, while configuration may still target S3-compatible endpoints.
- [Phase 7-remote-artifact-storage-contract]: `storage_uri` remains an app-owned opaque locator and normal artifact delivery stays behind application-owned authorized routes.
- [Phase 8-summary-first-large-trace-views]: Large traces should open on a compact overview with separate summary panels rather than the current full deep-dive stack.
- [Phase 8-summary-first-large-trace-views]: Privileged raw payloads should be fetched on demand per item, not page-wide through initial `include_payloads=true` loads.
- [Phase 9-evaluation-control-plane]: Supported evaluation workflows should be API-backed first, with the CLI retained only as a compatibility path.
- [Phase 9-evaluation-control-plane]: Supported evaluation launches should use curated suite IDs or approved manifests rather than arbitrary repo file paths.
- [Phase 9-evaluation-control-plane]: Evaluation ownership should be project-scoped by default rather than introducing a global operator-only auth model.
- [Phase 9-evaluation-control-plane]: Reopened evaluation history should expose persisted run summary plus explicit per-case results, not just a `results_json` blob.
- [Phase 10-live-hybrid-execution-hardening]: Live or hybrid evaluation starts should enqueue canonical child analysis runs and return immediately instead of executing inline.
- [Phase 10-live-hybrid-execution-hardening]: Each live or hybrid evaluation case should link directly to child `AnalysisRun` records, with latest-run pointer plus bounded prior history.
- [Phase 10-live-hybrid-execution-hardening]: Evaluation case verdicts should be derived from linked `AnalysisRun` terminal status plus existing degradation taxonomy rather than a parallel lifecycle.
- [Phase 10-live-hybrid-execution-hardening]: Existing `/health`, `/v1/worker/health`, and `/metrics` surfaces should expose evaluation-specific SEC or storage degradation explicitly.
- [Phase 12-runtime-reliability-for-chat-delivery]: Chat should force synchronous execution for now; background queueing should not remain a co-equal default while the worker path is unreliable.
- [Phase 12-runtime-reliability-for-chat-delivery]: If background delivery is unavailable, chat may automatically fall back to synchronous execution, but that fallback must still be visible in workspace and per-message status.
- [Phase 12-runtime-reliability-for-chat-delivery]: Phase 12 may pull in auth/onboarding fixes found during live testing if they materially block first-run chat delivery.
- [Phase 12-runtime-reliability-for-chat-delivery]: The planned implementation is split into 3 sequential waves: worker/runtime foundation, sync-first chat runtime contract, and auth/onboarding cleanup.
- [Phase 12-runtime-reliability-for-chat-delivery]: The documented stack now satisfies `RUN-01`, `RUN-02`, and `RUN-03`, so the next milestone bottleneck is request routing and chat-native answer delivery rather than runtime boot or onboarding.
- [Phase 13-analyst-prompt-routing]: Broad analyst theses should map to the closest supported deterioration/trend route when there are enough business cues; users should not need anomaly-specific wording.
- [Phase 13-analyst-prompt-routing]: Broader peer-relative language is allowed, but multiple tickers alone must not force peer mode.
- [Phase 13-analyst-prompt-routing]: Prompt text may narrow to a subset already in the workspace scope, but must not silently expand scope to outside symbols.
- [Phase 13-analyst-prompt-routing]: Unsupported routing should return concrete rewrite suggestions, and any LLM rescue path must remain explicit, gated, and auditable.
- [Phase 13-analyst-prompt-routing]: The planned implementation is split into 3 sequential waves: deterministic routing foundation, deterministic preview/guidance contract, and chat/example alignment.
- [Phase 13-analyst-prompt-routing]: Planner guidance stays on PlanningOutcome so preview callers return the exact deterministic routing result instead of re-deriving suggestions in the API layer.
- [Phase 14-chat-native-result-contract]: Move a compact primary answer block into chat now, while keeping findings, caveats, and navigation depth for Phase 15.
- [Phase 14-chat-native-result-contract]: Each user prompt should keep one assistant message that upgrades in place from pending to final instead of emitting duplicate completion chatter.
- [Phase 14-chat-native-result-contract]: Reload-safe chat history should be hydrated from persisted project runs, but Phase 14 should not add full persisted chat-thread infrastructure yet.
- [Phase 14-chat-native-result-contract]: Completed chat answers should show a compact run identity strip with one primary run action, not the current multi-link sprawl.
- [Phase 14-chat-native-result-contract]: Follow-up prompts stay as new analyses in the same visible thread, without implicit prior-run context injection.

### Pending Todos

None.

### Blockers/Concerns

- Completed analyses still read primarily through the standalone run page rather than the chat surface that launched them.
- Chat does not yet have a first-class result contract, so the conversation still loses the completed answer as a primary artifact.
- Evidence navigation is still fragmented across run-page sections instead of one compact chat-attached surface.
- Non-blocking carry-over: `python -m backend.maintenance.retention` still emits a `runpy` `RuntimeWarning` because `backend/maintenance/__init__.py` eagerly imports the module.

## Session Continuity

Last session: 2026-04-18T22:04:42Z
Stopped at: Phase 14 context captured; ready to plan
Resume file: .planning/PROJECT.md
