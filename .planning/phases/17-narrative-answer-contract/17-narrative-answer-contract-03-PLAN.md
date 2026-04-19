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
    - "Completed assistant replies read as one centered narrative answer with thesis, prose sections, and a short limitation rider."
    - "Supporting UI remains visually subordinate beneath the prose and partial answers do not look blank or boilerplate."
    - "Pending and unsupported-routing states still render correctly in the same transcript after the narrative card replaces the old summary-card feel."
  artifacts:
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Narrative-first chat renderer with a centered prose hierarchy."
    - path: frontend/src/components/chat-shell/chat-message-list.tsx
      provides: "Transcript host that centers the answer card while preserving pending and unsupported branches."
    - path: frontend/src/components/chat-shell/chat-message-list.test.tsx
      provides: "Rendering coverage for full, partial, pending, and unsupported assistant states."
  key_links:
    - "frontend/src/components/chat-shell/chat-message-list.tsx passes the narrative-first answer card into `ChatRunAnswerCard` without altering the pending and unsupported branches."
    - "frontend/src/components/chat-shell/chat-shell.test.tsx validates that hydrated history still renders inside the single-thread shell after the answer body becomes narrative-first."
---

<objective>
Render the new narrative answer contract as the primary reading surface in chat and lock the final frontend gate.

Purpose: satisfy the visible UX portion of `ANSR-01` and the no-boilerplate fallback requirement in `ANSR-02` without leaking Phase 18-20 work into this phase.
Output: a centered narrative-first chat answer card, subordinate support chrome, and a green frontend regression/build gate.
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
@.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace the summary-card layout with a centered narrative answer body</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/ROADMAP.md
.planning/REQUIREMENTS.md
.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - The assistant answer follows D-01 and the UI spec: quiet `Answer` label, thesis, `What’s happening`, `Why we think that`, and `What weakens the claim`, plus an optional limitation rider.
    - The main answer sits in one centered reading column instead of the current summary header plus two-column utility grid.
    - Existing findings, confidence/caveat, and evidence-navigation surfaces remain available only as subordinate blocks below the prose, and Phase 18-20 features stay out.
  </behavior>
  <action>Rebuild `ChatRunAnswerCard` around `answerCard.narrativeAnswer` so the completed assistant reply renders as one centered narrative column with the exact D-01 section labels and the analyst-memo tone from D-07. Remove the dominant two-column split from the main answer body, keep any retained support surfaces below the prose with lower contrast and smaller headings, and preserve the existing pending and unsupported branches in `chat-message-list.tsx`. Update the rendering test to assert the narrative section labels, thesis-first body, explicit limited-support copy for `partial` mode, and the continued absence of legacy footer-link sprawl.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `What’s happening`, `Why we think that`, and `What weakens the claim`.
The main answer-card layout no longer uses the current `lg:grid-cols-[minmax(0,1.55fr)_minmax(18rem,0.95fr)]` split.
`frontend/src/components/chat-shell/chat-message-list.tsx` still contains explicit pending and unsupported-routing branches.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>The chat answer reads like one narrative reply first, with supporting UI visibly stepped back below it.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Lock narrative rendering compatibility and the final frontend gate</name>
  <files>frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx</files>
  <read_first>.planning/ROADMAP.md
.planning/REQUIREMENTS.md
.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx</read_first>
  <behavior>
    - Hydrated history, full narratives, partial narratives, pending states, and unsupported-routing replies must all coexist in the single-thread chat shell.
    - The plan closes only when the focused renderer tests and the production frontend build are green.
  </behavior>
  <action>Extend `chat-message-list.test.tsx` and `chat-shell.test.tsx` so they cover full-mode narrative cards, `partial` limited-support cards, and hydrated history inside the existing one-thread shell without regressing pending or unsupported-routing behavior. Run the Phase 17 frontend gate exactly as documented in `17-VALIDATION.md`, including `npm run build`, before marking the plan complete.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-message-list.test.tsx` includes assertions for a `partial` narrative answer and hydrated full narrative sections.
`frontend/src/components/chat-shell/chat-shell.test.tsx` still verifies one-thread hydrated history behavior after the renderer change.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build</automated>
  </verify>
  <done>The narrative-first chat UI is regression-locked and build-clean, with no fallback backslide into blank or boilerplate successful replies.</done>
</task>

</tasks>

<verification>
Run the documented full frontend gate before closing the plan:
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build`
</verification>

<success_criteria>
The chat answer now reads like a substantive analyst reply instead of a summary card, and successful limited-support runs still render as deliberate partial answers rather than vague placeholders.
</success_criteria>

<output>
After completion, create `.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-03-SUMMARY.md`
</output>
