# Phase 10: Live/Hybrid Execution Hardening - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Link live and hybrid evaluation cases to the canonical `AnalysisRun` infrastructure so execution, worker attempts, artifacts, and traceability all flow through the same persisted run model the product already uses, while surfacing upstream SEC or remote-storage degradation truthfully through the existing ops surfaces.

This phase covers launch mode for live or hybrid evaluation execution, child-run linkage shape, how evaluation case outcomes are derived from linked canonical runs, and how evaluation-specific degradation is reported through `/health`, `/v1/worker/health`, and `/metrics`.

It does not broaden live validation into default user workflows, change the project-scoped evaluation ownership model, add a new evaluation UI surface, or replace application-owned artifact delivery with storage-native access.

</domain>

<decisions>
## Implementation Decisions

### Evaluation launch mode
- **D-01:** Starting a live or hybrid evaluation should enqueue child analysis runs and return immediately rather than executing inline inside the evaluation control-plane request.
- **D-02:** Live and hybrid evaluation execution must reuse the existing queue, worker, and canonical run lifecycle instead of introducing a separate parallel execution path.

### Child-run linkage shape
- **D-03:** Each live or hybrid evaluation case should link to one canonical child `AnalysisRun` per execution attempt.
- **D-04:** Each case should expose a direct link to the latest child run plus bounded prior child-run history rather than a single opaque execution-log reference.

### Case outcome mapping
- **D-05:** Evaluation case verdicts should be derived from linked child `AnalysisRun` terminal status plus the existing validation degradation taxonomy.
- **D-06:** This phase should not invent a second runtime lifecycle alongside `AnalysisRunStatus`; canonical run state remains the source of truth for execution progress and terminal disposition.

### Ops truthfulness surface
- **D-07:** Existing ops surfaces (`/health`, `/v1/worker/health`, and `/metrics`) must expose explicit evaluation/live-validation dependency degradation instead of burying it only inside case messages or result blobs.
- **D-08:** SEC upstream and remote-storage failures encountered by live or hybrid evaluation flows must appear as truthful degraded signals rather than false-green idle or healthy state.

### the agent's Discretion
- Exact schema fields for child-run links, bounded child-run history, and evaluation-case execution metadata
- Exact API or wire shape for linking from a case result to its latest or prior child runs
- Exact metrics and health-field names for evaluation-specific degraded state, as long as they remain explicit and operator-truthful
- Exact queueing mechanics for child-run fan-out, as long as they preserve the canonical worker and run lifecycle

</decisions>

<specifics>
## Specific Ideas

- User accepted all recommended defaults in one step:
  - live or hybrid evaluation starts should enqueue child runs and return immediately
  - each case should link directly to canonical child analysis runs, not opaque execution logs
  - case verdicts should be derived from linked run outcomes rather than a separate lifecycle
  - ops surfaces should explicitly show evaluation-specific SEC or storage degradation
- The desired outcome is operational consistency more than new UX: live and hybrid validation should feel like a thin evaluation layer over the existing run system, not a separate executor.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — current milestone intent and the remaining v1.1 scope after Phase 9
- `.planning/ROADMAP.md` — Phase 10 goal, dependencies, and success criteria
- `.planning/REQUIREMENTS.md` — `EVAL-02` and `OPS-01` define the acceptance criteria for this phase
- `.planning/STATE.md` — current project position after Phase 9 completion

### Prior phase constraints
- `.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md` — live and hybrid evaluation remain explicit operator-invoked and non-default, with degradation taxonomy already locked
- `.planning/phases/05-storage-and-ops/05-CONTEXT.md` — degraded-state reporting must stay explicit and truthful in health and metrics surfaces
- `.planning/phases/09-evaluation-control-plane/09-CONTEXT.md` — evaluation workflows are API-backed first, suite IDs are curated, and evaluation ownership stays project-scoped
- `.planning/phases/09-evaluation-control-plane/09-VERIFICATION.md` — verified Phase 9 boundaries and the existing supported evaluation surface this phase must build on

### Existing canonical run infrastructure
- `backend/models/analysis_run.py` — canonical persisted run aggregate and terminal statuses
- `backend/api/routes/runs.py` — current run create/list/detail and trace-summary product surfaces
- `backend/services/run_lifecycle_service.py` — canonical queued/running/retry/cancel transitions
- `backend/worker/loop.py` — worker execution path and claim/finalize behavior for queued runs
- `backend/services/edgar_pipeline_execution_service.py` — actual canonical run execution path, artifact ingest, and error-summary behavior

### Existing evaluation and ops seams
- `backend/models/evaluation_run.py` — supported evaluation aggregate
- `backend/models/evaluation_case_result.py` — persisted per-case results that need child-run linkage
- `backend/api/routes/evaluations.py` — existing evaluation create/start/review surface
- `backend/services/evaluation_control_plane_service.py` — current direct-run evaluation execution path that Phase 10 must harden
- `edgar_project/evaluation/runner.py` — current live/hybrid skip semantics and degradation metadata
- `backend/api/routes/health.py` — current readiness, health, and worker-health surfaces
- `backend/observability/metrics.py` — current Prometheus surfaces and queue truthfulness behavior
- `backend/observability/worker_queue.py` — current DB-backed worker observability contract
- `backend/auth/resource_access.py` — owner-scoped access logic that should still govern child-run-linked evaluation artifacts and run access

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/run_lifecycle_service.py` and `backend/worker/loop.py` already provide the canonical queued background execution contract this phase should reuse.
- `backend/api/routes/runs.py` and `backend/models/analysis_run.py` already provide the audit trail, trace-summary, and terminal-status surfaces that live or hybrid evaluation cases should link into.
- `backend/services/evaluation_control_plane_service.py` already persists supported evaluation runs and per-case records, so Phase 10 can extend that control plane rather than replace it.
- `backend/api/routes/health.py`, `backend/observability/metrics.py`, and `backend/observability/worker_queue.py` already implement truthful degraded-state ops reporting patterns that can be extended to evaluation-specific dependency state.

### Established Patterns
- Evaluation is already API-backed, project-scoped, and suite-id-driven after Phase 9; this phase should preserve those boundaries while changing execution plumbing.
- Live and hybrid semantics are already policy-gated and non-default after Phase 6, so child-run linkage must not weaken those guardrails.
- The product already treats `AnalysisRun` as the canonical execution record for artifacts, traceability, queueing, and retries; this phase should route evaluation execution into that model instead of shadowing it.
- Health and metrics surfaces already distinguish degraded dependency state from "no work queued" for DB-backed worker observability, so evaluation-specific dependency degradation should follow the same truthfulness pattern.

### Integration Points
- Child-run linkage will need to connect `EvaluationCaseResult` records to canonical `AnalysisRun` rows without breaking existing project-owner access checks.
- Live or hybrid evaluation start behavior will need to fan out into the existing run queue and worker path rather than continuing to execute entirely inside `EvaluationControlPlaneService`.
- Evaluation-specific degraded-state signals will need to plug into `backend/api/routes/health.py` and `backend/observability/metrics.py` without regressing existing queue and DB observability semantics.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-live-hybrid-execution-hardening*
*Context gathered: 2026-04-18*
