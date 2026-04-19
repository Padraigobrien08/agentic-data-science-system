---
phase: 17-narrative-answer-contract
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/actions/runs.ts
  - frontend/src/lib/chat-run-history.ts
  - frontend/src/lib/__tests__/run-primary-view.test.ts
  - frontend/src/actions/runs.test.ts
  - frontend/src/lib/chat-run-history.test.ts
autonomous: true
requirements:
  - ANSR-01
  - ANSR-02
must_haves:
  truths:
    - "Live chat replies and hydrated history prefer the backend `narrative_answer` preview instead of summary-line assembly."
    - "Older runs without the new preview still resolve to a readable narrative-first answer through a legacy compatibility branch."
    - "Limited-support successful runs produce a stable partial narrative, not generic success copy, in both live and hydrated chat paths."
  artifacts:
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Narrative-first answer builder with full, partial, and legacy compatibility branches."
    - path: frontend/src/actions/runs.ts
      provides: "Live chat reply payloads sourced from the narrative-first answer contract."
    - path: frontend/src/lib/chat-run-history.ts
      provides: "Persisted run hydration that reuses the same narrative-first answer builder."
  key_links:
    - "frontend/src/actions/runs.ts and frontend/src/lib/chat-run-history.ts both call `buildChatAnswerCardView` so live and hydrated replies stay on the same contract."
    - "frontend/src/lib/run-primary-view.ts consumes `RunTransparencySummary.narrative_answer` first and only synthesizes a legacy narrative when older runs do not have the new backend preview."
---

<objective>
Refactor the answer builder, live reply path, and history hydration around the new narrative preview contract.

Purpose: satisfy the data-migration half of `ANSR-01` and `ANSR-02` before the renderer changes, while preserving older persisted runs.
Output: narrative-first `PrimaryAnswerView` / `ChatAnswerCardView` data and identical live-vs-history hydration behavior.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
@.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
@.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
@frontend/src/lib/api/types.ts
@frontend/src/lib/run-primary-view.ts
@frontend/src/actions/runs.ts
@frontend/src/lib/chat-run-history.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Make the primary answer builder narrative-first with a legacy compatibility branch</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</files>
  <read_first>.planning/ROADMAP.md
.planning/REQUIREMENTS.md
.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
frontend/src/lib/api/types.ts
frontend/src/lib/run-primary-view.ts
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/lib/__tests__/run-primary-view.test.ts</read_first>
  <behavior>
    - `buildPrimaryAnswerView` prefers the backend `transparency.narrative_answer` contract from D-03 and D-04.
    - Full answers keep the D-01 section order and labels; partial answers keep the same footprint with a limitation statement per D-05 and D-06.
    - Older runs that only have summary/takeaway data still synthesize a compatible narrative so history stays readable after rollout.
  </behavior>
  <action>Add a typed `narrativeAnswer` object to `PrimaryAnswerView` and `ChatAnswerCardView` while keeping existing summary, evidence, confidence, and navigation data available for secondary surfaces. In `buildPrimaryAnswerView`, consume `transparency.narrative_answer` first; when it is missing, synthesize a compatible narrative from the legacy summary/takeaway/caveat data rather than returning a blank or generic success state. Ensure the synthesized legacy path still separates thesis, support, and watchouts, and mark whether the source was `full`, `partial`, or legacy-derived so the renderer can stay deterministic. Update `run-primary-view.test.ts` to cover full preview, partial preview, and legacy-only runs.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` exports a `narrativeAnswer` field on the answer view with `full` and `partial` mode handling.
The file contains a legacy compatibility branch that synthesizes a narrative when `transparency.narrative_answer` is absent.
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts</automated>
  </verify>
  <done>The answer builder produces one narrative-first contract for new and old runs without dropping the existing secondary evidence metadata.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Reuse the narrative-first contract in live replies and hydrated history</name>
  <files>frontend/src/actions/runs.ts
frontend/src/lib/chat-run-history.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts</files>
  <read_first>.planning/ROADMAP.md
.planning/REQUIREMENTS.md
.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
frontend/src/actions/runs.ts
frontend/src/lib/chat-run-history.ts
frontend/src/lib/run-primary-view.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts</read_first>
  <behavior>
    - Newly executed runs and persisted chat history must emit the same narrative-first answer-card payload.
    - Successful partial answers use a thesis/limitation narrative string first, not the old `Analysis completed...` fallback.
    - Run ordering, run metadata, and unsupported-routing behavior stay unchanged.
  </behavior>
  <action>Update `createAnalysisRunFromChat` and `buildProjectChatHistory` so both paths derive their assistant `content` and `answerCard` from `narrativeAnswer` first. Use the thesis as the default plain-text content, append or prefer the limitation statement for `partial` mode, and reserve generic fallback copy for actual error states only. Keep the run-backed history ordering and run metadata exactly as Phase 14 established. Extend the action and hydration tests so they assert full narrative replies, partial limited-support replies, and legacy-history compatibility on the same contract.</action>
  <acceptance_criteria>`frontend/src/actions/runs.ts` and `frontend/src/lib/chat-run-history.ts` both derive reply content from the narrative-first answer contract before any generic success fallback.
Both test files assert narrative-first live and hydrated behavior.
`cd frontend && npm run test -- src/lib/chat-run-history.test.ts src/actions/runs.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/chat-run-history.test.ts src/actions/runs.test.ts</automated>
  </verify>
  <done>Live chat replies and hydrated history produce the same narrative-first assistant payload and stay readable for older runs.</done>
</task>

</tasks>

<verification>
Run the focused frontend data-path suite after both tasks:
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/actions/runs.test.ts`
</verification>

<success_criteria>
Chat data no longer depends on summary-line-first assembly. Both live and hydrated answers flow through the backend narrative preview when present and fall back to a stable synthesized narrative when older runs lack the new contract.
</success_criteria>

<output>
After completion, create `.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-02-SUMMARY.md`
</output>
