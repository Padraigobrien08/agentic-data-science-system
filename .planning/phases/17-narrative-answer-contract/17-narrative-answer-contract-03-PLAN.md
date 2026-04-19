---
phase: 17-narrative-answer-contract
plan: 03
type: execute
wave: 3
depends_on:
  - 02
files_modified:
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/chat-shell/chat-message-list.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
autonomous: true
requirements:
  - ANSR-01
  - ANSR-02
must_haves:
  truths:
    - "The chat answer renders as a centered narrative reading surface instead of a summary card with a dominant right rail."
    - "Full, partial, weak-support, and error states all use one coherent narrative-first shell instead of dropping back to vague placeholder copy."
    - "Any legacy findings or support blocks that remain in Phase 17 are visually subordinate to the prose body and sit below it rather than beside it."
  artifacts:
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Narrative-first chat renderer aligned to the approved Phase 17 UI contract"
    - path: frontend/src/components/chat-shell/chat-message-list.test.tsx
      provides: "Regression coverage for narrative, partial, and error rendering states"
    - path: frontend/src/components/chat-shell/chat-shell.test.tsx
      provides: "Transcript-level regression coverage that the narrative answer remains the primary visible surface"
  key_links:
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: .planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
      via: "The card follows the centered single-column narrative reading contract instead of the prior utility-grid layout"
      pattern: "Answer|What's happening|Why we think that|What weakens the claim|max-w-[54rem]"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/lib/run-primary-view.ts
      via: "Rendered prose comes from the typed `narrativeAnswer` contract, while legacy support blocks remain secondary compatibility surfaces"
      pattern: "narrativeAnswer|mode|fallbackReason|sections"
    - from: frontend/src/components/chat-shell/chat-message-list.test.tsx
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "Tests lock the narrative shell across full, partial, and error states so generic placeholder copy cannot regress into the main answer body"
      pattern: "This analysis didn’t finish cleanly.|What weakens the claim|limited evidence"
---

<objective>
Render the narrative-first answer in chat and harden the visible fallback states so the product reads like a substantive analyst reply instead of a summary-card system.

Purpose: satisfy the user-facing half of `ANSR-01` and `ANSR-02` by making the prose column the primary reading surface and removing vague placeholder behavior from the main answer path.
Output: centered narrative renderer, subordinate legacy support layout, and frontend regression/build coverage.
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
@.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-02-PLAN.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/lib/run-primary-view.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Refactor the chat answer card into a centered narrative reading surface</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - The assistant answer must render in one centered narrative column instead of the current main-column plus right-rail split.
    - The thesis and prose sections must appear before any compatibility findings, confidence, or evidence surfaces.
    - Any legacy support blocks that remain during Phase 17 must render below the prose and step back visually.
  </behavior>
  <action>In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, replace the current `lg:grid-cols-[minmax(0,1.55fr)_minmax(18rem,0.95fr)]` answer layout with one centered narrative column capped at an exact max width between `46rem` and `54rem`; use the exact class `max-w-[54rem]` for the card body. Render the primary answer in this exact order: quiet `Answer` eyebrow, thesis from `answerCard.narrativeAnswer.thesis`, then one block per `answerCard.narrativeAnswer.sections` row. Each section heading must render the exact text supplied by the narrative contract, including `What's happening`, `Why we think that`, and `What weakens the claim`. Keep any `conclusionRider` or fallback note below the prose body. If legacy findings, confidence, caveats, or evidence chips remain in Phase 17 for compatibility, move them into one subordinate vertical section below the prose, remove the right-rail presentation, and reduce their visual dominance with smaller labels and lower-contrast surfaces. Update `frontend/src/components/chat-shell/chat-message-list.tsx` only as needed to pass the narrative answer card the new primary narrative content. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` so one completed answer asserts the thesis plus all three narrative headings render in order, and a second test asserts the old two-column right-rail class is gone from the output.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `max-w-[54rem]`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain `lg:grid-cols-[minmax(0,1.55fr)_minmax(18rem,0.95fr)]`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `narrativeAnswer`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `What's happening`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Why we think that`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `What weakens the claim`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `What's happening`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Why we think that`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `What weakens the claim`.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>The primary chat answer now reads like one centered narrative reply instead of a summary-card grid with a dominant side rail.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Harden partial, weak-support, and error rendering in the narrative shell</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx</files>
  <read_first>.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - Partial and weak-support answers must keep the same narrative shell as full answers and explicitly name their limitation.
    - Error answers must never fall back to generic success or blank-card copy.
    - Pending answers may stay lightweight, but completed error and partial states must read as intentional product states rather than accidental emptiness.
  </behavior>
  <action>In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, add explicit branching on `answerCard.narrativeAnswer.mode` and on terminal error/no-data states so the main answer body never shows `Run completed without a summary line.` or similarly vague process text. For `partial` and weak-support cases, preserve the narrative shell and render the strongest supportable thesis plus a clear limitation line beneath it. For error cases, render the exact failure copy from the UI-SPEC: `This analysis didn’t finish cleanly.` followed by `Open trace to inspect what failed, then retry with narrower wording or refreshed SEC data.` Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` with a partial-answer test that asserts the limitation language is visible in the narrative shell, and extend `frontend/src/components/chat-shell/chat-shell.test.tsx` with an error-state rendering test that asserts the exact failure copy above is present. Finish by running the full Phase 17 frontend gate including `npm run build` to catch server/client contract regressions.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `This analysis didn’t finish cleanly.`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Open trace to inspect what failed`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain `Run completed without a summary line.`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `This analysis didn’t finish cleanly.`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains a partial-answer limitation assertion.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains `This analysis didn’t finish cleanly.`.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` passes.
`cd frontend && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build</automated>
  </verify>
  <done>All completed answer states now use the same narrative-first shell, with explicit partial and error behavior instead of vague placeholder prose.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` after both tasks land.
</verification>

<success_criteria>
Phase 17 has a valid final wave once the assistant answer renders as a centered narrative reply, legacy support blocks become subordinate, and partial/error states remain readable and intentional instead of placeholder-driven.
</success_criteria>

<output>
After completion, create `.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-03-SUMMARY.md`
</output>
