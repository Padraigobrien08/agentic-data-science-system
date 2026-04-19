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
    - "The frontend answer builder prefers the new `narrative_answer` preview over `summaryLine` while preserving readable legacy behavior for older runs."
    - "Live chat replies and persisted history hydration both consume the same narrative-first answer contract."
    - "Generic success placeholders no longer dominate the primary chat answer path when narrative or partial-answer data exists."
  artifacts:
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Narrative-first answer-view derivation with explicit full, partial, and legacy modes"
    - path: frontend/src/actions/runs.ts
      provides: "Live chat reply path that returns the narrative-first answer contract for newly completed runs"
    - path: frontend/src/lib/chat-run-history.ts
      provides: "Persisted-run transcript hydration that stays compatible with both new and legacy answer shapes"
  key_links:
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/lib/api/types.ts
      via: "The answer builder consumes `transparency.narrative_answer` first and only falls back to summary-era fields when needed"
      pattern: "narrative_answer|mode|fallbackReason|legacy"
    - from: frontend/src/actions/runs.ts
      to: frontend/src/lib/run-primary-view.ts
      via: "Live chat replies reuse the same narrative-first builder as persisted history and the chat card"
      pattern: "buildPrimaryAnswerView|buildChatAnswerCardView|narrativeAnswer"
    - from: frontend/src/lib/chat-run-history.ts
      to: frontend/src/actions/runs.ts
      via: "Hydrated history and newly executed runs share the same narrative-first assistant payload shape"
      pattern: "answerCard|narrativeAnswer|fallbackReason"
---

<objective>
Refactor the answer-view derivation and chat data paths so the narrative preview becomes the primary answer contract without breaking persisted history or older runs.

Purpose: satisfy the migration half of `ANSR-01` and `ANSR-02` by making live replies and hydrated history narrative-first while preserving legacy compatibility.
Output: narrative-first view models, updated live reply/history paths, and regression coverage around compatibility and fallback states.
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
@.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
@.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
@.planning/phases/17-narrative-answer-contract/17-VALIDATION.md
@.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
@.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-01-PLAN.md
@frontend/src/lib/api/types.ts
@frontend/src/lib/run-primary-view.ts
@frontend/src/actions/runs.ts
@frontend/src/lib/chat-run-history.ts
@frontend/src/lib/__tests__/run-primary-view.test.ts
@frontend/src/actions/runs.test.ts
@frontend/src/lib/chat-run-history.test.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Make the answer-view builder narrative-first with explicit compatibility modes</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</files>
  <read_first>.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
frontend/src/lib/api/types.ts
frontend/src/lib/run-primary-view.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</read_first>
  <behavior>
    - The primary answer view must prefer `transparency.narrative_answer` whenever it exists.
    - The answer builder must preserve an explicit compatibility path for older runs that do not yet carry the new preview.
    - Full, partial, and legacy answer modes must remain inspectable in tests instead of being hidden behind ad hoc strings.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add exact exported types `NarrativeAnswerSectionView` and `NarrativeAnswerView`. `NarrativeAnswerView` must expose exact keys `mode`, `thesis`, `sections`, and `fallbackReason`, where `mode` is the exact union `\"full\" | \"partial\" | \"legacy\"`. Extend `PrimaryAnswerView` and `ChatAnswerCardView` with a required `narrativeAnswer` field of that type. Update `buildPrimaryAnswerView(...)` so it reads `input.transparency?.narrative_answer` first. When a typed preview exists, map it into `narrativeAnswer` directly and stop using `summaryLine` as the primary thesis source. When the preview is absent, create a `legacy` narrative answer using the current summary/takeaway compatibility logic: use the best available `summaryLine` or first takeaway as `thesis`, create at most one compatibility section from the strongest remaining takeaway or empty-state reason, and set `fallbackReason` to the exact string `legacy_summary`. Keep `summaryLine` for migration compatibility, but no downstream caller in this phase should treat it as the primary answer contract. Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` with exact coverage for three cases: `full` preview, `partial` preview with explicit `fallbackReason`, and `legacy` fallback when only summary-era fields exist.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains `export type NarrativeAnswerView`.
`frontend/src/lib/run-primary-view.ts` contains `export type NarrativeAnswerSectionView`.
`frontend/src/lib/run-primary-view.ts` contains `mode: "full" | "partial" | "legacy"` or equivalent type union.
`frontend/src/lib/run-primary-view.ts` contains `narrativeAnswer`.
`frontend/src/lib/run-primary-view.ts` contains `legacy_summary`.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains `full`.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains `partial`.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains `legacy_summary`.
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts</automated>
  </verify>
  <done>The answer-view builder now exposes a stable narrative-first contract with explicit compatibility modes instead of centering `summaryLine`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Move live replies and persisted history onto the narrative-first answer contract</name>
  <files>frontend/src/actions/runs.ts
frontend/src/lib/chat-run-history.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts</files>
  <read_first>.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-01-PLAN.md
frontend/src/actions/runs.ts
frontend/src/lib/chat-run-history.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - Newly completed chat runs and hydrated persisted runs must surface the same narrative-first answer data.
    - Fallback copy in live replies and history hydration must reflect the explicit narrative mode instead of generic summary strings.
    - History compatibility must remain intact for older runs that still only expose summary-era fields.
  </behavior>
  <action>In `frontend/src/actions/runs.ts`, update the supported-run reply path so the text `content` and `answerCard` are derived from `answerCard.narrativeAnswer`, not from `summaryLine ?? emptyStateReason`. Use `narrativeAnswer.thesis` as the fallback plain-text content for structured messages and keep unsupported rewrite-guidance unchanged. In `frontend/src/lib/chat-run-history.ts`, update hydrated assistant messages to use the same `narrativeAnswer`-first behavior, preserving `legacy` mode when older runs have no backend preview. Do not remove `summaryLine` from the wire in this phase; only stop treating it as the main answer source. Extend `frontend/src/actions/runs.test.ts` and `frontend/src/lib/chat-run-history.test.ts` so one case asserts a `full` narrative preview populates the assistant content with the narrative thesis, another asserts a `partial` preview preserves its `fallbackReason`, and a legacy run still hydrates with `mode: "legacy"` rather than collapsing into generic placeholder text.</action>
  <acceptance_criteria>`frontend/src/actions/runs.ts` contains `narrativeAnswer`.
`frontend/src/actions/runs.ts` contains `narrativeAnswer.thesis`.
`frontend/src/lib/chat-run-history.ts` contains `narrativeAnswer`.
`frontend/src/lib/chat-run-history.ts` contains `legacy_summary`.
`frontend/src/actions/runs.test.ts` contains `fallbackReason`.
`frontend/src/actions/runs.test.ts` contains `narrativeAnswer`.
`frontend/src/lib/chat-run-history.test.ts` contains `mode: "legacy"` or `legacy`.
`frontend/src/lib/chat-run-history.test.ts` contains `partial`.
`cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts</automated>
  </verify>
  <done>Live chat replies and persisted history now share the same narrative-first answer contract, including explicit partial and legacy fallback modes.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/actions/runs.test.ts src/lib/chat-run-history.test.ts` after both tasks land.
</verification>

<success_criteria>
Phase 17 has a sound second wave once the frontend answer builder prefers the backend narrative preview, live replies and persisted history share the same narrative-first contract, and older runs remain readable through an explicit legacy mode.
</success_criteria>

<output>
After completion, create `.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-02-SUMMARY.md`
</output>
