---
phase: 12-runtime-reliability-for-chat-delivery
plan: 02
type: execute
wave: 2
depends_on:
  - "12-01"
files_modified:
  - backend/config/settings.py
  - backend/schemas/health.py
  - backend/api/routes/health.py
  - frontend/src/lib/api/types.ts
  - frontend/src/lib/api/runs.ts
  - frontend/src/app/projects/[projectId]/chat/page.tsx
  - frontend/src/actions/runs.ts
  - frontend/src/components/chat-shell/types.ts
  - frontend/src/components/chat-shell/chat-composer.tsx
  - frontend/src/components/chat-shell/chat-shell.tsx
  - frontend/src/components/chat-shell/chat-message-list.tsx
  - frontend/src/components/chat-shell/chat-composer.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
autonomous: true
requirements:
  - RUN-03
must_haves:
  truths:
    - "Workspace chat defaults to synchronous execution for this phase instead of presenting queued delivery as a co-equal normal path."
    - "If a stale or explicit background request still reaches the server action, it is rerouted to synchronous execution and that reroute is disclosed to the user."
    - "Chat-visible runtime status comes from a coarse user-safe contract rather than the ops-only worker-health endpoint."
  artifacts:
    - path: frontend/src/actions/runs.ts
      provides: "Sync-first server action with explicit fallback and assistant reply metadata"
    - path: backend/schemas/health.py
      provides: "User-safe background delivery status contract for chat surfaces"
    - path: frontend/src/components/chat-shell/chat-shell.tsx
      provides: "Workspace-level runtime-status strip plus per-message delivery notes"
    - path: frontend/src/components/chat-shell/chat-composer.test.tsx
      provides: "Frontend regression coverage for sync-only chat mode"
  key_links:
    - from: backend/api/routes/health.py
      to: frontend/src/app/projects/[projectId]/chat/page.tsx
      via: "the chat page consumes a coarse public background-delivery status instead of the ops-only worker route"
      pattern: "background_delivery|delivery_mode|detail"
    - from: frontend/src/actions/runs.ts
      to: frontend/src/components/chat-shell/types.ts
      via: "assistant reply metadata captures when a background request was rerouted or when sync-only mode is active"
      pattern: "deliveryMode|deliveryDetail|reroutedFromBackground"
    - from: frontend/src/components/chat-shell/chat-message-list.tsx
      to: frontend/src/components/chat-shell/chat-shell.tsx
      via: "workspace-level and per-message runtime truth use the same delivery-status contract"
      pattern: "Background delivery|Sync only|rerouted"
---

<objective>
Convert workspace chat to a sync-first runtime contract with visible fallback and degraded-status reporting.

Purpose: satisfy the user-facing half of Phase 12 so chat no longer implies background delivery is healthy when it is not the primary supported mode.
Output: a coarse runtime-status API contract, sync-first chat submission behavior, and frontend regressions for workspace/per-message status.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-01-PLAN.md
@backend/config/settings.py
@backend/schemas/health.py
@backend/api/routes/health.py
@frontend/src/app/projects/[projectId]/chat/page.tsx
@frontend/src/actions/runs.ts
@frontend/src/components/chat-shell/types.ts
@frontend/src/components/chat-shell/chat-composer.tsx
@frontend/src/components/chat-shell/chat-shell.tsx
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/lib/api/runs.ts
@frontend/src/lib/api/types.ts

<interfaces>
From `frontend/src/actions/runs.ts`:
```ts
export async function createAnalysisRunFromChat(projectId: string, prev: ..., formData: FormData): Promise<{ error?: string; reply?: ... }>
```

From `backend/schemas/health.py`:
```python
class HealthResponse(BaseModel):
    status: str
    version: str
    database: DatabaseHealth
    llm: LlmHealth
    evaluation: EvaluationDependencyHealth
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add a coarse public background-delivery status contract for chat</name>
  <files>backend/config/settings.py
backend/schemas/health.py
backend/api/routes/health.py
frontend/src/lib/api/types.ts
frontend/src/lib/api/runs.ts
frontend/src/app/projects/[projectId]/chat/page.tsx</files>
  <read_first>.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
backend/config/settings.py
backend/schemas/health.py
backend/api/routes/health.py
backend/observability/worker_queue.py
frontend/src/lib/api/types.ts
frontend/src/lib/api/runs.ts
frontend/src/app/projects/[projectId]/chat/page.tsx</read_first>
  <behavior>
    - Chat can read a user-safe public delivery-mode signal without depending on the ops-token-protected worker-health route.
    - The delivery-mode signal distinguishes at least sync-only, background-ready, and background-degraded states.
    - The chat page can fetch this status server-side and pass it into the workspace shell on first render.
  </behavior>
  <action>Add an explicit backend setting in `backend/config/settings.py` for Phase 12 chat policy, such as `chat_force_synchronous: bool = True`, with a description that this keeps workspace chat on the synchronous path while background delivery is not the primary supported mode. Extend `backend/schemas/health.py` with a new `BackgroundDeliveryHealth` model containing the exact fields `delivery_mode: str`, `background_available: bool`, and `detail: str | None`, then add `background_delivery: BackgroundDeliveryHealth` to `HealthResponse`. Update `backend/api/routes/health.py` so `/v1/health` populates `background_delivery` using the new setting plus worker queue observability: return `delivery_mode="sync_only"` when the setting forces sync, `delivery_mode="background_degraded"` when stale-running or backlog-without-active-lease flags indicate the background path is unhealthy, and `delivery_mode="background_ready"` otherwise. Extend `frontend/src/lib/api/types.ts` and `frontend/src/lib/api/runs.ts` with a typed helper that fetches `HealthResponse` or the new `background_delivery` slice, and update `frontend/src/app/projects/[projectId]/chat/page.tsx` to fetch that status server-side and pass it as a prop into `ChatShell`.</action>
  <acceptance_criteria>`backend/config/settings.py` contains `chat_force_synchronous`.
`backend/schemas/health.py` contains `class BackgroundDeliveryHealth`.
`backend/schemas/health.py` contains `delivery_mode`.
`backend/schemas/health.py` contains `background_available`.
`backend/schemas/health.py` contains `background_delivery: BackgroundDeliveryHealth`.
`backend/api/routes/health.py` contains `sync_only`.
`backend/api/routes/health.py` contains `background_degraded`.
`backend/api/routes/health.py` contains `background_ready`.
`frontend/src/lib/api/types.ts` contains `background_delivery`.
`frontend/src/app/projects/[projectId]/chat/page.tsx` contains `backgroundDelivery` or `background_delivery`.
`python3 -m pytest tests/test_backend_health.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_backend_health.py -q --tb=short</automated>
  </verify>
  <done>Workspace chat now has a coarse public runtime-status contract it can consume safely on first render.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Enforce sync-first chat submission and disclose automatic fallback</name>
  <files>frontend/src/actions/runs.ts
frontend/src/components/chat-shell/types.ts
frontend/src/components/chat-shell/chat-composer.tsx
frontend/src/components/chat-shell/chat-shell.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-composer.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
frontend/src/actions/runs.ts
frontend/src/components/chat-shell/types.ts
frontend/src/components/chat-shell/chat-composer.tsx
frontend/src/components/chat-shell/chat-shell.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/app/projects/[projectId]/chat/page.tsx</read_first>
  <behavior>
    - Workspace chat should no longer present `Queue for worker` as a normal equal option in this phase.
    - If a stale form submission or explicit queue request still arrives, the server action reroutes it to synchronous execution rather than leaving the request queued.
    - The workspace shows one persistent status strip and one per-message note when a background request was rerouted or background mode is unavailable.
  </behavior>
  <action>Update `frontend/src/actions/runs.ts` so `createAnalysisRunFromChat(...)` treats synchronous execution as the authoritative Phase 12 path: create runs with `enqueue_execution: false` for the normal flow, call `executeRun(...)` immediately, and preserve a legacy branch that detects `enqueue_execution=on` but coerces the request to synchronous execution. Extend the reply payload with the exact metadata fields `deliveryMode`, `deliveryDetail`, and `reroutedFromBackground`. Update `frontend/src/components/chat-shell/types.ts` so `ChatAssistantMessage` carries those fields. Update `frontend/src/components/chat-shell/chat-composer.tsx` to remove the visible `Queue for worker` checkbox, render the workspace-level runtime strip using the `backgroundDelivery` prop, and keep `Execute now` either implicit or the only visible mode. Update `frontend/src/components/chat-shell/chat-shell.tsx` and `frontend/src/components/chat-shell/chat-message-list.tsx` so pending and completed assistant messages render the new delivery metadata and explicitly tell the user when a request was rerouted from background delivery to synchronous execution. Add `chat-composer.test.tsx`, `chat-shell.test.tsx`, and `chat-message-list.test.tsx` to lock the sync-only mode, workspace status strip, and rerouted per-message note.</action>
  <acceptance_criteria>`frontend/src/actions/runs.ts` contains `deliveryMode`.
`frontend/src/actions/runs.ts` contains `deliveryDetail`.
`frontend/src/actions/runs.ts` contains `reroutedFromBackground`.
`frontend/src/actions/runs.ts` contains `enqueue_execution`.
`frontend/src/actions/runs.ts` contains `executeRun(run.id`.
`frontend/src/components/chat-shell/chat-composer.tsx` does not contain `Queue for worker`.
`frontend/src/components/chat-shell/chat-composer.tsx` contains `backgroundDelivery` or `delivery mode`.
`frontend/src/components/chat-shell/types.ts` contains `deliveryMode`.
`frontend/src/components/chat-shell/chat-message-list.tsx` contains `rerouted`.
`frontend/src/components/chat-shell/chat-composer.test.tsx` exists.
`frontend/src/components/chat-shell/chat-shell.test.tsx` exists.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` exists.
`cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>Workspace chat is now sync-first, and any background fallback is visible instead of silently misleading.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_backend_health.py -q --tb=short` after the public delivery-status contract lands, then rerun `cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/chat-shell/chat-message-list.test.tsx` after the sync-first chat UI and reply metadata are in place.
</verification>

<success_criteria>
Phase 12 satisfies the user-visible runtime goal once workspace chat always executes synchronously by default, exposes a truthful coarse delivery status, and clearly discloses any rerouted background request.
</success_criteria>

<output>
After completion, create `.planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-02-SUMMARY.md`
</output>
