---
phase: 14-chat-native-result-contract
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - frontend/src/lib/chat-run-history.ts
  - frontend/src/lib/chat-run-history.test.ts
  - frontend/src/app/projects/[projectId]/chat/page.tsx
  - frontend/src/components/chat-shell/chat-shell.tsx
  - frontend/src/components/chat-shell/chat-sidebar.tsx
  - frontend/src/components/chat-shell/types.ts
  - frontend/src/components/chat-shell/chat-shell.test.tsx
autonomous: true
requirements:
  - CHAT-01
  - CHAT-03
must_haves:
  truths:
    - "Workspace chat hydrates a reload-safe transcript from persisted project runs instead of relying on `local-1` stub sessions."
    - "The visible chat surface becomes one workspace-level conversation; follow-up prompts append to that thread instead of switching between fake local conversations."
    - "Hydrated history and newly submitted prompts share the same structured assistant message contract, so run linkage survives reload and new messages still upgrade in place."
  artifacts:
    - path: frontend/src/lib/chat-run-history.ts
      provides: "Bounded persisted-run to chat-message mapping for reload-safe workspace transcripts"
    - path: frontend/src/app/projects/[projectId]/chat/page.tsx
      provides: "Server-rendered chat page that seeds the transcript from persisted project runs"
    - path: frontend/src/components/chat-shell/chat-shell.tsx
      provides: "Client chat shell initialized from persisted history instead of fake local sessions"
    - path: frontend/src/components/chat-shell/chat-sidebar.tsx
      provides: "Sidebar that no longer pretends client-only sessions are durable conversations"
  key_links:
    - from: frontend/src/lib/chat-run-history.ts
      to: frontend/src/actions/runs.ts
      via: "Hydrated history and live server-action replies both use the same compact chat-answer contract"
      pattern: "buildCompactChatAnswerView|answerCard|runStatus"
    - from: frontend/src/app/projects/[projectId]/chat/page.tsx
      to: frontend/src/lib/chat-run-history.ts
      via: "The chat page server-renders initial transcript messages and secondary recent-run metadata from persisted runs"
      pattern: "buildProjectChatHistory|initialMessages|recentRuns"
    - from: frontend/src/components/chat-shell/chat-shell.tsx
      to: frontend/src/components/chat-shell/chat-sidebar.tsx
      via: "The shell moves from fake local session selection to one workspace-level thread with secondary recent-run context"
      pattern: "initialMessages|recentRuns|Recent runs"
---

<objective>
Hydrate workspace chat from persisted project runs and remove the fake local conversation model so the chat transcript becomes reload-safe and visibly tied to real run history.

Purpose: satisfy the reload-safe continuity half of `CHAT-01` and `CHAT-03` without introducing full persisted multi-thread chat infrastructure.
Output: persisted-run transcript mapping, server-rendered initial history, and a one-thread workspace chat shell.
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
@.planning/phases/14-chat-native-result-contract/14-CONTEXT.md
@.planning/phases/14-chat-native-result-contract/14-RESEARCH.md
@.planning/phases/14-chat-native-result-contract/14-VALIDATION.md
@.planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
@.planning/phases/14-chat-native-result-contract/14-chat-native-result-contract-01-PLAN.md
@frontend/src/app/projects/[projectId]/chat/page.tsx
@frontend/src/components/chat-shell/chat-shell.tsx
@frontend/src/components/chat-shell/chat-sidebar.tsx
@frontend/src/components/chat-shell/types.ts
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/lib/api/runs.ts
@frontend/src/actions/runs.ts

<interfaces>
From `frontend/src/lib/api/runs.ts`:
```ts
export async function listRuns(projectId: string): Promise<AnalysisRunSummary[]>
export async function getRun(runId: string, options?: boolean | RunFetchOptions): Promise<AnalysisRunDetail>
```

From `frontend/src/components/chat-shell/chat-shell.tsx`:
```ts
export function ChatShell({ projectId, tickers, backgroundDelivery }: Props)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Build a persisted-run transcript mapper for the workspace chat seed</name>
  <files>frontend/src/lib/chat-run-history.ts
frontend/src/lib/chat-run-history.test.ts
frontend/src/lib/api/runs.ts
frontend/src/components/chat-shell/types.ts</files>
  <read_first>.planning/phases/14-chat-native-result-contract/14-CONTEXT.md
.planning/phases/14-chat-native-result-contract/14-RESEARCH.md
.planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
.planning/phases/14-chat-native-result-contract/14-chat-native-result-contract-01-PLAN.md
frontend/src/lib/api/runs.ts
frontend/src/actions/runs.ts
frontend/src/components/chat-shell/types.ts
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - Reloading the chat page must reconstruct a bounded visible transcript from persisted project runs.
    - Each persisted run must map to exactly one user message and one assistant message in the visible transcript.
    - Hydrated assistant messages must use the same `answerCard`, `runStatus`, `runCreatedAt`, and `runFinishedAt` fields as live server-action replies.
  </behavior>
  <action>Create `frontend/src/lib/chat-run-history.ts` and export an exact helper named `buildProjectChatHistory(projectId: string, limit = 12)`. That helper must call `listRuns(projectId)`, take the most recent `12` runs by `created_at`, hydrate each with `getRun(run.id, { includeTransparency: true })`, and map them into one transcript seed object with two arrays: `messages` and `recentRuns`. For each hydrated run, create one user message from `orchestration_goal_text` and one assistant message. For supported runs, the assistant message must reuse `buildPrimaryAnswerView(...)` plus `buildCompactChatAnswerView(...)`; for unsupported or sparse runs, keep the same fallback summary semantics the run page already uses. Sort the final `messages` array oldest-to-newest for transcript rendering. Add `frontend/src/lib/chat-run-history.test.ts` that proves two persisted runs become four transcript rows and that a completed run produces an assistant message containing `answerCard` and `runHref`.</action>
  <acceptance_criteria>`frontend/src/lib/chat-run-history.ts` exists.
`frontend/src/lib/chat-run-history.ts` contains `export async function buildProjectChatHistory(`.
`frontend/src/lib/chat-run-history.ts` contains `limit = 12`.
`frontend/src/lib/chat-run-history.ts` contains `listRuns(`.
`frontend/src/lib/chat-run-history.ts` contains `getRun(`.
`frontend/src/lib/chat-run-history.ts` contains `messages`.
`frontend/src/lib/chat-run-history.ts` contains `recentRuns`.
`frontend/src/lib/chat-run-history.test.ts` exists.
`frontend/src/lib/chat-run-history.test.ts` contains `buildProjectChatHistory`.
`frontend/src/lib/chat-run-history.test.ts` asserts `answerCard`.
`cd frontend && npm run test -- src/lib/chat-run-history.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/chat-run-history.test.ts</automated>
  </verify>
  <done>The app can now derive a reload-safe workspace transcript from persisted runs using the same answer contract as live chat submissions.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace fake local sessions with one persisted workspace thread</name>
  <files>frontend/src/app/projects/[projectId]/chat/page.tsx
frontend/src/components/chat-shell/chat-shell.tsx
frontend/src/components/chat-shell/chat-sidebar.tsx
frontend/src/components/chat-shell/types.ts
frontend/src/components/chat-shell/chat-shell.test.tsx</files>
  <read_first>.planning/phases/14-chat-native-result-contract/14-CONTEXT.md
.planning/phases/14-chat-native-result-contract/14-RESEARCH.md
.planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
frontend/src/app/projects/[projectId]/chat/page.tsx
frontend/src/components/chat-shell/chat-shell.tsx
frontend/src/components/chat-shell/chat-sidebar.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/lib/chat-run-history.ts</read_first>
  <behavior>
    - The page must seed the transcript from persisted history on first load.
    - The client shell must stop creating or switching fake local conversations such as `local-1` or `New conversation`.
    - Follow-up prompts must append to the same visible thread while preserving the current in-place pending upgrade behavior.
  </behavior>
  <action>Update `frontend/src/app/projects/[projectId]/chat/page.tsx` so it calls `buildProjectChatHistory(projectId)` on the server and passes the resulting `initialMessages` and `recentRuns` into `ChatShell`. In `frontend/src/components/chat-shell/chat-shell.tsx`, delete the `sessions`, `activeSessionId`, `messagesBySession`, `local-1`, `newId()`, `initialMessages()`, `onNewSession`, and `onSelectSession` conversation-stub machinery. Replace it with one `messages` state initialized from the new `initialMessages` prop, and keep the existing request-id keyed pending-replacement behavior in that one array. Update `frontend/src/components/chat-shell/chat-sidebar.tsx` so it no longer accepts `sessions`, `activeSessionId`, `onNewSession`, or `onSelectSession`. Replace the old `New conversation` section with a read-only `Recent runs` section backed by the `recentRuns` prop, while leaving the workspace navigation links intact. Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` so it covers initial hydrated history rendering and verifies that sending a new prompt appends beneath existing persisted rows rather than resetting to a fake local session.</action>
  <acceptance_criteria>`frontend/src/app/projects/[projectId]/chat/page.tsx` contains `buildProjectChatHistory(`.
`frontend/src/app/projects/[projectId]/chat/page.tsx` contains `initialMessages`.
`frontend/src/app/projects/[projectId]/chat/page.tsx` contains `recentRuns`.
`frontend/src/components/chat-shell/chat-shell.tsx` no longer contains `local-1`.
`frontend/src/components/chat-shell/chat-shell.tsx` no longer contains `messagesBySession`.
`frontend/src/components/chat-shell/chat-shell.tsx` no longer contains `activeSessionId`.
`frontend/src/components/chat-shell/chat-sidebar.tsx` contains `Recent runs`.
`frontend/src/components/chat-shell/chat-sidebar.tsx` no longer contains `New conversation`.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains an assertion for hydrated history content before a new send.
`cd frontend && npm run test -- src/components/chat-shell/chat-shell.test.tsx src/lib/chat-run-history.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-shell.test.tsx src/lib/chat-run-history.test.ts</automated>
  </verify>
  <done>The workspace chat is now one persisted, reload-safe visible thread instead of a set of fake local conversation tabs.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/lib/chat-run-history.test.ts src/components/chat-shell/chat-shell.test.tsx` after both tasks land.
</verification>

<success_criteria>
Phase 14 has a valid second wave once the chat page reloads into a persisted run-backed transcript, fake local conversation stubs are gone, and new prompts continue the same visible thread with stable run linkage.
</success_criteria>

<output>
After completion, create `.planning/phases/14-chat-native-result-contract/14-chat-native-result-contract-02-SUMMARY.md`
</output>
