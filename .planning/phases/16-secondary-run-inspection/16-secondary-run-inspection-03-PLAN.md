---
phase: 16-secondary-run-inspection
plan: 03
type: execute
wave: 3
depends_on:
  - 01
  - 02
files_modified:
  - frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
  - frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
  - frontend/src/components/runs/run-inspection-panel.test.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
autonomous: true
requirements:
  - NAV-03
must_haves:
  truths:
    - "The run page and trace page copy now reinforce that chat is the primary answer surface and the run page is secondary inspection."
    - "Focused regressions lock the run-page role change without regressing the chat-first answer model."
    - "The phase closes with a green frontend build."
  artifacts:
    - path: frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
      provides: "Final run-page copy and action hierarchy"
    - path: frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
      provides: "Trace-page copy aligned to the new secondary run-page role"
    - path: frontend/src/components/runs/run-inspection-panel.test.tsx
      provides: "Final regression coverage for the inspection surface"
---

<objective>
Lock the final run-page role change with copy cleanup, regressions, and build verification.

Purpose: close `NAV-03` and the v1.2 milestone product goal.
Output: aligned page copy, focused tests, and green production build.
</objective>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Align copy and close the phase with the frontend gate</name>
  <files>frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx</files>
  <read_first>.planning/phases/16-secondary-run-inspection/16-VALIDATION.md
frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx</read_first>
  <behavior>
    - Page copy must reinforce the chat-first answer model.
    - The run page role change must not regress the chat-first transcript behavior.
    - The phase closes only with the frontend build green.
  </behavior>
  <action>Finish any remaining copy cleanup on the run page and trace page so the hierarchy is explicit: chat is primary answer reading, run page is secondary inspection, trace is deep dive. Extend the focused tests as needed, then run `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build`.</action>
  <acceptance_criteria>Run-page and trace-page copy align to the chat-first answer model.
Focused frontend tests cover the inspection surface.
`cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build</automated>
  </verify>
  <done>Phase 16 closes with the standalone run page clearly reduced to a secondary inspection surface.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` after the task lands.
</verification>
