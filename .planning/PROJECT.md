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

### Active

- [ ] Add storage and retention controls so artifact ingestion, payload growth, and operational history scale without corrupting trust

### Out of Scope

- New anomaly-detection models or analytical feature work — reliability and product trust are the current bottlenecks, not model breadth
- Mobile or native clients — the existing web, CLI, and MCP surfaces are sufficient until the platform core is production-safe
- Multi-region or managed-cloud deployment work — the current target remains the documented self-hosted stack until isolation and ops basics are solid

## Context

This repo is a layered brownfield monorepo with a deterministic EDGAR analysis core in `src/`, an orchestration and MCP layer in `edgar_project/`, a persistence and API shell in `backend/`, and a Next.js frontend in `frontend/`. The existing system already proves value by producing SEC-based analysis artifacts, exposing traceable runs, and supporting authenticated project/run workflows, but the codebase map shows that several core platform assumptions still depend on shared filesystem paths, cwd mutation, and large multi-responsibility modules.

The highest-value current concerns are operational rather than feature-based. The first four trust-boundary phases are now complete: run outputs are isolated, worker attempts are lease-safe and auditable, insecure auth/ops defaults have been removed, and pull-request CI now exercises the documented stack, seeded browser workflows, and focused Postgres regressions. The next major gap is storage and retention behavior under sustained usage. The active project therefore remains a production-hardening milestone for an already-valuable system, not a greenfield build.

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
| Treat this as a brownfield hardening project, not a new-feature milestone | The current platform already delivers EDGAR analyses; trust, concurrency, and operability are the blockers to wider use | — Pending |
| Preserve the deterministic `src/` analysis core and harden the boundaries around it | Rewriting the numerical path would increase risk and distract from the isolation and reliability problems that matter now | — Pending |
| Prioritize run-scoped artifact contracts before other platform improvements | Shared global artifact paths create the largest correctness risk for concurrent or repeated execution | — Pending |
| Expand verification around the documented self-hosted stack instead of relying on narrow happy-path tests | The repo already documents API, worker, frontend, and Postgres workflows that are not fully gated today | — Pending |
| Track project planning artifacts in git | The hardening work touches architecture, security, and operations decisions that should remain auditable alongside code changes | — Pending |

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
*Last updated: 2026-04-17 after Phase 4 completion*
