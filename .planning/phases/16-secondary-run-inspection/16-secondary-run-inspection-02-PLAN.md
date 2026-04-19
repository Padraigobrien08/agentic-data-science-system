---
phase: 16-secondary-run-inspection
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - frontend/src/components/runs/run-primary-answer.tsx
  - frontend/src/components/runs/run-inspection-panel.tsx
  - frontend/src/components/runs/verify-analysis-section.tsx
  - frontend/src/components/runs/outcome-suggestions-panel.tsx
  - frontend/src/components/runs/run-inspection-panel.test.tsx
autonomous: true
requirements:
  - NAV-03
must_haves:
  truths:
    - "Duplicated answer-reading sections are removed or compressed from the run page."
    - "Verification-oriented sections remain available."
    - "Outcome suggestions stay only when they materially help partial or degraded runs."
  artifacts:
    - path: frontend/src/components/runs/run-primary-answer.tsx
      provides: "Reduced or retired duplicate primary-answer composition on the run page"
    - path: frontend/src/components/runs/run-inspection-panel.tsx
      provides: "Inspection-focused body that keeps verification and follow-up controls"
    - path: frontend/src/components/runs/run-inspection-panel.test.tsx
      provides: "Coverage for absence of duplicated reading sections"
---

<objective>
Remove the duplicated reading stack from the run page while preserving verification value.

Purpose: satisfy the reduction half of `NAV-03`.
Output: a slimmer inspection body with verification, rerun, and trace access but without the chat-owned answer-reading sections.
</objective>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Remove or compress duplicated answer-reading sections</name>
  <files>frontend/src/components/runs/run-primary-answer.tsx
frontend/src/components/runs/run-inspection-panel.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx</files>
  <read_first>.planning/phases/16-secondary-run-inspection/16-CONTEXT.md
.planning/phases/16-secondary-run-inspection/16-UI-SPEC.md
frontend/src/components/runs/run-primary-answer.tsx
frontend/src/components/runs/run-inspection-panel.tsx</read_first>
  <behavior>
    - The run page should not render full top findings, confidence/caveats, evidence, and next-step reading sections anymore.
    - Verification-oriented content remains.
    - The page should still feel useful when opened directly from outside chat.
  </behavior>
  <action>Trim or retire `RunPrimaryAnswer` from the run-page flow so the standalone page no longer duplicates the full answer-reading stack now present in chat. Keep or move the verification strip, selective outcome suggestions, and compact inspection actions into the inspection panel. Update the new component test so it asserts the absence of duplicated reading sections and the presence of inspection-focused content.</action>
  <acceptance_criteria>The standalone run page no longer renders full duplicated findings/confidence/evidence reading sections.
Verification-oriented content remains present.
`cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx</automated>
  </verify>
  <done>The standalone run page is visibly reduced to inspection-oriented content.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx` after the task lands.
</verification>
