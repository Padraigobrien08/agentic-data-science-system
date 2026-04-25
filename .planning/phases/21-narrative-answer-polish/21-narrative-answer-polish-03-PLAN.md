---
phase: 21-narrative-answer-polish
plan: 03
type: execute
wave: 3
depends_on:
  - 21-narrative-answer-polish-02-PLAN.md
files_modified:
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/trace/run-trace-summary-view.tsx
  - frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
  - frontend/src/components/trace/run-trace-summary-view.test.tsx
  - .planning/PROJECT.md
autonomous: true
requirements:
  - EVID-03
  - CHRT-03
must_haves:
  truths:
    - "Trace is clearly framed as the technical deep-dive and audit surface, not a competing answer-reading page."
    - "Chat remains the primary answer surface in both wording and navigation."
    - "The final phase closes with regression coverage and build safety for the full polished answer experience."
  artifacts:
    - path: frontend/src/components/trace/run-trace-summary-view.tsx
      provides: "Final trace wording and navigation alignment"
    - path: frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
      provides: "Trace page framing aligned to the narrative-first chat product"
    - path: frontend/src/components/trace/run-trace-summary-view.test.tsx
      provides: "Regression coverage for technical-surface copy and navigation intent"
  key_links:
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/trace/run-trace-summary-view.tsx
      via: "Chat-to-trace language now reinforces answer versus audit roles"
      pattern: "trace|technical|chat"
    - from: frontend/src/components/trace/run-trace-summary-view.tsx
      to: frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
      via: "Trace page framing and summary copy stay consistent"
      pattern: "technical deep dive|Back to chat|inspect"
---

<objective>
Align the remaining chat/trace wording and navigation so the milestone finishes with one coherent answer-reading model and one clearly technical deep-dive surface.

Purpose: close the milestone with final language alignment, trace framing, and full frontend regression/build hardening.
Output: trace wording that reinforces its technical role, final polished navigation copy, updated milestone/project tracking, and green build/test coverage.
</objective>

<context>
@.planning/phases/21-narrative-answer-polish/21-CONTEXT.md
@.planning/phases/21-narrative-answer-polish/21-RESEARCH.md
@.planning/phases/21-narrative-answer-polish/21-UI-SPEC.md
@.planning/phases/21-narrative-answer-polish/21-VALIDATION.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/trace/run-trace-summary-view.tsx
@frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
@frontend/src/components/trace/run-trace-summary-view.test.tsx
@.planning/PROJECT.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Finish trace framing and milestone-closeout polish</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/trace/run-trace-summary-view.tsx
frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
frontend/src/components/trace/run-trace-summary-view.test.tsx
.planning/PROJECT.md</files>
  <action>Refine the remaining wording and navigation so chat clearly reads as the answer surface and trace clearly reads as the technical deep dive. Adjust copy, helper text, and action labels where needed, update trace-focused tests, run the full frontend regression/build gate, and then update `.planning/PROJECT.md` to reflect that the narrative-first answer experience has shipped coherently across narrative answer, confidence, evidence, charts, and technical inspection.</action>
  <acceptance_criteria>`frontend/src/components/trace/run-trace-summary-view.tsx` contains final technical-surface wording.
`frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` is aligned with the final trace framing.
`frontend/src/components/trace/run-trace-summary-view.test.tsx` is updated for the final wording/navigation intent.
`.planning/PROJECT.md` is updated for Phase 21 completion.
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx src/components/trace/run-trace-summary-view.test.tsx && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx src/components/trace/run-trace-summary-view.test.tsx && npm run build</automated>
  </verify>
  <done>The milestone finishes with one coherent answer-reading experience and a clearly technical trace surface.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx src/components/trace/run-trace-summary-view.test.tsx && npm run build` after the task lands.
</verification>

<success_criteria>
Phase 21 Wave 3 is complete when chat/trace wording is aligned, the full polished answer experience is build-safe, and project tracking reflects the shipped milestone state.
</success_criteria>

<output>
After completion, create `.planning/phases/21-narrative-answer-polish/21-narrative-answer-polish-03-SUMMARY.md`
</output>
