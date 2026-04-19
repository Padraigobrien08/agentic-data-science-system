---
phase: 15-evidence-navigation-in-chat
plan: 03
type: execute
wave: 3
depends_on:
  - 01
  - 02
files_modified:
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/structured-answer/top-findings-list.tsx
  - frontend/src/components/structured-answer/finding-cards.tsx
  - frontend/src/components/structured-answer/caveat-badge-group.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
  - frontend/src/actions/runs.test.ts
autonomous: true
requirements:
  - NAV-02
must_haves:
  truths:
    - "Finding-level and caveat-level exact jumps remain available, but as secondary verification affordances instead of the primary reading pattern."
    - "The richer Phase 15 chat card preserves the one-thread, in-place upgrade behavior introduced in Phase 14."
    - "Production build verification closes the phase after the richer answer contract and exact-jump behavior are both locked."
  artifacts:
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Exact-jump hrefs for findings and caveat/context overflow"
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Secondary exact-jump affordances attached to findings and caveats"
    - path: frontend/src/components/chat-shell/chat-message-list.test.tsx
      provides: "Regression coverage for compact nav plus exact-jump behavior"
    - path: frontend/src/components/chat-shell/chat-shell.test.tsx
      provides: "Regression coverage for one-thread behavior after the richer card lands"
  key_links:
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/structured-answer/top-findings-list.tsx
      via: "Finding rows receive exact target hrefs without reintroducing the old repeated chip clutter"
      pattern: "chips|href|tracePath"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/caveat-badge-group.tsx
      via: "Caveat overflow and exact jumps still route into the correct verification surface"
      pattern: "overflowHref|trace|artifact"
---

<objective>
Finish the Phase 15 contract with exact finding/caveat jumps and regression hardening.

Purpose: satisfy `NAV-02` while locking the richer chat answer against regressions in transcript continuity and build behavior.
Output: exact-jump affordances, focused regressions, and green production build verification.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md
@.planning/phases/15-evidence-navigation-in-chat/15-RESEARCH.md
@.planning/phases/15-evidence-navigation-in-chat/15-UI-SPEC.md
@.planning/phases/15-evidence-navigation-in-chat/15-VALIDATION.md
@.planning/phases/15-evidence-navigation-in-chat/15-evidence-navigation-in-chat-01-PLAN.md
@.planning/phases/15-evidence-navigation-in-chat/15-evidence-navigation-in-chat-02-PLAN.md
@frontend/src/lib/run-primary-view.ts
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/structured-answer/top-findings-list.tsx
@frontend/src/components/structured-answer/finding-cards.tsx
@frontend/src/components/structured-answer/caveat-badge-group.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/actions/runs.test.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add quiet exact-jump affordances for findings and caveats</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/structured-answer/top-findings-list.tsx
frontend/src/components/structured-answer/finding-cards.tsx
frontend/src/components/structured-answer/caveat-badge-group.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md
.planning/phases/15-evidence-navigation-in-chat/15-UI-SPEC.md
frontend/src/lib/run-primary-view.ts
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/structured-answer/top-findings-list.tsx
frontend/src/components/structured-answer/finding-cards.tsx
frontend/src/components/structured-answer/caveat-badge-group.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - Exact artifact or trace jumps must exist for deeper verification.
    - Those exact jumps must be secondary affordances, not the dominant navigation pattern.
    - Caveat overflow must still route to the right verification target.
  </behavior>
  <action>Extend the answer-view derivation and the reused structured-answer components so finding rows and caveat sections can expose quiet secondary exact-jump affordances. Favor one small inline link or quiet action per row over restoring the old repeated chip farm. Keep compact primary navigation intact. Update the message-list tests so a completed rich answer asserts exact-jump affordances and target hrefs while preserving the compact nav labels.</action>
  <acceptance_criteria>The richer answer contract includes exact-jump hrefs for findings and caveats where available.
The chat card exposes those exact jumps as secondary affordances.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` asserts exact-jump behavior and expected hrefs.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>Users can jump from a finding or caveat in chat to the exact verification surface without reintroducing fragmented navigation.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Harden transcript continuity and close the phase with the full frontend gate</name>
  <files>frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/actions/runs.test.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/15-evidence-navigation-in-chat/15-VALIDATION.md
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/actions/runs.test.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - The richer Phase 15 card must not break one-thread persisted history or pending-to-final upgrades.
    - Tests must lock the richer answer contract and exact-jump behavior together.
    - The phase closes only with a green frontend build.
  </behavior>
  <action>Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` so the richer assistant answer still upgrades in place after a new prompt and continues the same visible thread. Extend `frontend/src/actions/runs.test.ts` so the richer answer-card data and run linkage fields remain present together. Finish by running the full Phase 15 frontend gate: `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build`.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-shell.test.tsx` covers one-thread continuity with the richer answer card.
`frontend/src/actions/runs.test.ts` keeps the richer answer-card data plus run linkage fields.
`cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build</automated>
  </verify>
  <done>Phase 15 closes with exact-jump behavior locked and the richer chat card verified end to end.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` after both tasks land.
</verification>

<success_criteria>
Phase 15 is complete once chat exposes inline findings, confidence/caveats, one compact navigation surface, and exact-jump affordances without breaking transcript continuity or build health.
</success_criteria>

<output>
After completion, create `.planning/phases/15-evidence-navigation-in-chat/15-evidence-navigation-in-chat-03-SUMMARY.md`
</output>
