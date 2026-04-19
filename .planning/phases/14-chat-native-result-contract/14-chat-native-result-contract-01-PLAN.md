---
phase: 14-chat-native-result-contract
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/actions/runs.ts
  - frontend/src/components/chat-shell/types.ts
  - frontend/src/components/chat-shell/assistant-structured-frame.tsx
  - frontend/src/components/chat-shell/chat-message-list.tsx
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/actions/runs.test.ts
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
autonomous: true
requirements:
  - CHAT-01
must_haves:
  truths:
    - "A supported chat request returns a typed compact answer payload derived from the existing run-answer builder instead of only plain status text and follow-up links."
    - "The assistant slot reuses one structured footprint for pending and completed states so a request upgrades in place without duplicate completion chatter."
    - "The chat answer surface reuses the standalone run page's conclusion, goal, conclusion-rider, and orchestration-status semantics rather than inventing a second answer language."
  artifacts:
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Compact chat-answer view builder layered on top of the existing primary-answer derivation path"
    - path: frontend/src/actions/runs.ts
      provides: "Server action that hydrates the finished run and returns a structured assistant answer payload"
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Compact chat-native answer card aligned to the approved Phase 14 UI contract"
    - path: frontend/src/actions/runs.test.ts
      provides: "Regression coverage for the new structured reply contract on supported runs"
  key_links:
    - from: frontend/src/actions/runs.ts
      to: frontend/src/lib/run-primary-view.ts
      via: "The server action hydrates the finished run and converts it into a compact chat answer with the same summary semantics used by the standalone run page"
      pattern: "buildPrimaryAnswerView|buildCompactChatAnswerView|getRun("
    - from: frontend/src/components/chat-shell/chat-message-list.tsx
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "Structured assistant replies render through a dedicated answer-card component while unsupported guidance remains on the prose branch"
      pattern: "answerCard|ChatRunAnswerCard|rewriteSuggestions"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: .planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
      via: "The answer card follows the approved compact hierarchy: conclusion first, goal second, pending and final states share one footprint"
      pattern: "Conclusion|Goal|Running analysis...|Updating…"
---

<objective>
Create the compact structured answer contract for chat and render it in the assistant slot, while keeping the result semantics tied to the existing run-answer builder.

Purpose: satisfy the first half of `CHAT-01` by making chat capable of showing the primary answer content itself instead of only linking out to the run page.
Output: compact chat-answer payloads from the server action, a dedicated answer-card component, and pending/final rendering coverage.
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
@frontend/src/lib/run-primary-view.ts
@frontend/src/actions/runs.ts
@frontend/src/actions/runs.test.ts
@frontend/src/components/chat-shell/types.ts
@frontend/src/components/chat-shell/assistant-structured-frame.tsx
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/lib/api/runs.ts
@frontend/src/lib/orchestration-output.ts
@frontend/src/lib/ai-agents-meta.ts

<interfaces>
From `frontend/src/lib/run-primary-view.ts`:
```ts
export function buildPrimaryAnswerView(
  input,
  artifacts,
  orch,
  userReport,
  ai,
  nav?,
): PrimaryAnswerView
```

From `frontend/src/actions/runs.ts`:
```ts
type ChatReply = {
  requestId: string;
  content: string;
  runId?: string;
  runHref?: string;
  deepDiveHref?: string;
  runsHref?: string;
}
```

From `frontend/src/components/chat-shell/types.ts`:
```ts
export type ChatAssistantMessage = {
  id: string;
  role: "assistant";
  content: string;
  pending?: boolean;
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add a compact chat-answer view model and return it from the chat run action</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/actions/runs.ts
frontend/src/components/chat-shell/types.ts
frontend/src/actions/runs.test.ts</files>
  <read_first>.planning/phases/14-chat-native-result-contract/14-CONTEXT.md
.planning/phases/14-chat-native-result-contract/14-RESEARCH.md
.planning/phases/14-chat-native-result-contract/14-VALIDATION.md
.planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
frontend/src/lib/run-primary-view.ts
frontend/src/actions/runs.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/api/runs.ts
frontend/src/lib/orchestration-output.ts
frontend/src/lib/ai-agents-meta.ts</read_first>
  <behavior>
    - Supported synchronous chat runs must return a structured answer payload, not just plain prose and navigation links.
    - The compact answer payload must come from the same orchestration parsing and primary-answer derivation path already used by the standalone run page.
    - Unsupported routing guidance must remain its existing branch; this task only changes the supported-run response shape.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add an exact exported type `CompactChatAnswerView` and an exact exported helper `buildCompactChatAnswerView(view: PrimaryAnswerView): CompactChatAnswerView`. That helper must return only the Phase 14 subset: `goalDisplay`, `summaryLine`, `orchestrationStatus`, and `conclusionRider`. In `frontend/src/actions/runs.ts`, extend `ChatReply` with an optional `answerCard` field of type `CompactChatAnswerView`, plus `runStatus`, `runCreatedAt`, and `runFinishedAt`. After `executeRun(run.id, {})` resolves, call `getRun(run.id, { includeTransparency: true })`, then derive `orch` with `parseOrchestrationOutput(...)`, `userReport` with `parseUserFacingReport(...)`, and `ai` with `parseAiAgents(...)`. Pass those into `buildPrimaryAnswerView(hydratedRun, [], orch, userReport, ai, { projectId, runId: run.id })`, then convert that full view with `buildCompactChatAnswerView(...)`. Return that structured payload on the supported branch instead of the current plain success or error sentence. Keep the unsupported preview branch untouched. Extend `frontend/src/components/chat-shell/types.ts` so assistant messages can carry `answerCard`, `runStatus`, `runCreatedAt`, and `runFinishedAt`. Extend `frontend/src/actions/runs.test.ts` so the supported branch asserts `getRun(...)` is called after execution and the reply includes an `answerCard` object instead of only link strings.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains `export type CompactChatAnswerView`.
`frontend/src/lib/run-primary-view.ts` contains `export function buildCompactChatAnswerView(`.
`frontend/src/lib/run-primary-view.ts` contains `goalDisplay`.
`frontend/src/lib/run-primary-view.ts` contains `summaryLine`.
`frontend/src/actions/runs.ts` contains `answerCard`.
`frontend/src/actions/runs.ts` contains `runStatus`.
`frontend/src/actions/runs.ts` contains `getRun(run.id`.
`frontend/src/actions/runs.ts` contains `parseOrchestrationOutput`.
`frontend/src/actions/runs.ts` contains `buildCompactChatAnswerView`.
`frontend/src/components/chat-shell/types.ts` contains `answerCard`.
`frontend/src/actions/runs.test.ts` contains `getRun`.
`frontend/src/actions/runs.test.ts` asserts `answerCard`.
`cd frontend && npm run test -- src/actions/runs.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/actions/runs.test.ts</automated>
  </verify>
  <done>Supported chat runs now return a compact structured answer payload derived from the same answer-building path as the standalone run page.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Render the compact answer card in chat and reuse the same footprint for pending replies</name>
  <files>frontend/src/components/chat-shell/assistant-structured-frame.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/14-chat-native-result-contract/14-CONTEXT.md
.planning/phases/14-chat-native-result-contract/14-RESEARCH.md
.planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
frontend/src/components/chat-shell/assistant-structured-frame.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/types.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/runs/run-primary-answer.tsx</read_first>
  <behavior>
    - Supported assistant replies must render as a compact answer card, not as plain prose bubbles.
    - Pending assistant replies must keep the same structured footprint and show `Running analysis...` plus `Updating…`.
    - Unsupported rewrite-guidance replies must stay on the current prose-and-suggestions path with no structured answer card.
  </behavior>
  <action>Create `frontend/src/components/chat-shell/chat-run-answer-card.tsx` as the dedicated Phase 14 structured assistant card. Use the approved shadcn surfaces already present in the repo (`card`, `separator`, `skeleton`) and render exactly these sections in order: `Conclusion`, optional note text for `conclusionRider`, `Goal`, and optional technical-status disclosure. Do not add findings, caveats, evidence summaries, or a run strip yet. Update `frontend/src/components/chat-shell/assistant-structured-frame.tsx` so its inner placeholder becomes a reusable pending shell with skeleton or muted blocks instead of the generic “Structured blocks mount here” copy. Then update `frontend/src/components/chat-shell/chat-message-list.tsx` so assistant messages with `answerCard` render `ChatRunAnswerCard`, assistant messages with `pending=true` render `AssistantStructuredFrame variant=\"pending\"`, and assistant messages with only `rewriteSuggestions` stay on the current unsupported-guidance branch. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` so one test proves a completed assistant message renders `Conclusion` and `Goal` from `answerCard`, and another proves a pending assistant message still shows `Running analysis...` and `Updating…` in the structured footprint.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` exists.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Conclusion`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Goal`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain `Top findings`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain `Confidence & caveats`.
`frontend/src/components/chat-shell/assistant-structured-frame.tsx` contains `Updating…`.
`frontend/src/components/chat-shell/chat-message-list.tsx` contains `answerCard`.
`frontend/src/components/chat-shell/chat-message-list.tsx` contains `ChatRunAnswerCard`.
`frontend/src/components/chat-shell/chat-message-list.tsx` contains `AssistantStructuredFrame`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Conclusion`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Running analysis...`.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>Chat can now render compact structured answer cards and pending structured slots without falling back to generic assistant prose.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx` after both tasks land.
</verification>

<success_criteria>
Phase 14 has a valid first wave once supported chat submissions return a compact structured answer payload, the transcript renders that payload as a dedicated answer card, and pending replies use the same footprint instead of duplicate completion chatter.
</success_criteria>

<output>
After completion, create `.planning/phases/14-chat-native-result-contract/14-chat-native-result-contract-01-SUMMARY.md`
</output>
