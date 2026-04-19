---
phase: 15-evidence-navigation-in-chat
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/actions/runs.ts
  - frontend/src/lib/chat-run-history.ts
  - frontend/src/components/chat-shell/types.ts
  - frontend/src/actions/runs.test.ts
  - frontend/src/lib/chat-run-history.test.ts
autonomous: true
requirements:
  - CHAT-02
  - NAV-01
must_haves:
  truths:
    - "Supported chat replies and hydrated run history use one richer answer-card contract that includes findings, confidence, caveats, and compact evidence navigation."
    - "The richer chat answer view is still derived from the existing `PrimaryAnswerView` path, not from a second chat-only semantics layer."
    - "Phase 15 data work stays bounded: it prepares inline reading and navigation, but does not simplify the standalone run page."
  artifacts:
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Rich chat answer view builder layered on top of PrimaryAnswerView"
    - path: frontend/src/actions/runs.ts
      provides: "Supported chat reply contract with rich answer-card data"
    - path: frontend/src/lib/chat-run-history.ts
      provides: "Hydrated persisted-run history using the same rich answer-card data"
    - path: frontend/src/actions/runs.test.ts
      provides: "Regression coverage for rich chat reply payloads"
  key_links:
    - from: frontend/src/actions/runs.ts
      to: frontend/src/lib/run-primary-view.ts
      via: "The server action hydrates the completed run and maps it into the richer Phase 15 chat answer view"
      pattern: "buildPrimaryAnswerView|build.*Chat.*Answer|getRun("
    - from: frontend/src/lib/chat-run-history.ts
      to: frontend/src/lib/run-primary-view.ts
      via: "Reloaded chat history uses the same richer answer-card contract as live chat replies"
      pattern: "buildPrimaryAnswerView|answerCard"
---

<objective>
Create the richer chat answer data contract needed for inline findings, confidence, caveats, and compact evidence navigation.

Purpose: satisfy the data-model half of `CHAT-02` and `NAV-01` so chat can render the full bounded answer-reading surface in later waves.
Output: a richer chat answer view, live reply payloads, hydrated history payloads, and focused action/history regression coverage.
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
@.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md
@.planning/phases/15-evidence-navigation-in-chat/15-RESEARCH.md
@.planning/phases/15-evidence-navigation-in-chat/15-UI-SPEC.md
@.planning/phases/15-evidence-navigation-in-chat/15-VALIDATION.md
@frontend/src/lib/run-primary-view.ts
@frontend/src/actions/runs.ts
@frontend/src/lib/chat-run-history.ts
@frontend/src/components/chat-shell/types.ts
@frontend/src/actions/runs.test.ts
@frontend/src/lib/chat-run-history.test.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend the chat answer-card view model from the existing primary-answer derivation seam</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/components/chat-shell/types.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts</files>
  <read_first>.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md
.planning/phases/15-evidence-navigation-in-chat/15-RESEARCH.md
.planning/phases/15-evidence-navigation-in-chat/15-UI-SPEC.md
frontend/src/lib/run-primary-view.ts
frontend/src/components/chat-shell/types.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts</read_first>
  <behavior>
    - The chat answer model must be richer than the Phase 14 compact subset.
    - The richer model must still come from `PrimaryAnswerView`.
    - The model must carry the data required for findings, confidence/caveats, and one compact nav area.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add a richer exported chat answer type and builder layered on top of `PrimaryAnswerView`. Include the conclusion and goal fields already used in Phase 14 plus bounded findings, confidence/caveat fields, and compact evidence-navigation data. Keep the builder deterministic and derived-only; do not duplicate parsing logic outside `buildPrimaryAnswerView(...)`. Extend `frontend/src/components/chat-shell/types.ts` so assistant messages can carry the richer answer-card shape. Update the existing tests so the richer answer payload is asserted rather than only the compact Phase 14 subset.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains an exported richer chat answer type.
`frontend/src/lib/run-primary-view.ts` contains an exported richer chat answer builder.
`frontend/src/lib/run-primary-view.ts` contains fields for takeaway rows, confidence/caveat data, and compact nav data.
`frontend/src/components/chat-shell/types.ts` reflects the richer answer-card contract.
`frontend/src/actions/runs.test.ts` asserts the richer answer-card payload.
`frontend/src/lib/chat-run-history.test.ts` asserts hydrated history uses the richer answer-card payload.
`cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts</automated>
  </verify>
  <done>The richer Phase 15 chat answer contract exists and is covered at the derivation seam.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Return the richer answer-card contract from live chat replies and hydrated history</name>
  <files>frontend/src/actions/runs.ts
frontend/src/lib/chat-run-history.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts</files>
  <read_first>.planning/phases/15-evidence-navigation-in-chat/15-RESEARCH.md
frontend/src/actions/runs.ts
frontend/src/lib/chat-run-history.ts
frontend/src/actions/runs.test.ts
frontend/src/lib/chat-run-history.test.ts
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - Supported chat execution returns the richer answer-card contract.
    - Reloaded persisted-run chat history returns the same richer answer-card contract.
    - Unsupported preview guidance remains its own branch.
  </behavior>
  <action>Update `frontend/src/actions/runs.ts` so the supported execution path returns the richer answer-card builder output. Update `frontend/src/lib/chat-run-history.ts` so hydrated persisted runs also use that same builder output. Keep the unsupported-guidance preview contract untouched. Extend the tests so both live reply and hydrated history flows assert the richer answer-card shape and continue to carry the Phase 14 run linkage fields.</action>
  <acceptance_criteria>`frontend/src/actions/runs.ts` returns the richer answer-card contract on supported runs.
`frontend/src/lib/chat-run-history.ts` maps hydrated runs to the richer answer-card contract.
Unsupported preview guidance behavior is unchanged.
`cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts</automated>
  </verify>
  <done>Both live chat replies and hydrated run history now share one Phase 15 answer contract.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts` after both tasks land.
</verification>

<success_criteria>
Phase 15 has a valid first wave once supported chat replies and hydrated run history both return one richer answer-card contract derived from `PrimaryAnswerView`.
</success_criteria>

<output>
After completion, create `.planning/phases/15-evidence-navigation-in-chat/15-evidence-navigation-in-chat-01-SUMMARY.md`
</output>
