# Project Research Summary

**Project:** Agentic Data Science System
**Domain:** Brownfield EDGAR analysis platform hardening for live validation, remote artifact storage, and large-trace inspectability
**Researched:** 2026-04-18
**Confidence:** HIGH

## Executive Summary

Agentic Data Science System v1.1 is not a greenfield "agent platform" build. It is a brownfield evidence product where trust comes from deterministic EDGAR computation, persisted run records, auditable artifacts, and operator-facing traceability. The research is consistent on the core approach: keep the existing Python + FastAPI + SQLAlchemy + Next.js + Postgres architecture, and add explicit seams where the current product would otherwise blur new semantics into existing surfaces. Experts solve this by introducing first-class validation modes, a backend-agnostic object-store contract, and summary-first trace read models instead of rewriting the stack.

For milestone scope, the table-stakes decision set is clear. v1.1 should ship: first-class `live` and `hybrid` validation workflows with case-level outcomes and degradation taxonomy; an S3-compatible remote object-store backend behind the current artifact contract; and a large-trace experience that loads typed summaries first and raw payloads only on demand. The integration order should be boundary-first: define validation identity and isolation rules, harden artifact storage semantics, decompose trace APIs, then add the supported evaluation control plane and finally connect live SEC execution. This keeps the existing run pipeline intact while preventing the new milestone from leaking into user runs, CI expectations, or monolithic trace payloads.

The biggest risks are semantic bleed and false confidence. If live SEC checks are treated like deterministic regression tests, if remote storage is treated like a filesystem transaction, or if large traces are "fixed" only in the frontend while APIs still over-fetch, the product will look done while becoming less trustworthy. Mitigation is straightforward but non-optional: separate validation modes and retention rules, preserve checksums and reconciliation across DB/object storage, keep raw payload access explicit and limited, and instrument the real download/trace paths rather than relying on green health endpoints alone.

## Key Findings

### Recommended Stack

See [STACK.md](./STACK.md). The recommended stack delta is intentionally small: add one S3-compatible storage client, one SEC rate-limit helper, and two frontend libraries for large trace rendering. Do not add a new queue, cache, async storage client, frontend state-management layer, or alternate API architecture for this milestone.

The repo already has the right seams. The milestone should use `boto3` for remote artifact storage, keep the existing synchronous `requests` SEC client with explicit retry/rate-limit policy, and fix large-trace performance with smaller endpoints plus virtualization rather than serializer swaps or full client-side rearchitecture.

**Core technologies:**
- `boto3==1.42.91`: remote S3-compatible artifact storage backend — preserves the current object-store contract while staying compatible with AWS S3, Cloudflare R2, and MinIO-style endpoints.
- `requests>=2.33.1,<2.34` plus `pyrate-limiter==4.1.0`: live SEC access with explicit fair-access controls — keeps the current fetch path and adds the missing request-budget boundary instead of rewriting around a new HTTP client.
- `@tanstack/react-virtual@^3.13.12`: large trace list virtualization — fits the existing custom trace UI without introducing a heavy grid framework or new client-state model.
- `react-json-view-lite@^2.5.0`: collapsible raw JSON inspection — replaces oversized `<pre>` dumps with an inspectable, read-only tree for debug-only payload access.
- `moto[s3]==5.1.22`: backend contract testing for remote storage — gives local and CI coverage for the new storage backend without requiring cloud credentials.

### Expected Features

See [FEATURES.md](./FEATURES.md). The milestone is credible only if it treats validation, storage, and traceability as supported product workflows rather than ad hoc scripts or hidden operator knowledge. Users will expect first-class validation entrypoints, trustworthy artifact handling, and a trace UI that still works when payloads get large.

**Must have (table stakes):**
- Explicit `live` and `hybrid` evaluation runs — users need supported entrypoints, not skipped modes or one-off scripts.
- Curated live SEC canary cases with hybrid failure taxonomy — live validation must distinguish upstream lag, throttling, and product regressions instead of flattening everything into pass/fail.
- Remote object-store backend behind the current artifact contract — artifact IDs, routes, checksums, and retention semantics must stay stable even when blob storage moves off shared disk.
- Summary-first large trace page with on-demand drill-down — traceability must remain inspectable without loading every payload blob on first render.
- Server-side search, filter, and jump navigation for large runs — large traces need fast narrowing tools, not just more scrolling.

**Should have (competitive):**
- Scheduled canary live validations with alerting — useful once manual/operator-invoked live validation is trusted and request budgets are understood.
- Failure-to-fixture promotion loop — turns real live regressions into durable deterministic coverage.
- Brokered short-lived signed URL downloads for very large artifacts — improves throughput once remote object storage is stable.
- Evidence-coverage and weak-evidence summaries — helps operators judge trust before opening raw payloads.

**Defer (v2+):**
- Automatic quarantine/replay workflows for production validation failures.
- Multi-cloud or tiered storage orchestration beyond the first S3-compatible backend.
- Real-time trace streaming, collaborative review, or cross-run observability search as a broader platform surface.

**Anti-features to reject in requirements:**
- Running the full live suite on every PR, deploy, or user-triggered run.
- Exact snapshot or golden assertions against live SEC outputs.
- Exposing bucket names, object keys, or long-lived object URLs in the UI or API.
- Loading complete run, step, and model payload JSON by default in trace views.

### Architecture Approach

See [ARCHITECTURE.md](./ARCHITECTURE.md). The architecture research recommends additive product seams, not a platform rewrite. Live and hybrid validation should run through the same persisted `AnalysisRun` pipeline already used by operators, but only behind a new evaluation control plane with case-level result records. Remote storage should stay behind the existing artifact abstraction, and large-trace performance should be solved with read-model projection plus section-based APIs and lazy UI loading.

**Major components:**
1. `EvaluationExecutionService` + evaluation routes/models — own suite lifecycle, case fan-out, case-result persistence, and links to child analysis runs.
2. `S3ObjectStore` + storage registry/resolver — select write/read backends by configuration and `storage_uri` scheme while preserving the existing artifact contract.
3. `TraceProjectionService` + trace summary/section DTOs — build small run summaries and demand-loaded section payloads instead of serving monolithic trace blobs.
4. Existing `EdgarPipelineExecutionService` and worker path — remain the execution engine for live/hybrid child runs, preserving audit trails and retry semantics.

### Critical Pitfalls

See [PITFALLS.md](./PITFALLS.md). The highest-risk failures are not generic bugs; they are trust-boundary mistakes that make the system appear complete while weakening auditability and operator clarity.

1. **Treating live SEC validation as deterministic regression testing** — split fixture, hybrid, and live modes; persist observation time, freshness window, and drift policy; keep live mode out of merge-blocking CI by default.
2. **Letting evaluation traffic pollute normal product runs** — isolate validation identity, retention, prefixes, metrics, and UI visibility so benchmark traffic cannot be mistaken for user work.
3. **Treating remote object storage like a filesystem or an ACID database extension** — lock the interface to object operations, persist explicit checksums, and add reconciliation for DB/object-store divergence.
4. **Trying to fix large traces only in the frontend** — change the API contract first with summary/section endpoints, pagination, and explicit debug payload fetches.
5. **Keeping ever-larger trace blobs on hot run rows and proxying all heavy traffic blindly** — move toward compact run summaries, track payload budgets, and instrument end-to-end download/trace latency before scale rollout.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Validation Boundaries and Policy
**Rationale:** This must come first because v1.1 fails at the requirements level if validation traffic, live semantics, and retention policy are not distinct from ordinary user runs.
**Delivers:** `validation_mode` semantics, observed-at/freshness metadata, drift policy, separate listing/visibility rules, and clear rules for fixture vs hybrid vs live execution.
**Addresses:** Explicit live/hybrid entrypoints, hybrid verdict taxonomy, evaluation isolation, anti-feature rejection around live CI gating.
**Avoids:** Treating live validation as deterministic regression, polluting normal runs, and misclassifying SEC lag/throttling as product failure.

### Phase 2: Remote Object Store Contract
**Rationale:** Artifact semantics must be stable before live validation and larger retained traces create more remote-storage pressure.
**Delivers:** `S3ObjectStore`, scheme-aware storage registry/resolver, checksum-preserving writes, artifact health reporting, backend-agnostic contract tests, and reconciliation/tombstone rules.
**Uses:** `boto3`, `moto[s3]`.
**Implements:** Storage registry, artifact service integration, artifact route delivery choices, and truthful storage readiness checks.
**Avoids:** Filesystem-shaped assumptions, false atomicity between Postgres and object storage, and incorrect integrity/delete assumptions in S3-style backends.

### Phase 3: Large-Trace API Decomposition
**Rationale:** Large-payload trace usability is already a constraint, and live validation will amplify it if the product keeps full-payload defaults.
**Delivers:** Trace summary and section endpoints, raw debug payload endpoints kept separate, pagination/windowing, field deferral for heavy JSON columns, virtualized trace sections, and collapsible raw JSON inspection.
**Uses:** `@tanstack/react-virtual`, `react-json-view-lite`.
**Implements:** `TraceProjectionService`, runs trace DTOs/routes, and lazy section loading in the Next.js trace surface.
**Avoids:** Frontend-only performance fixes, oversized JSON responses, hot-row JSON bloat, and opaque trace UX at larger scale.

### Phase 4: Evaluation Control Plane
**Rationale:** After validation semantics, storage, and trace read models are in place, the product can safely expose a supported evaluation workflow rather than CLI-only research plumbing.
**Delivers:** `evaluation_case_results`, `EvaluationExecutionService`, evaluation APIs, fixture execution through the new control plane, and operator-facing suite/case history surfaces.
**Addresses:** First-class validation workflows, curated canary case management, durable per-case outcomes, and inspectable result lineage.
**Avoids:** Blob-only `results_json` persistence, hidden validation workflows, and unsupported case retries or filtering.

### Phase 5: Live/Hybrid Canary Execution and Operational Hardening
**Rationale:** Real SEC traffic should be connected last, once the product already has mode boundaries, storage discipline, and trace scaling in place.
**Delivers:** Child `AnalysisRun` linkage for live/hybrid cases, centralized SEC access policy, degraded-state classification, optional scheduled canaries, end-to-end smoke checks, and delivery/path observability.
**Uses:** Existing `requests` path plus `pyrate-limiter`.
**Implements:** Evaluation-to-run delegation, worker reuse, fairness budgets, and alerting around SEC throttling, storage degradation, and large artifact/trace delivery.
**Avoids:** Flaky live CI, concurrency-driven SEC denial, and scale failures hidden behind green health checks.

### Phase Ordering Rationale

- Phase 1 is first because it defines product truth: what counts as validation, how it is judged, and how it is isolated from user work.
- Phase 2 and Phase 3 harden the two existing seams most likely to break under v1.1 load: artifact storage and trace retrieval.
- Phase 4 builds supported workflow only after the core storage and trace contracts are safe to expose.
- Phase 5 introduces real upstream variability last so live SEC integration lands as an additive adapter, not a cross-cutting rewrite.
- This ordering also rejects the main anti-features: it prevents live CI gating, avoids bucket-coupled APIs, and removes full-payload trace hydration before scale traffic arrives.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** If the deployment target is Cloudflare R2 or MinIO rather than plain AWS S3, validate versioning, delete, checksum, and presign behavior before locking requirements.
- **Phase 5:** SEC live-validation policy needs phase-level confirmation for request budgets, worker concurrency, freshness windows, and whether scheduled canaries are in scope for v1.1 or deferred to v1.x.
- **Phase 5:** If large artifact delivery must bypass the API in v1.1, research the exact proxy vs presigned threshold and audit requirements before planning implementation.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Baseline S3-compatible object-store adapter and contract testing are well-documented if the target is standard S3 semantics.
- **Phase 3:** Summary-first APIs, lazy section loading, pagination, virtualization, and JSON tree inspection follow established FastAPI + Next.js + React patterns.
- **Phase 4:** Basic evaluation CRUD/control-plane work is mostly internal architecture and schema extension once mode boundaries are decided.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Recommended libraries are narrow, additive, and validated against official docs; no disruptive stack rewrite is required. |
| Features | MEDIUM | Table stakes are clear, but final validation workflow scope and operator UX are partly inferred from adjacent products and need milestone scoping decisions. |
| Architecture | HIGH | The recommended seams map cleanly onto the existing codebase and preserve current run, artifact, and worker surfaces. |
| Pitfalls | HIGH | Risks are strongly grounded in the current repo shape plus official SEC, S3, PostgreSQL, and Next.js behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **Validation surface scope:** Decide whether v1.1 includes only CLI/API-backed evaluation workflows or also ships the validation dashboard UI in the same milestone.
- **Remote storage target:** Choose AWS S3 vs R2 vs MinIO-style deployment before finalizing health checks, delete semantics, presign support, and integration tests.
- **Evaluation namespace policy:** Decide whether validation runs live in dedicated system projects/namespaces or share projects with stronger filtering and labeling.
- **Large-download delivery model:** Decide whether proxy-only delivery is acceptable for v1.1 or whether short-lived signed URLs are required for artifacts above a defined size threshold.
- **Trace raw-payload retention budget:** Define where oversized raw payloads should live long term: capped DB child records, object storage, or both.
- **Debug access policy:** Decide which roles can access raw run/step/model payloads once summary-first trace views become the default.

## Sources

### Primary (HIGH confidence)
- Internal research: [STACK.md](./STACK.md), [FEATURES.md](./FEATURES.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [PITFALLS.md](./PITFALLS.md)
- Internal codebase seams referenced across the research: `backend/storage/*`, `backend/services/artifact_service.py`, `backend/api/routes/runs.py`, `backend/models/evaluation_run.py`, `edgar_project/evaluation/runner.py`, `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`
- SEC developer resources and EDGAR API docs — fair-access guidance, user-agent expectations, live-data behavior, and API surfaces
- AWS S3 and Boto3 docs — upload/download/head behavior, integrity, presigned URLs, versioning, and Object Lock implications
- Next.js App Router docs — route handlers, loading/streaming, and self-hosting behavior for sectioned trace pages
- FastAPI response docs — confirmation that serializer swaps are not the right primary fix for trace scaling

### Secondary (MEDIUM confidence)
- LangSmith evaluation docs — offline/live evaluation pattern language and feedback-loop ideas
- Dagster reliability docs — freshness/drift framing for operator-facing validation workflows
- Langfuse v4 architecture notes — selective retrieval and large-trace UX patterns
- MUI X server-side lazy-loading guidance — large-list pagination/windowing patterns

### Tertiary (LOW confidence)
- None. Remaining uncertainty is mostly product-scope choice, not unsupported technical claims.

---
*Research completed: 2026-04-18*
*Ready for roadmap: yes*
