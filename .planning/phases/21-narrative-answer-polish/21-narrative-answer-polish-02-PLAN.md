---
phase: 21-narrative-answer-polish
plan: 02
type: execute
wave: 2
depends_on:
  - 21-narrative-answer-polish-01-PLAN.md
files_modified:
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/structured-answer/inline-evidence-charts.tsx
  - frontend/src/components/structured-answer/supplemental-evidence-disclosure.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
  - frontend/src/components/runs/run-inspection-panel.test.tsx
autonomous: true
requirements:
  - CONF-01
  - EVID-01
  - CHRT-01
must_haves:
  truths:
    - "The same answer hierarchy survives on desktop and smaller screens: prose first, charts second, supplemental evidence third."
    - "Responsive tuning uses one layout model rather than separate desktop/mobile product ideas."
    - "Charts, disclosure, and secondary surfaces stay subordinate to the answer."
  artifacts:
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Responsive answer-shell composition"
    - path: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      provides: "Responsive chart stacking and spacing polish"
    - path: frontend/src/components/structured-answer/supplemental-evidence-disclosure.tsx
      provides: "Responsive disclosure behavior aligned to the final answer shell"
  key_links:
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      via: "Charts remain between prose and disclosure across breakpoints"
      pattern: "InlineEvidenceCharts|supplemental evidence"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/supplemental-evidence-disclosure.tsx
      via: "Disclosure stays below charts and remains secondary"
      pattern: "Collapsible|Show supporting evidence"
---

<objective>
Tune the final answer architecture so it works cleanly across common screen sizes without reintroducing split reading regions or cramped stacked blocks.

Purpose: satisfy the responsive polish goal while preserving the answer-first hierarchy already shipped in Phases 17-20.
Output: responsive answer-shell refinements across prose, charts, and disclosure, with regression coverage for the final composition.
</objective>

<context>
@.planning/phases/21-narrative-answer-polish/21-CONTEXT.md
@.planning/phases/21-narrative-answer-polish/21-RESEARCH.md
@.planning/phases/21-narrative-answer-polish/21-UI-SPEC.md
@.planning/phases/21-narrative-answer-polish/21-VALIDATION.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/structured-answer/inline-evidence-charts.tsx
@frontend/src/components/structured-answer/supplemental-evidence-disclosure.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/components/runs/run-inspection-panel.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Finish responsive composition for charts and supporting-evidence surfaces</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/structured-answer/inline-evidence-charts.tsx
frontend/src/components/structured-answer/supplemental-evidence-disclosure.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx</files>
  <action>Refine breakpoint behavior so the final answer shell relaxes cleanly from the centered desktop column to a near-full-width smaller-screen reading surface. Charts, disclosure rows, and secondary answer surfaces should stack cleanly, keep calm spacing, and avoid overflow-heavy or side-rail-like behavior. Update tests to lock the final composition and ensure the technical inspection surface remains secondary to the polished chat answer.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains final responsive answer-shell refinements.
`frontend/src/components/structured-answer/inline-evidence-charts.tsx` contains final chart responsive polish.
`frontend/src/components/chat-shell/chat-shell.test.tsx` is updated for the final composition.
`frontend/src/components/runs/run-inspection-panel.test.tsx` still passes after the responsive polish.
`cd frontend && npm run test -- src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx</automated>
  </verify>
  <done>The answer architecture now behaves cleanly across common screen sizes without giving up the answer-first hierarchy.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx` after the task lands.
</verification>

<success_criteria>
Phase 21 Wave 2 is complete when responsive behavior feels intentional and the answer still clearly dominates charts, disclosure, and technical inspection surfaces.
</success_criteria>

<output>
After completion, create `.planning/phases/21-narrative-answer-polish/21-narrative-answer-polish-02-SUMMARY.md`
</output>
