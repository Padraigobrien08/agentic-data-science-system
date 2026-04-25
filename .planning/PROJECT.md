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
- ✓ Normal analyst phrasing in chat now routes to supported deterioration, anomaly, and peer-comparison flows, and unsupported prompts return rewrite guidance before failed run creation — validated in Phase 13
- ✓ Workspace chat now hydrates persisted run history and renders completed analyses inline with one compact run-linked answer card, so the standalone run page is no longer the primary reading surface — validated in Phase 14
- ✓ Workspace chat answers now include inline findings, confidence/caveats, compact evidence navigation, and quiet exact-jump verification links without leaving the transcript — validated in Phase 15
- ✓ The standalone run page now acts as a secondary inspection surface focused on verification rather than duplicating the primary answer — validated in Phase 16
- ✓ Workspace chat answers now render as backend-authored narrative replies with explicit full, partial, legacy, and error behavior, so the answer reads like an analyst memo instead of a summary card — validated in Phase 17
- ✓ Workspace chat answers now surface evidence strength inline in the answer header through one compact semantic pill with a grouped explainer, instead of a large standalone confidence block — validated in Phase 18
- ✓ Workspace chat answers now treat evidence as supplemental through a collapsed proof disclosure, slim exact-jump evidence rows, and a quiet secondary navigation strip beneath the answer — validated in Phase 19

### Active

- ✓ Users experience the product primarily as a chat with history instead of a workspace shell with redundant framing — validated in Phase 22/23
- ✓ Users can manage analysis scope as lightweight conversation context without leaving the chat flow — validated in Phase 24
- ✓ Users can read a tighter answer layout that begins closer to the prompt and uses width more effectively before proof and secondary navigation appear — validated in Phase 25
- ✓ Users can treat trace and artifact views as technical deep dives linked from chat instead of as competing primary destinations — validated in Phase 26

### Out of Scope

- New anomaly-detection models or analytical feature work — reliability and product trust are the current bottlenecks, not model breadth
- Mobile or native clients — the existing web, CLI, and MCP surfaces are sufficient until the platform core is production-safe
- Multi-region or managed-cloud deployment work — the current target remains the documented self-hosted stack until isolation and ops basics are solid

## Current State

**Shipped:** `v1.4 Conversation-First Information Architecture` on 2026-04-25
**Status:** The platform now presents as chat with history and lightweight scope, while keeping trace and artifacts as secondary technical deep dives.

## Current Milestone

No active milestone is defined. `v1.4` is complete and archived.

## Future Milestone Candidates

- Multi-run conversation workflows so analysts can compare or revisit prior runs inside one chat thread
- Saved evidence bundles and reusable verification sets built from the new supplemental evidence cards
- Scheduled live canary suites with alerting and explicit request-budget controls
- Promotion of failing live or hybrid cases into deterministic fixture regressions
- Cross-run evidence-coverage and weak-evidence summaries for operator review

## Context

This repo is a layered brownfield monorepo with a deterministic EDGAR analysis core in `src/`, an orchestration and MCP layer in `edgar_project/`, a persistence and API shell in `backend/`, and a Next.js frontend in `frontend/`. The existing system already proves value by producing SEC-based analysis artifacts, exposing traceable runs, and supporting authenticated project/run workflows, but the codebase map showed that several core platform assumptions still depended on shared filesystem paths, cwd mutation, and large multi-responsibility modules before the v1.0 hardening effort.

The highest-value work in v1.0 was operational rather than feature-based, and all five trust-boundary phases are now complete. Run outputs are isolated, worker attempts are lease-safe and auditable, insecure auth and ops defaults are removed, pull-request CI exercises the documented stack and key user flows, and storage or retention behavior now scales more honestly under sustained usage. The project has therefore shipped a v1.0 hardening baseline for an already-valuable system. The v1.1 milestone then added explicit live-validation policy boundaries, a remote object-store contract, a summary-first large-trace experience, a first-class persisted evaluation control plane, canonical child-run execution for live or hybrid validation, truthful evaluation dependency observability on the existing ops surfaces, and the final Phase 11 bookkeeping cleanup that restored clean archival traceability.

The `v1.2` milestone came directly from local product testing after the `v1.1` ship. The original answer-reading flow pushed users onto a dense standalone run page with repeated evidence chips and buried caveats, even when the natural place to read the result was the workspace chat that launched the run. Phase 12 repaired the documented runtime and onboarding seams, Phase 13 removed the dead-end intent failures by broadening deterministic analyst-language routing and surfacing rewrite guidance inline in chat, Phase 14 moved the compact answer itself into chat with persisted history and stable run linkage, Phase 15 added inline findings, confidence/caveats, compact evidence navigation, and exact-jump verification links, and Phase 16 reduced the standalone run page to a secondary inspection surface.

`v1.3` follows directly from the first live iteration on the new chat-first answer surface. Phase 17 replaced the old summary-first card contract with a backend-authored narrative answer and a centered narrative renderer, Phase 18 moved evidence strength into a compact header pill backed by a grouped confidence explainer, Phase 19 pushed supporting proof into a collapsed supplemental disclosure with slim exact-jump evidence rows and a quiet secondary pill strip, Phase 20 added deterministic inline charts rendered directly inside the answer column from backend-authored chart previews, and Phase 21 finished the stack with calmer editorial spacing, responsive answer-shell cleanup, and final chat-versus-trace wording alignment.

`v1.4` built directly on that shipped answer stack and completed the information-architecture pass. The visible product now behaves like chat with history and lightweight scope, while the backend `project/run/artifact` model remains intact underneath for persistence and traceability.

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
| Keep prompt routing deterministic-first and expose unsupported guidance before run creation | Analyst trust depends on predictable routing behavior and actionable chat guidance rather than opaque fallback behavior | ✓ Good |
| Treat the chat reply as the primary analytical product and move evidence into a clearly secondary disclosure | The current centered answer still reads like a summary card; analysts need a substantive narrative first and supporting proof second | ✓ Good |
| Render inline charts only from deterministic, backend-safe chart specs derived from trusted run data | Visuals should strengthen trust, not introduce frontend-side inference or chart hallucination risk | ✓ Good |
| Keep the backend project and run model while demoting workspace language in the visible product | Persistence, ownership, and traceability still depend on the existing model, but the user-facing experience should feel like chat with history | ✓ Good |

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
*Last updated: 2026-04-25 after shipping v1.4 Conversation-First Information Architecture*
