# Phase 12: Runtime Reliability for Chat Delivery - Research

**Researched:** 2026-04-18
**Domain:** Worker/runtime stability, sync-first chat delivery, truthful degraded-status reporting, and first-run auth/onboarding cleanup for the local stack
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Chat should force synchronous execution as the primary path for this phase instead of keeping worker queueing as an equal default.
- **D-02:** Runtime reliability is more important than preserving the current dual-mode chat affordance; the UI may collapse or hide the queue choice temporarily.
- **D-03:** If a user requests worker queueing while background delivery is degraded or unavailable, the product should automatically fall back to synchronous execution.
- **D-04:** Automatic fallback must still be disclosed in workspace and per-message status surfaces.
- **D-05:** Chat must show a persistent workspace-level background-delivery status near the composer.
- **D-06:** Chat must also show a per-message note whenever the requested background path was unavailable, degraded, or automatically rerouted.
- **D-07:** Phase 12 may include auth and onboarding fixes discovered during live testing if they materially block first-run chat delivery.
- **D-08:** The phase is still bounded to delivery-critical runtime seams, queue truthfulness, and onboarding blockers directly encountered during chat testing.

### the agent's Discretion
- Exact UI treatment for sync-default behavior and hidden/de-emphasized background mode
- Exact implementation of automatic fallback while still preserving truthful status reporting
- Exact technical fix for the worker boot/import failure
- Exact auth/onboarding remediation, so long as it removes the current dead-end flow without broadening into a full auth redesign

### Deferred Ideas (OUT OF SCOPE)
- Chat-native answer rendering and message schema
- Evidence/artifact navigation attached to chat answers
- Broad auth program or team-admin workflows beyond first-run chat blockers
- General deep-dive/run-page redesign
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RUN-01 | User can launch a chat-driven run in the documented Compose stack without run-workspace permission failures | The run-workspace permission fix is already landed in `docker-entrypoint.sh`; Phase 12 should lock it with explicit regression coverage and keep Compose smoke in the validation contract. |
| RUN-02 | User can rely on queued/background execution in the documented Compose stack because the worker starts cleanly and can claim work | The worker currently fails before the loop starts because importing `backend.services.analysis_run_service` executes `backend/services/__init__.py`, which eagerly imports `EdgarPipelineExecutionService`, which reaches `RecordedChatCompletionService`, which re-imports `backend.observability.metrics`. The lowest-risk repair is to remove eager heavy imports from `backend/services/__init__.py` so package import no longer pulls the pipeline/LLM stack into worker-queue observability paths. |
| RUN-03 | User can see truthful chat-visible status when background delivery is degraded or unavailable | Chat should stop pretending the background path is a healthy co-equal mode. The current UI and server action already pass through one place (`frontend/src/components/chat-shell/chat-composer.tsx` and `frontend/src/actions/runs.ts`), so Phase 12 can enforce sync-default behavior, automatic fallback for stale queue requests, and explicit workspace/per-message status using one shared runtime-status contract. |
</phase_requirements>

## Summary

Phase 12 should not create a second execution model. The repo already has the correct runtime architecture: both synchronous and async dispatch reconverge inside `EdgarPipelineExecutionService.execute_analysis_run(...)`. The real problem is that the wrappers around that shared execution core are currently brittle or misleading. The run-workspace permission bug has already been fixed in `docker-entrypoint.sh`, but the worker still cannot boot in the documented Compose stack because the import graph around `backend.services` and `backend.observability.metrics` is too eager. Separately, the chat UI still presents `Execute now` and `Queue for worker` as equivalent options even though the current product and user decision now require a synchronous-first experience.

The safest brownfield move is therefore to treat Phase 12 as a runtime-boundary cleanup phase, not an analysis or UI redesign phase. The worker boot issue should be fixed at the import boundary, not by moving metrics into a new subsystem or rewriting the worker loop. `backend/repositories/run_execution_job_repository.py` only needs `AnalysisRunService`, but importing `backend.services.analysis_run_service` causes Python to execute `backend/services/__init__.py`, which currently re-exports heavy service modules. Simplifying `backend/services/__init__.py` so it no longer eagerly imports `EdgarPipelineExecutionService` or `EvaluationControlPlaneService` breaks the circular chain with minimal blast radius because repo search shows the package-level re-export surface is not actually relied on elsewhere.

On the chat side, the user-selected product policy is clear: make synchronous execution the only primary mode for now. That means the UI should stop offering a healthy-looking queue toggle to ordinary chat users in this phase. The current `createAnalysisRunFromChat(...)` server action already owns the mode split; it can coerce or ignore stale `enqueue_execution` requests, execute synchronously by default, and attach a structured status note to the assistant reply. The chat shell can then show a persistent workspace-level strip that explains the current delivery mode and a per-message note when a request that asked for background delivery was rerouted. This is the cleanest way to honor the user’s `1C/2C/3A` choices without inventing streaming or a richer answer contract ahead of schedule.

The auth/onboarding scope expansion should stay small and surgical. The current login/register pages are misleading in a secure-default local stack because they keep advertising `/register` even when registration is closed and bootstrap may already be completed. The minimal phase-appropriate remedy is a coarse public auth-capability read model: expose whether registration is open, whether bootstrap is still needed, and whether the user should simply sign in. The frontend can use that to replace the dead-end “Create account” flow with truthful copy and links, without exposing secrets or broadening into account-management work.

**Primary recommendation:** plan Phase 12 as **3 sequential plans**. First, repair worker boot/runtime seams and lock the Compose/runtime baseline with focused regressions. Second, make chat delivery sync-first and explicitly truthful about background availability, including automatic fallback for stale queue requests. Third, clean up first-run auth/onboarding surfaces so the secure-default local stack no longer funnels users into dead-end registration flows. That shape satisfies `RUN-01`, `RUN-02`, and `RUN-03` while keeping the later chat-answer phases intact.

## Recommended Patterns

### Pattern 1: Fix the Worker at the Package Import Boundary

**What:** Remove eager heavy imports from `backend/services/__init__.py` so importing a lightweight submodule such as `backend.services.analysis_run_service` does not also import the pipeline and LLM service graph.

**When to use:** Worker startup, queue observability imports, and any repository or health path that only needs lightweight services.

**Why:** The worker boot failure is not caused by the worker loop logic itself. It is caused by package import side effects. Fixing the import boundary is the smallest repair that preserves the current runtime model.

**Recommended shape:**
- Keep `backend/services/__init__.py` as a light namespace surface or remove most re-exports entirely.
- Do not move `observe_llm_completion(...)` or LLM logging into a new subsystem unless needed after the import-boundary fix.
- Add a focused regression that imports the worker entrypoint and/or calls worker processing without triggering the circular import.

### Pattern 2: Sync-Only Chat Mode Should Be Enforced Server-Side, Not Just Styled Away

**What:** Treat synchronous execution as the authoritative Phase 12 chat mode in the server action, not merely a default checkbox state in the UI.

**When to use:** Every chat submission path in `frontend/src/actions/runs.ts`.

**Why:** The UI can be stale, manipulated, or behind the latest deployment. The server action is the one place that can guarantee a queue request is coerced or rejected truthfully.

**Recommended behavior:**
- Hide or collapse `Queue for worker` in the composer for ordinary chat users.
- In `createAnalysisRunFromChat(...)`, always create a non-enqueued run for the primary flow and call `executeRun(...)`.
- If a stale or explicit queue request still reaches the server action, coerce to sync execution and return assistant-reply metadata that the request was rerouted.

### Pattern 3: Chat Needs a Coarse Runtime-Status Contract, Not Raw Ops Health

**What:** Add a user-safe runtime-status shape that the chat workspace can consume without requiring the ops-only worker-health route.

**When to use:** Header/composer status strip and per-message delivery notes.

**Why:** `/v1/worker/health` is correctly ops-protected, but chat still needs a truthful explanation of delivery mode. Exposing raw queue counts or ops-token routes to ordinary users is unnecessary.

**Recommended contract:**
- Coarse fields only: e.g. `delivery_mode`, `background_delivery_available`, `detail`
- Values should support at least `sync_only`, `background_ready`, and `background_degraded`
- It is acceptable in Phase 12 for chat to report a stable `sync_only` mode even after the worker is repaired, because the user explicitly chose synchronous-first behavior for this phase

### Pattern 4: Auth Onboarding Should Use Capability Discovery, Not Hardcoded Marketing Copy

**What:** Add a lightweight auth capability read model so login/register pages can tell whether registration is open, whether bootstrap is still needed, and whether the correct action is simply sign-in.

**When to use:** `frontend/src/app/login/page.tsx`, `frontend/src/app/register/page.tsx`, and possibly the landing/auth links.

**Why:** The current frontend hardcodes a generic registration story that is false in secure-default deployments. A small capability endpoint or server-side auth-status fetch is enough to remove the dead-end flow.

**Recommended shape:**
- Public coarse response only, no secrets or token material
- Suggested fields: `allow_open_registration`, `bootstrap_required`, `bootstrap_completed`
- Login page can hide or replace the “Create one” link when registration is closed and bootstrap is already complete
- Register page can become a bootstrap guidance page or redirect away when registration is not the correct path

## Implementation Slices

### Slice A: Worker Boot and Compose Runtime Foundation

Focus files:
- `backend/services/__init__.py`
- `backend/worker/__main__.py`
- `backend/worker/loop.py`
- `backend/observability/metrics.py`
- `docker-entrypoint.sh`
- `tests/test_worker_lease_heartbeat.py`
- `tests/test_backend_health.py`
- `tests/test_async_run_queue.py`

Deliver:
- worker boot no longer fails from the current circular import
- queued runs can be claimed in the documented local stack
- the run-workspace entrypoint contract remains locked by regression coverage or smoke verification

### Slice B: Sync-First Chat Runtime Contract

Focus files:
- `frontend/src/actions/runs.ts`
- `frontend/src/components/chat-shell/chat-composer.tsx`
- `frontend/src/components/chat-shell/chat-shell.tsx`
- `frontend/src/components/chat-shell/chat-message-list.tsx`
- `frontend/src/components/chat-shell/types.ts`
- `backend/api/routes/health.py`
- `backend/schemas/health.py`
- `frontend/src/lib/api/`
- `frontend/src/components/chat-shell/*.test.tsx`

Deliver:
- chat runs execute synchronously by default
- stale queue requests automatically fall back to sync execution
- workspace-level and per-message delivery status is explicit and truthful
- chat no longer visually implies that queued delivery is the normal healthy path

### Slice C: First-Run Auth and Onboarding Cleanup

Focus files:
- `backend/api/routes/auth.py`
- `backend/schemas/auth.py` or a small new auth-capability schema file
- `frontend/src/actions/auth.ts`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/register/page.tsx`
- `frontend/src/components/auth/register-form.tsx`
- `tests/test_auth_api.py`
- `tests/test_secure_defaults_api.py`
- `frontend/src/components/auth/*.test.tsx`

Deliver:
- login/register surfaces stop routing users into a dead-end registration flow
- bootstrap-needed vs sign-in-only state is explicit in the local secure-default stack
- onboarding cleanup remains narrowly scoped to first-run chat blockers, not general account management

## Validation Architecture

Phase 12 needs both backend and frontend verification because the runtime policy change crosses API, worker, chat UI, and auth surfaces.

**Recommended quick command:**
```bash
python3 -m pytest tests/test_backend_health.py tests/test_worker_lease_heartbeat.py tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short && cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/auth/register-form.test.tsx
```

**Recommended full command:**
```bash
python3 -m pytest tests/test_backend_health.py tests/test_worker_lease_heartbeat.py tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short && cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/auth/register-form.test.tsx && npm run build
```

**Manual smoke that should remain in the phase:**
- rebuild the documented Compose stack
- sign in through the local web app
- submit a chat prompt and confirm it executes synchronously without workspace-permission errors
- verify the chat header/composer explains the current delivery mode truthfully

**Required new or extended tests:**
- `tests/test_worker_lease_heartbeat.py` or a new worker import smoke — import/boot regression for the worker circular-import path
- `tests/test_async_run_queue.py` / `tests/test_worker_job_lifecycle.py` — queued jobs can be claimed and moved off pending in the repaired local stack
- `tests/test_backend_health.py` — coarse public delivery-status contract plus existing ops truthfulness
- `tests/test_auth_api.py` and `tests/test_secure_defaults_api.py` — auth capability contract and bootstrap/closed-registration states
- `frontend/src/components/chat-shell/chat-composer.test.tsx` — sync-only mode and hidden/de-emphasized queue affordance
- `frontend/src/components/chat-shell/chat-shell.test.tsx` / `chat-message-list.test.tsx` — workspace-level and per-message delivery-status rendering
- `frontend/src/components/auth/register-form.test.tsx` — environment-aware register/bootstrap guidance

## Pitfalls and Boundaries

- Do not split synchronous and async execution into separate analysis engines; they already share `EdgarPipelineExecutionService`.
- Do not “fix” the worker by weakening observability or removing metrics entirely; fix the import boundary instead.
- Do not keep `Queue for worker` visible as a normal healthy option in chat while Phase 12 policy says sync-first.
- Do not implement silent fallback with no disclosure; the user explicitly chose automatic fallback plus visible truthfulness.
- Do not solve onboarding by reopening registration broadly in secure-default environments.
- Do not widen this phase into chat-answer rendering, evidence navigation, or a full auth redesign.

## Recommended Plan Shape

Phase 12 should be planned as **3 sequential plans**:

1. **Plan 01 — Worker/runtime foundation**
   - repair the worker boot import cycle
   - lock the Compose runtime baseline and queued-claim behavior with focused regressions

2. **Plan 02 — Sync-first chat runtime contract**
   - make chat synchronous by default
   - add automatic fallback for stale queue requests
   - expose truthful workspace/per-message delivery status

3. **Plan 03 — First-run auth/onboarding cleanup**
   - add a coarse auth-capability contract
   - remove dead-end registration flows in secure-default local use
   - harden with frontend/backend regressions and one final local smoke path
