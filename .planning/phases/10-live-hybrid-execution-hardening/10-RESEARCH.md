# Phase 10: Live/Hybrid Execution Hardening - Research

**Researched:** 2026-04-18
**Domain:** Queue-backed live and hybrid evaluation execution through canonical child analysis runs with truthful dependency observability
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Starting a live or hybrid evaluation should enqueue child analysis runs and return immediately rather than executing inline inside the evaluation control-plane request.
- **D-02:** Live and hybrid evaluation execution must reuse the existing queue, worker, and canonical run lifecycle instead of introducing a separate parallel execution path.
- **D-03:** Each live or hybrid evaluation case should link to one canonical child `AnalysisRun` per execution attempt.
- **D-04:** Each case should expose a direct link to the latest child run plus bounded prior child-run history rather than a single opaque execution-log reference.
- **D-05:** Evaluation case verdicts should be derived from linked child `AnalysisRun` terminal status plus the existing validation degradation taxonomy.
- **D-06:** Phase 10 must not invent a second runtime lifecycle alongside `AnalysisRunStatus`; canonical run state remains the execution source of truth.
- **D-07:** Existing ops surfaces (`/health`, `/v1/worker/health`, and `/metrics`) must expose explicit evaluation/live-validation dependency degradation instead of burying it only inside case messages or result blobs.
- **D-08:** SEC upstream and remote-storage failures encountered by live or hybrid evaluation flows must appear as truthful degraded signals rather than false-green idle or healthy state.

### the agent's Discretion
- Exact persistence shape for latest child-run pointers and bounded prior child-run history on case rows
- Exact child-run metadata contract used to tie `AnalysisRun` rows back to evaluation runs and case IDs
- Exact reconciliation strategy for deriving case and evaluation aggregate verdicts from linked child runs
- Exact health and Prometheus field names for evaluation-specific SEC or storage degradation

### Deferred Ideas (OUT OF SCOPE)
- New evaluation UI surfaces beyond the existing control-plane API and run links
- A separate evaluation worker or executor path
- Default-user live validation workflows, merge-blocking live suites, or global operator-only evaluation ownership
- Storage-native direct artifact access or multi-cloud observability expansion
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-02 | Live and hybrid validation cases execute through linked child analysis runs so existing run audit trails, workers, and artifacts remain canonical | Use `AnalysisRun`, `RunQueueService`, and the worker loop as the execution engine for live/hybrid cases, then persist latest child-run pointers and bounded prior run history on evaluation case rows. |
| OPS-01 | Health and metrics surfaces report SEC upstream or remote-storage degradation truthfully for supported validation and artifact flows | Extend existing health and Prometheus observability helpers with evaluation-specific dependency degradation instead of masking those failures inside case messages or summary blobs. |
</phase_requirements>

## Summary

Phase 09 deliberately stopped short of canonical run execution. `backend/services/evaluation_control_plane_service.py` still runs supported suites inline with `EvaluationRunner`, and `edgar_project/evaluation/runner.py` still treats `live` and `hybrid` as skipped placeholders. That means the supported control plane exists, but the two modes that actually need production hardening still bypass the canonical `AnalysisRun` plus worker model the rest of the product relies on.

The repo already has the exact pieces needed to close that gap without adding a second executor. `backend/api/routes/runs.py`, `backend/services/analysis_run_service.py`, `backend/services/run_queue_service.py`, `backend/services/run_lifecycle_service.py`, `backend/worker/loop.py`, and `backend/services/edgar_pipeline_execution_service.py` together already define the canonical queued execution path, run audit trail, artifact ingest path, and retry semantics. Phase 10 should use those seams directly. The evaluation control plane becomes a thin scheduler for live and hybrid cases: create child `AnalysisRun` rows, enqueue them, persist the run links on each case result, and derive evaluation verdicts from the linked run state instead of from an inline runner loop.

The lowest-risk linkage contract is additive on top of `EvaluationCaseResult`. That table already stores one persisted row per case. Extending it with a nullable `latest_analysis_run_id`, a cached `latest_analysis_run_status`, and bounded `analysis_run_history_json` gives the API a direct run pointer plus prior child-run context without needing a brand-new evaluation-history aggregate. The child `AnalysisRun` itself should carry evaluation metadata in `meta_json` so the existing run surfaces remain inspectable and attributable: `evaluation_run_id`, `evaluation_case_id`, `evaluation_input_mode`, and the originating suite ID. Because `AnalysisRun` already tracks worker attempts in `execution_jobs`, Phase 10 does not need a second per-attempt lifecycle on the evaluation side; `EvaluationStatus.pending` is sufficient while the latest child run is non-terminal, and terminal case verdicts can be reconciled from the final run status plus the Phase 06 degradation taxonomy.

The main new logic therefore belongs in reconciliation, not orchestration. When a linked child run is `pending`, `queued`, or `running`, the evaluation case stays `pending`. When the run reaches a terminal state, the control plane should update the case row by deriving: the evaluation status (`passed`, `failed`, `error`, or `skipped`), the degradation class (`none`, `product_regression`, `upstream_sec_degraded`, `stale_source`, or `policy_skipped`), and a refreshed summary message. Phase 06 already gave the repo the classification rules in `EvaluationRunner._classify_degradation_class`; the Phase 10 move is to feed that taxonomy from child-run evidence instead of from inline placeholder results. That likely means persisting or deriving two specific signals from canonical runs: upstream SEC error codes and freshness observation data for live or hybrid sources.

For ops truthfulness, the repo already has the right pattern in `backend/api/routes/health.py`, `backend/schemas/health.py`, `backend/observability/worker_queue.py`, and `backend/observability/metrics.py`: dependency reads may fail, and when they do the surfaces must return degraded state or `NaN` gauges instead of pretending the world is empty. Phase 10 should extend that pattern with one DB-backed evaluation dependency view. That helper should look at recent linked evaluation case results and their child runs, detect SEC-related or storage-related degradation, and feed explicit status into `/health`, `/v1/worker/health`, and Prometheus. The product already has app-owned artifact delivery and remote-storage reconciliation semantics from Phase 07, so the new observability should reuse those signals rather than invent a storage-specific health path.

**Primary recommendation:** keep Phase 10 to three additive slices. First, add child-run linkage fields and a run-enqueue builder for live and hybrid cases. Second, convert live/hybrid evaluation starts into queued child-run launches with read-time or service-driven reconciliation of case and evaluation aggregate state. Third, extend health and metrics with evaluation dependency degradation signals plus focused regressions. That satisfies the phase goal while preserving the repo’s brownfield contracts: one canonical run model, one worker system, one artifact path, and explicit operator truthfulness.

Repo note: `AGENTS.md` was applied. No repository-local `.claude/skills/` or `.agents/skills/` directory exists under the project root.

## Standard Stack

### Core

| Library / Seam | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `AnalysisRun` + queue/worker services in `backend/services/` | in-repo seam | Canonical queued execution for live and hybrid evaluation cases | The run system already owns retries, artifacts, traces, and audit history. |
| Evaluation control-plane API and persistence in `backend/api/routes/evaluations.py` and `backend/models/evaluation_case_result.py` | in-repo seam | Persist case-level child-run linkage and expose run navigation | Phase 09 already made evaluation runs and case results first-class resources. |
| Health/metrics stack in `backend/api/routes/health.py`, `backend/schemas/health.py`, and `backend/observability/metrics.py` | in-repo seam | Report evaluation-specific SEC or storage degradation truthfully | These surfaces already model degraded dependency reads instead of false-green emptiness. |
| Evaluation policy/degradation contracts in `edgar_project/evaluation/schemas.py` and `edgar_project/evaluation/runner.py` | in-repo seam | Reuse the existing `EvaluationStatus`, `ValidationDegradationClass`, and observation semantics | Phase 10 should extend the current taxonomy, not fork it. |
| `pytest 8.4.2` via `pytest.ini` | local repo tooling | API, service, and observability regression coverage | Existing backend phases already verify new contracts through focused pytest slices. |

### Supporting

| Library / Seam | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `backend/services/analysis_run_service.py` | in-repo seam | Create child analysis runs with evaluation metadata and ownership inherited from the project | Use when enqueueing live or hybrid cases into the canonical run table. |
| `backend/services/run_queue_service.py` | in-repo seam | Queue new child runs without bypassing existing worker semantics | Use for Phase 10 launches instead of inline execution. |
| `backend/services/edgar_pipeline_execution_service.py` | in-repo seam | Produce run outputs, artifacts, and error summaries that evaluation reconciliation can inspect | Use as-is through the worker path rather than duplicating execution logic. |
| `backend/api/access_checks.py` and `backend/auth/resource_access.py` | in-repo seam | Preserve owner/project-scoped access to linked runs and artifacts | Use so evaluation case → run navigation stays within existing auth boundaries. |
| Phase 07 storage and retention signals | in-repo seam | Surface storage degradation and artifact delivery truthfully | Use when child runs fail on remote artifact access or retention-visible states. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Canonical `AnalysisRun` child execution | Keep inline live/hybrid work inside `EvaluationControlPlaneService` | Simpler in one file, but it violates the phase goal and duplicates worker/run behavior. |
| Case-row latest pointer + bounded history | Separate evaluation-child-run table plus a second lifecycle aggregate | More normalized, but wider than Phase 10 needs and slower to integrate into existing APIs. |
| Reconciliation from canonical run states | A second evaluation-specific runtime lifecycle | Easier to tailor to evaluation wording, but it directly violates the locked decision against parallel lifecycles. |
| DB-backed evaluation dependency helper | Hard-code `/health` and `/metrics` from recent summary blobs | Cheap, but not truthful enough for live SEC and remote-storage degradation. |
| Read-time or service-triggered refresh of linked case rows | A new event bus or dedicated evaluation worker | More reactive, but a larger architectural jump than the repo needs for this phase. |

## Architecture Patterns

### Pattern 1: Live/Hybrid Evaluation as a Thin Scheduler Over `AnalysisRun`

**What:** When a supported evaluation suite contains `live` or `hybrid` cases, the control plane creates canonical child `AnalysisRun` rows, enqueues them, and returns immediately.

**When to use:** `POST /v1/evaluations/{id}/start` for live or hybrid cases.

**Why:** The canonical run model already owns queueing, retries, artifacts, traceability, and run audit surfaces. Phase 10 should schedule into that model instead of extending the inline evaluation runner path.

**Recommended behavior:**
- Keep fixture and `orchestration_mocked` flows on the Phase 09 synchronous service path.
- For each live or hybrid case, create one child `AnalysisRun` with `project_id` and `initiated_by_user_id` inherited from the parent evaluation run.
- Set `meta_json["evaluation_case_link"]` on the child run with `evaluation_run_id`, `case_id`, `suite_id`, and `input_mode`.
- Queue the child run through `RunQueueService.enqueue_after_create(...)`.

### Pattern 2: Case Rows Own the Latest Run Pointer and Bounded Prior History

**What:** Extend `EvaluationCaseResult` with fields that directly point to the latest child run and preserve a compact history of prior child runs.

**When to use:** Every live or hybrid case row persisted by the evaluation control plane.

**Why:** The API needs a direct navigation target to the canonical run audit trail, and the user explicitly rejected opaque execution-log blobs.

**Recommended fields:**
- `latest_analysis_run_id`
- `latest_analysis_run_status`
- `analysis_run_history_json`
- optional cached timestamps such as `latest_analysis_run_finished_at` if the API needs bounded summary fields without additional queries

### Pattern 3: Reconcile Evaluation Verdicts From Child Run Truth

**What:** Update case and aggregate evaluation status by reading linked `AnalysisRun` rows, not by inventing a second executor lifecycle.

**When to use:** On evaluation detail/case reads, or in a service refresh step after child-run launches and terminal transitions.

**Why:** Phase 10 explicitly requires canonical run status to remain the execution source of truth.

**Recommended mapping:**
- `AnalysisRunStatus.pending`, `queued`, `running` -> `EvaluationStatus.pending`
- `AnalysisRunStatus.success` -> `EvaluationStatus.passed` unless freshness or dependency evidence reclassifies to `stale_source` or `upstream_sec_degraded`
- `AnalysisRunStatus.error`, `cancelled` -> `EvaluationStatus.error` or `failed` with degradation classified from upstream/storage evidence
- Degradation classes must reuse the Phase 06 taxonomy rather than introduce new labels

### Pattern 4: Truthful Evaluation Dependency Observability Follows Existing Queue Patterns

**What:** Add one DB-backed evaluation observability helper that reports recent SEC or storage degradation from supported validation flows.

**When to use:** `/health`, `/v1/worker/health`, and `/metrics`.

**Why:** The current health and metrics surfaces already treat failed dependency reads as degraded state. Phase 10 should extend that exact pattern instead of relying on summary blobs or hidden case messages.

**Recommended behavior:**
- Return an explicit evaluation dependency slice on JSON health routes.
- Export Prometheus gauges that show whether evaluation SEC and storage dependencies are currently healthy, degraded, or unknown.
- Preserve `NaN` or null semantics when the DB-backed observability read itself fails.

## Implementation Slices

### Slice A: Child-Run Linkage Foundation

Focus files:
- `alembic/versions/013_live_hybrid_evaluation_case_run_links.py`
- `backend/models/evaluation_case_result.py`
- `backend/schemas/evaluation_case_result.py`
- `backend/schemas/evaluation_run.py`
- `backend/repositories/evaluation_case_result_repository.py`
- `backend/services/evaluation_control_plane_service.py`
- `tests/test_evaluation_live_hybrid_execution.py`
- `tests/test_evaluation_control_plane_api.py`

Deliver:
- latest child-run pointer and bounded prior run history on case rows
- child-run metadata contract for evaluation-linked `AnalysisRun` rows
- service helpers that can enqueue live or hybrid cases into the canonical queue

### Slice B: Queue-Backed Live/Hybrid Launch and Reconciliation

Focus files:
- `backend/services/evaluation_control_plane_service.py`
- `backend/services/run_queue_service.py`
- `backend/api/routes/evaluations.py`
- `backend/schemas/evaluation_case_result.py`
- `backend/schemas/evaluation_run.py`
- `edgar_project/evaluation/runner.py`
- `tests/test_evaluation_live_hybrid_execution.py`
- `tests/test_evaluation_control_plane_api.py`

Deliver:
- `start_evaluation_run(...)` launches live/hybrid child runs and returns with the evaluation aggregate still in a truthful running state
- case rows reconcile from linked child-run status and degradation evidence
- evaluation APIs expose direct case -> run navigation without opaque execution logs

### Slice C: Evaluation Dependency Health and Metrics

Focus files:
- `backend/api/routes/health.py`
- `backend/schemas/health.py`
- `backend/observability/metrics.py`
- `backend/observability/evaluation_validation.py`
- `tests/test_backend_health.py`
- `tests/test_evaluation_live_hybrid_execution.py`
- `README.md`

Deliver:
- JSON health routes expose evaluation-specific SEC or storage degradation explicitly
- Prometheus metrics export evaluation dependency truth instead of false-green idle state
- operator docs and tests explain how live/hybrid evaluation health relates to canonical child runs

## Validation Architecture

Phase 10 needs Wave 0 coverage because there is currently no test seam for child-run linkage or evaluation dependency observability.

**Recommended quick command:**
```bash
python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py tests/test_backend_health.py -q --tb=short
```

**Recommended full command:**
```bash
python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py tests/test_backend_health.py tests/test_evaluation_policy_contract.py tests/test_async_run_queue.py tests/test_worker_job_lifecycle.py -q --tb=short
```

**Required new or extended tests:**
- `tests/test_evaluation_live_hybrid_execution.py`
  - live and hybrid starts enqueue child `AnalysisRun` rows instead of running inline
  - case rows persist `latest_analysis_run_id`, `latest_analysis_run_status`, and bounded history
  - reconciliation maps non-terminal child runs to `EvaluationStatus.pending`
  - terminal child runs update case and aggregate evaluation status from canonical run truth
- `tests/test_evaluation_control_plane_api.py`
  - case responses surface latest child-run links and bounded history
  - evaluation detail and case list refresh linked child-run state before returning
  - operators can move from a case result to the existing run detail or status surfaces without opaque logs
- `tests/test_backend_health.py`
  - `/health` and `/v1/worker/health` expose evaluation dependency degradation explicitly
  - `/metrics` exports evaluation SEC and storage degradation gauges truthfully
  - failed observability reads degrade gracefully instead of pretending no validation activity exists

## Pitfalls and Boundaries

- Do not build a second evaluation execution engine parallel to `AnalysisRun` and the worker loop.
- Do not leave live or hybrid case execution as inline placeholder work inside `EvaluationControlPlaneService`.
- Do not hide child-run history inside one opaque blob with no direct run pointer.
- Do not add a new evaluation lifecycle that conflicts with `AnalysisRunStatus`; use `EvaluationStatus.pending` while child runs are non-terminal.
- Do not mask SEC or remote-storage degradation as empty queue state, empty metrics, or overall healthy JSON.
- Do not widen the phase into a new UI buildout or a separate auth model.

## Recommended Plan Shape

Phase 10 should be planned as **3 sequential plans**:

1. **Plan 01 — Child-run linkage foundation**
   - extend case-result persistence with latest child-run pointer and bounded prior history
   - add service helpers that mint and enqueue linked `AnalysisRun` rows for live or hybrid cases

2. **Plan 02 — Queue-backed launch and canonical verdict reconciliation**
   - convert live/hybrid evaluation starts into child-run launches
   - reconcile case and aggregate evaluation status from linked child runs plus degradation taxonomy

3. **Plan 03 — Evaluation dependency observability**
   - extend `/health`, `/v1/worker/health`, and `/metrics` with evaluation-specific SEC and storage degradation signals
   - harden the new linkage and observability contracts with focused regressions and operator docs
