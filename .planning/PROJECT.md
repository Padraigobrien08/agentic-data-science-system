# Agentic Data Science System

## What This Is

Agentic Data Science System is a brownfield EDGAR analysis platform that combines a deterministic financial-analysis pipeline with a FastAPI backend, a background worker, MCP tooling, and a Next.js web app. It is built for operators and analysts who need traceable SEC-based runs, inspectable artifacts, and a path from local experimentation to a dependable multi-user product.

## Core Value

Every EDGAR run must produce trustworthy, isolated, auditable results that the user can inspect without ambiguity.

## Requirements

### Validated

- ✓ Users can run deterministic EDGAR analyses from the CLI, MCP layer, and backend execution path and receive tabular plus Markdown artifacts — existing
- ✓ Users can authenticate, create projects, launch runs, and inspect artifacts and trace data through the FastAPI and Next.js application layers — existing
- ✓ The platform persists run steps, tool calls, artifacts, and model-call metadata so execution is traceable after a run completes — existing
- ✓ The repo already supports a documented self-hosted stack with API, worker, Postgres, frontend, tests, and Docker-based local workflows — existing
- ✓ Every run now uses an explicit run-scoped workspace and artifact-path contract, so overlapping execution no longer depends on shared repo-global outputs — validated in Phase 1
- ✓ Background execution is now lease-safe, retry-safe, and auditable on one persisted run identity — validated in Phase 2
- ✓ Deployment defaults now fail closed for JWT secrets, self-service registration, ops telemetry, and raw payload exposure — validated in Phase 3
- ✓ Pull requests now gate the documented Compose stack, seeded browser run workflows, and focused Postgres regressions instead of relying on narrow backend/frontend checks alone — validated in Phase 4
- ✓ Storage and operations now surface degraded dependency state truthfully, stream artifact ingest without full-memory copies, and support explicit audit-preserving retention workflows — validated in Phase 5
- ✓ Validation outcomes now expose explicit degradation classes, and live or hybrid evaluation stays operator-invoked and non-default behind explicit policy plus `--allow-live` guardrails — validated in Phase 6
- ✓ Artifact storage now supports a configured S3-compatible backend behind the same opaque artifact IDs, authorized delivery routes, and reconciliation-visible retention semantics as local storage — validated in Phase 7
- ✓ Large trace views now open on typed summaries, bounded collections, and item-scoped raw drill-downs instead of first-load payload hydration — validated in Phase 8
- ✓ Supported evaluation runs and case results are now first-class persisted project-scoped records with stored case metadata, reopenable case routes, and CLI compatibility through curated suite IDs — validated in Phase 9
- ✓ Live and hybrid evaluation now executes through linked canonical child runs, and health plus metrics surfaces report evaluation SEC or storage degradation truthfully — validated in Phase 10
- ✓ The documented local stack now boots the worker cleanly, executes chat-triggered runs reliably, surfaces sync-first background-delivery truth in chat, and no longer presents a dead-end secure-default registration path — validated in Phase 12

### Active

- [ ] Chat becomes the primary surface for reading completed analysis answers instead of the standalone run page
- [ ] Users can navigate from a chat answer to report, evidence, artifacts, critic, and trace surfaces through one compact navigation area
- [ ] Normal analyst phrasing in chat routes to supported analysis paths or returns actionable rewrite guidance instead of dead-end intent failures

### Out of Scope

- New anomaly-detection models or analytical feature work — reliability and product trust are the current bottlenecks, not model breadth
- Mobile or native clients — the existing web, CLI, and MCP surfaces are sufficient until the platform core is production-safe
- Multi-region or managed-cloud deployment work — the current target remains the documented self-hosted stack until isolation and ops basics are solid

## Current State

**Shipped:** `v1.1 Live Validation and Scale` on 2026-04-18
**Status:** The platform now supports policy-gated live validation, S3-compatible artifact storage, summary-first large-trace browsing, a persisted evaluation control plane, canonical child-run execution for live and hybrid evaluation, clean archive-grade planning traceability, and a repaired sync-first chat runtime in the documented local stack. Fresh hands-on testing still shows the next product bottlenecks clearly: ordinary analyst phrasing remains too brittle, and the primary answer-reading experience still lives on a fragmented run page instead of in chat.

## Current Milestone: v1.2 Chat-First Analysis Experience

**Goal:** Make workspace chat the primary place where users receive, inspect, and continue analysis answers, while fixing the runtime and prompt-handling issues that currently break that experience.

**Target features:**
- Deliver completed run answers directly into workspace chat with stable linkage back to the underlying run
- Attach one compact evidence-navigation area to the chat answer for report, evidence, artifacts, critic output, and trace views
- Accept normal analyst phrasing in chat for common deterioration, anomaly, and peer-comparison requests, or return helpful rewrite guidance
- Keep the documented Compose stack reliable enough for chat-native delivery, including run-workspace writes and background execution

## Future Milestone Candidates

- Environment-aware onboarding so secure-default deployments do not present dead-end registration flows
- Scheduled live canary suites with alerting and explicit request-budget controls
- Promotion of failing live or hybrid cases into deterministic fixture regressions
- Cross-run evidence-coverage and weak-evidence summaries for operator review

## Context

This repo is a layered brownfield monorepo with a deterministic EDGAR analysis core in `src/`, an orchestration and MCP layer in `edgar_project/`, a persistence and API shell in `backend/`, and a Next.js frontend in `frontend/`. The existing system already proves value by producing SEC-based analysis artifacts, exposing traceable runs, and supporting authenticated project/run workflows, but the codebase map showed that several core platform assumptions still depended on shared filesystem paths, cwd mutation, and large multi-responsibility modules before the v1.0 hardening effort.

The highest-value work in v1.0 was operational rather than feature-based, and all five trust-boundary phases are now complete. Run outputs are isolated, worker attempts are lease-safe and auditable, insecure auth and ops defaults are removed, pull-request CI exercises the documented stack and key user flows, and storage or retention behavior now scales more honestly under sustained usage. The project has therefore shipped a v1.0 hardening baseline for an already-valuable system. The v1.1 milestone then added explicit live-validation policy boundaries, a remote object-store contract, a summary-first large-trace experience, a first-class persisted evaluation control plane, canonical child-run execution for live or hybrid validation, truthful evaluation dependency observability on the existing ops surfaces, and the final Phase 11 bookkeeping cleanup that restored clean archival traceability.

The next milestone comes directly from local product testing after the `v1.1` ship. The current answer-reading flow still pushes users onto a dense standalone run page with repeated evidence chips and buried caveats, even when the natural place to read the result is the workspace chat that launched the run. The same testing also surfaced two supporting failures that block trust in a chat-first experience: ordinary analyst wording can still miss the deterministic intent matcher, and the background worker still fails to boot in Compose because of a circular import. `v1.2` therefore needs to move the answer into chat while fixing the delivery seams that make that experience brittle today.

## Constraints

- **Tech stack**: Keep the existing Python + FastAPI + SQLAlchemy + Next.js + Postgres architecture — hardening should preserve established surfaces instead of forcing a rewrite
- **Brownfield safety**: Prefer explicit seams and incremental migrations over invasive refactors — the current product already has working CLI, MCP, backend, and frontend flows
- **Deterministic analysis**: Preserve the non-LLM numerical path in `src/` — run trust depends on keeping deterministic EDGAR computations inspectable
- **Compatibility**: Avoid breaking existing run APIs, artifact access patterns, and local development workflows unless a migration path is introduced — operators already rely on the current surfaces
- **Security**: Defaults must be safe in deployed environments — current permissive defaults are acceptable for local development only
- **Operational clarity**: Health, metrics, and retained run data must reflect real system state — false green signals are worse than noisy failures

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat this as a brownfield hardening project, not a new-feature milestone | The current platform already delivers EDGAR analyses; trust, concurrency, and operability are the blockers to wider use | ✓ Good |
| Preserve the deterministic `src/` analysis core and harden the boundaries around it | Rewriting the numerical path would increase risk and distract from the isolation and reliability problems that matter now | ✓ Good |
| Prioritize run-scoped artifact contracts before other platform improvements | Shared global artifact paths create the largest correctness risk for concurrent or repeated execution | ✓ Good |
| Expand verification around the documented self-hosted stack instead of relying on narrow happy-path tests | The repo already documents API, worker, frontend, and Postgres workflows that are not fully gated today | ✓ Good |
| Track project planning artifacts in git | The hardening work touches architecture, security, and operations decisions that should remain auditable alongside code changes | ✓ Good |
| Roll out remote artifact storage as configured-write plus mixed-read behind opaque `s3:` locators | Brownfield deployments need remote storage without bucket exposure or forced migration of existing `local:` artifacts | ✓ Good |
| Treat blob-store and database divergence as explicit reconciliation state, not hidden transactional success | Remote object storage is a separate system, so deletes and retention must surface repairable drift instead of pretending they are atomic | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-18 after Phase 12 completion*
