# Phase 12: Runtime Reliability for Chat Delivery - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Make chat-triggered delivery reliable in the documented local stack before chat becomes the primary answer surface. This phase covers the worker boot/runtime blockers, chat submission defaults, automatic fallback behavior when background delivery is degraded, chat-visible degraded-state reporting, and the first-run auth/onboarding seams discovered during live testing that currently block or confuse chat usage.

It does not redesign the chat-native answer contract, evidence navigation, or secondary run-inspection experience; those remain later v1.2 phases.

</domain>

<decisions>
## Implementation Decisions

### Chat submission default
- **D-01:** Chat should force synchronous execution as the primary path for this phase instead of keeping worker queueing as an equal default.
- **D-02:** Runtime reliability takes precedence over preserving the current dual-mode chat affordance; the UI may collapse or hide the queue choice temporarily if that is the cleanest truthful behavior.

### Worker-unavailable behavior
- **D-03:** If a user requests worker queueing while background delivery is degraded or unavailable, the product should automatically fall back to synchronous execution rather than rejecting the request or accepting a stuck queued run.
- **D-04:** The fallback should not require an extra confirmation step, but it must still be reflected in status surfaces and message metadata so the user can tell what actually happened.

### Degraded-state visibility in chat
- **D-05:** Chat should show a persistent workspace-level background-delivery status near the composer.
- **D-06:** Chat should also show a per-message note whenever the requested background path was unavailable, degraded, or automatically rerouted to synchronous execution.

### Expanded scope boundary
- **D-07:** Phase 12 may include auth and onboarding fixes discovered during live testing if they materially block first-run chat delivery in the local stack.
- **D-08:** This expanded scope is still bounded to delivery-critical seams: worker boot/runtime reliability, queue truthfulness, chat-visible degradation, and onboarding blockers directly encountered while trying to use chat.

### the agent's Discretion
- Exact UI treatment for collapsing or hiding the queue option while synchronous execution is the enforced default
- Exact mechanism for surfacing fallback disclosure in message metadata, composer status, or helper text
- Exact technical fix for the worker import cycle and any adjacent runtime issues in Compose
- Exact auth/onboarding remediation, as long as it removes the current first-run dead-end without broadening into a full auth product redesign

</decisions>

<specifics>
## Specific Ideas

- User selected:
  - `1C` force synchronous execution for now
  - `2C` automatic fallback from worker queueing to synchronous execution
  - `3A` show both workspace-level and per-message degraded-state visibility
  - `4C` expand the phase to include auth/onboarding fixes found during testing
- The only meaningful tension is between `2C` and the project’s prior truthfulness constraints; this context resolves that by treating fallback as automatic but still explicitly disclosed.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — v1.2 milestone framing and chat-first product intent
- `.planning/REQUIREMENTS.md` — `RUN-01`, `RUN-02`, and `RUN-03` define the formal runtime requirements for this phase
- `.planning/ROADMAP.md` — Phase 12 goal and success criteria
- `.planning/STATE.md` — current project position after milestone initialization

### Prior phase decisions that constrain this phase
- `.planning/phases/01-run-isolation/01-CONTEXT.md` — run-scoped workspaces are canonical
- `.planning/phases/02-worker-resilience/02-CONTEXT.md` — retries stay on the same run identity and lease/claim behavior must remain explicit
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — secure defaults stay closed by default, so onboarding fixes cannot simply reopen registration everywhere
- `.planning/phases/05-storage-and-ops/05-CONTEXT.md` — degraded state must remain truthful instead of pretending healthy behavior

### Current runtime and chat seams
- `frontend/src/actions/runs.ts` — current chat create/execute/enqueue behavior
- `frontend/src/components/chat-shell/chat-composer.tsx` — current chat controls for execute-now vs queue-for-worker
- `frontend/src/components/chat-shell/chat-shell.tsx` — current placeholder assistant flow
- `backend/api/routes/runs.py` — create, execute, retry, and status routes
- `backend/services/run_queue_service.py` — queued-run creation path
- `backend/worker/loop.py` — worker claim, execute, and finalize loop
- `backend/worker/lease.py` — async-only lease heartbeat behavior
- `backend/services/edgar_pipeline_execution_service.py` — shared execution core for synchronous and async runtimes
- `docker-entrypoint.sh` — local container runtime preparation for shared writable roots

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/edgar_pipeline_execution_service.py` already gives both runtimes a single shared execution core, so this phase should fix dispatch/runtime seams without splitting the analysis engine.
- `frontend/src/actions/runs.ts` already routes chat through one server action, which is the natural place to enforce a temporary synchronous default or automatic fallback.
- `backend/api/routes/runs.py` already exposes both create and synchronous execute surfaces, so chat can lean on the sync path without introducing a new backend contract.
- `backend/api/routes/health.py` and worker/metrics surfaces already support degraded reporting patterns that can be reflected back into chat.

### Established Patterns
- Synchronous chat currently means create the run, then immediately call `/runs/{id}/execute` in the same request flow.
- Async chat currently means create the run with `enqueue_execution=true`, return immediately, and rely on the worker to claim and execute the queued `RunExecutionJob`.
- The worker path adds async-only machinery: claim tokens, lease heartbeat, reclaim, retry scheduling, and background finalization.
- The current local stack proves the synchronous path can still succeed even when the worker is unavailable, which is why the user chose to force sync as the primary Phase 12 behavior.

### Integration Points
- `backend/observability/metrics.py`, `backend/services/recorded_chat_completion_service.py`, and `backend/services/__init__.py` are part of the current worker boot failure chain
- `frontend/src/app/projects/[projectId]/chat/page.tsx`, `frontend/src/components/chat-shell/chat-message-list.tsx`, and related chat components are where degraded-state visibility and fallback disclosure need to surface
- Auth routes and frontend register/login entrypoints are now in-scope only insofar as they block first-run chat use during local testing

</code_context>

<deferred>
## Deferred Ideas

- Chat-native answer rendering and message schema — later v1.2 phases
- Evidence navigation and artifact rail inside chat — later v1.2 phases
- Broader auth/onboarding redesign not directly required for first-run chat delivery

</deferred>

---

*Phase: 12-runtime-reliability-for-chat-delivery*
*Context gathered: 2026-04-18*
