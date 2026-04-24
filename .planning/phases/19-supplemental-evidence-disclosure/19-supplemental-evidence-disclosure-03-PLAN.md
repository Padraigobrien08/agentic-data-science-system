---
phase: 19-supplemental-evidence-disclosure
plan: 03
type: execute
wave: 3
depends_on:
  - 02
files_modified:
  - frontend/src/components/structured-answer/evidence-summary.tsx
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
autonomous: true
requirements:
  - ANSR-03
  - EVID-03
must_haves:
  truths:
    - "The five navigation pills remain available whether or not the disclosure is open."
    - "The pills are visually secondary to the answer and the opened evidence rows."
    - "The final answer composition preserves answer-first reading while keeping exact escape hatches easy to find."
  artifacts:
    - path: frontend/src/components/structured-answer/evidence-summary.tsx
      provides: "Secondary pill strip behavior and visual weight after the disclosure rollout"
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Final Phase 19 answer composition with disclosure above pills"
    - path: frontend/src/components/chat-shell/chat-shell.test.tsx
      provides: "Hydrated history and composition regressions for the final support hierarchy"
  key_links:
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/evidence-summary.tsx
      via: "The persistent navigation strip moves below the disclosure and stays secondary"
      pattern: "Report|Evidence|Artifacts|Critic|Trace"
    - from: frontend/src/components/chat-shell/chat-message-list.test.tsx
      to: frontend/src/components/chat-shell/chat-shell.test.tsx
      via: "Renderer tests lock pill persistence independent of disclosure state"
      pattern: "Show supporting evidence|Report|Evidence|Artifacts|Critic|Trace"
---

<objective>
Finish the Phase 19 answer hierarchy by keeping the five navigation pills always available below the disclosure while making them clearly secondary.

Purpose: satisfy `EVID-03` and complete the answer-first hierarchy in `ANSR-03` by positioning the navigation strip beneath the supplemental-evidence disclosure and hardening the final chat composition.
Output: final evidence-summary placement, secondary pill treatment, renderer regressions, and build verification.
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
@.planning/phases/19-supplemental-evidence-disclosure/19-CONTEXT.md
@.planning/phases/19-supplemental-evidence-disclosure/19-RESEARCH.md
@.planning/phases/19-supplemental-evidence-disclosure/19-VALIDATION.md
@.planning/phases/19-supplemental-evidence-disclosure/19-UI-SPEC.md
@.planning/phases/19-supplemental-evidence-disclosure/19-supplemental-evidence-disclosure-02-PLAN.md
@frontend/src/components/structured-answer/evidence-summary.tsx
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reposition the navigation pills below the disclosure and reduce their visual weight</name>
  <files>frontend/src/components/structured-answer/evidence-summary.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/19-supplemental-evidence-disclosure/19-UI-SPEC.md
frontend/src/components/structured-answer/evidence-summary.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - The `Report / Evidence / Artifacts / Critic / Trace` pills must stay visible even when the disclosure is closed.
    - The pills must sit below the disclosure instead of inside it.
    - The pills must read as secondary navigation rather than as another evidence-content section.
  </behavior>
  <action>In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, place the persistent navigation strip below the supplemental-evidence disclosure and outside its open/closed content region. In `frontend/src/components/structured-answer/evidence-summary.tsx`, reduce the visual weight of the pill strip so it reads as neutral navigation rather than another card-heavy content block; preserve provenance hints and exact destinations, but keep the pills compact and visually quieter than the evidence rows. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` so it proves the five pills remain visible when the disclosure is closed.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` renders the navigation strip below the disclosure.
`frontend/src/components/structured-answer/evidence-summary.tsx` still contains `Report`, `Evidence`, `Artifacts`, `Critic`, and `Trace` destinations or equivalent mapped labels.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains assertions that the pills are visible with the disclosure closed.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>The answer now ends with one quiet navigation strip beneath the disclosure rather than mixing pills into the evidence content.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Harden the final Phase 19 composition across hydrated history and build output</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/19-supplemental-evidence-disclosure/19-CONTEXT.md
.planning/phases/19-supplemental-evidence-disclosure/19-VALIDATION.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - Hydrated past runs and live chat answers must both render the same answer-first hierarchy.
    - The final Phase 19 composition must keep the narrative answer central, the disclosure optional, and the pills secondary.
    - The frontend build must remain green after the hierarchy change.
  </behavior>
  <action>In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, remove any leftover composition branches that could reintroduce always-visible support content or place the pill strip above the disclosure. Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` so hydrated history answers preserve the same closed-by-default disclosure and persistent-pill arrangement. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` with one regression assertion that the final composition order is answer body, disclosure, then secondary pills. Finish by running the full Phase 19 frontend gate including `npm run build`.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-shell.test.tsx` contains hydrated-history coverage for the supplemental evidence disclosure.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains a regression assertion for the final composition order.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` passes.
`cd frontend && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build</automated>
  </verify>
  <done>The final Phase 19 answer hierarchy is stable for both live and hydrated chat answers and is ready for execution without reintroducing evidence-first layout drift.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` after both tasks land.
</verification>

<success_criteria>
Phase 19 has a valid final wave once the persistent navigation pills stay below the disclosure, remain visibly secondary, and the full chat answer composition is stable across hydrated history and build output.
</success_criteria>

<output>
After completion, create `.planning/phases/19-supplemental-evidence-disclosure/19-supplemental-evidence-disclosure-03-SUMMARY.md`
</output>
