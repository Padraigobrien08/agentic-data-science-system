---
phase: 16-secondary-run-inspection
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
  - frontend/src/components/runs/run-primary-answer.tsx
  - frontend/src/components/runs/run-inspection-panel.tsx
  - frontend/src/components/runs/run-inspection-panel.test.tsx
autonomous: true
requirements:
  - NAV-03
must_haves:
  truths:
    - "The standalone run page presents itself as an inspection surface, not a primary answer page."
    - "Users get an explicit return path to chat near the top of the run page."
    - "The new inspection composition reuses existing status and verification seams rather than inventing new run semantics."
  artifacts:
    - path: frontend/src/components/runs/run-inspection-panel.tsx
      provides: "Verification-first run-page composition"
    - path: frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
      provides: "Run page header and page-role framing aligned to secondary inspection"
    - path: frontend/src/components/runs/run-inspection-panel.test.tsx
      provides: "Coverage for the new inspection-first composition"
---

<objective>
Establish the verification-first run-page shell and explicit back-to-chat framing.

Purpose: satisfy the page-role half of `NAV-03` before removing duplicated answer-reading sections.
Output: a dedicated inspection composition, header copy that stops calling the page a primary summary, and focused component coverage.
</objective>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Introduce an inspection-first run-page composition</name>
  <files>frontend/src/components/runs/run-inspection-panel.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx
frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx</files>
  <read_first>.planning/phases/16-secondary-run-inspection/16-CONTEXT.md
.planning/phases/16-secondary-run-inspection/16-RESEARCH.md
.planning/phases/16-secondary-run-inspection/16-UI-SPEC.md
frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
frontend/src/components/runs/run-primary-answer.tsx
frontend/src/components/runs/verify-analysis-section.tsx</read_first>
  <behavior>
    - The run page must explicitly frame itself as inspection-first.
    - The page must include a clear return-to-chat action.
    - Existing status and verification seams remain intact.
  </behavior>
  <action>Create a dedicated inspection-oriented component for the run page and update the page header copy away from `Primary summary`. Add an explicit `Back to chat` action near the top. Keep the run state banner, phase track, and verify strip in the new composition. Add a component test that asserts the new verification framing and return-to-chat action.</action>
  <acceptance_criteria>The run page no longer calls itself `Primary summary`.
The run page exposes `Back to chat`.
The new inspection component renders the verification strip and keeps status context.
`cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx</automated>
  </verify>
  <done>The standalone run page now presents itself as a secondary inspection surface.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx` after the task lands.
</verification>
