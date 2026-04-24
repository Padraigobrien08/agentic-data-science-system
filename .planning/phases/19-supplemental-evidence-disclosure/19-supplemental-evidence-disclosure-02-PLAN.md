---
phase: 19-supplemental-evidence-disclosure
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - frontend/src/components/ui/collapsible.tsx
  - frontend/src/components/structured-answer/supplemental-evidence-row.tsx
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
autonomous: true
requirements:
  - ANSR-03
  - EVID-01
  - EVID-02
must_haves:
  truths:
    - "The narrative answer remains the default reading path because supporting evidence is collapsed by default."
    - "Opening supporting evidence reveals one slim, merged evidence list instead of separate takeaway and alignment sections."
    - "Thin or empty evidence still opens to an explicit explanatory state rather than disappearing."
  artifacts:
    - path: frontend/src/components/ui/collapsible.tsx
      provides: "shadcn-style disclosure primitive for the supplemental evidence layer"
    - path: frontend/src/components/structured-answer/supplemental-evidence-row.tsx
      provides: "Long, slim support-row renderer with exact jump link"
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Collapsed-by-default supplemental evidence disclosure beneath the answer"
  key_links:
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/structured-answer/supplemental-evidence-row.tsx
      via: "The merged evidence-row contract becomes the single support renderer"
      pattern: "title|reason|jump"
    - from: frontend/src/components/ui/collapsible.tsx
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "Supporting evidence opens locally under the answer instead of remaining permanently visible"
      pattern: "Collapsible|Show supporting evidence|Hide supporting evidence"
    - from: frontend/src/components/chat-shell/chat-message-list.test.tsx
      to: frontend/src/components/chat-shell/chat-shell.test.tsx
      via: "Renderer tests lock collapsed-by-default behavior and the limited-evidence disclosure state"
      pattern: "Show supporting evidence|Hide supporting evidence|Supporting evidence is limited"
---

<objective>
Render the supplemental evidence disclosure in the chat answer and make the merged support rows feel light, horizontal, and clearly secondary to the narrative answer.

Purpose: satisfy the visible UI behavior in `ANSR-03`, `EVID-01`, and `EVID-02` by collapsing support behind one disclosure and replacing the current stacked support cards with one slim row renderer.
Output: disclosure primitive, slim supplemental-evidence rows, collapsed-by-default chat rendering, and renderer regression coverage.
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
@.planning/phases/19-supplemental-evidence-disclosure/19-supplemental-evidence-disclosure-01-PLAN.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/structured-answer/top-findings-list.tsx
@frontend/src/components/structured-answer/finding-cards.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add the disclosure primitive and slim supplemental evidence row component</name>
  <files>frontend/src/components/ui/collapsible.tsx
frontend/src/components/structured-answer/supplemental-evidence-row.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/19-supplemental-evidence-disclosure/19-UI-SPEC.md
frontend/src/components/structured-answer/top-findings-list.tsx
frontend/src/components/structured-answer/finding-cards.tsx
frontend/src/components/structured-answer/types.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - The disclosure primitive must follow the local shadcn style used elsewhere in the repo.
    - Evidence rows must be horizontally wide, vertically thin, and lighter than the old support cards.
    - Each row must preserve one exact source jump.
  </behavior>
  <action>In `frontend/src/components/ui/`, add a local shadcn-style `collapsible.tsx` primitive if one does not already exist, following the repo’s Radix-backed composition pattern. Add a new `frontend/src/components/structured-answer/supplemental-evidence-row.tsx` component that renders one merged support row with a short title, one reason sentence, and one exact jump link labeled `Open source`. Style the row as light, horizontally generous, and visually subordinate to the answer body. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` with expectations that the new row copy and jump label render when support is expanded.</action>
  <acceptance_criteria>`frontend/src/components/ui/collapsible.tsx` exists.
`frontend/src/components/structured-answer/supplemental-evidence-row.tsx` exists.
`frontend/src/components/structured-answer/supplemental-evidence-row.tsx` contains `Open source`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Open source`.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>The renderer now has a local disclosure primitive and one slim evidence-row component ready for chat integration.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace the always-visible support panel with a collapsed-by-default disclosure</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx</files>
  <read_first>.planning/phases/19-supplemental-evidence-disclosure/19-CONTEXT.md
.planning/phases/19-supplemental-evidence-disclosure/19-RESEARCH.md
.planning/phases/19-supplemental-evidence-disclosure/19-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - Supporting evidence must be collapsed by default.
    - Opening the disclosure must reveal one merged support list or a compact limited/empty state.
    - The answer card must stop rendering separate `Supporting detail` sections that compete with the narrative answer.
  </behavior>
  <action>In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, replace the current always-visible support region with one disclosure directly beneath the answer body and any inline caution rider. The closed label must read `Show supporting evidence`; the open label must read `Hide supporting evidence`. When opened with strong support, render the merged supplemental-evidence rows using the new row component. When opened with limited or empty support, render the exact limited-evidence or empty-evidence copy from the derived view model instead of blank space. Remove the separate `Supporting detail` heading and the split rendering of `TopFindingsList` plus `FindingCards` from the primary chat answer path. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` and `frontend/src/components/chat-shell/chat-shell.test.tsx` so they assert the disclosure is collapsed by default, opens correctly, and shows explicit copy for thin-evidence states.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Show supporting evidence`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Hide supporting evidence`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain `Supporting detail`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not render separate `TopFindingsList` and `FindingCards` sections for completed narrative answers.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Show supporting evidence`.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains a limited- or empty-evidence disclosure assertion.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx</automated>
  </verify>
  <done>The chat answer now keeps evidence collapsed until asked for, and the open state feels like proof-on-demand instead of a second answer panel.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` after both tasks land.
</verification>

<success_criteria>
Phase 19 has a valid second wave once the answer keeps supporting evidence hidden by default, opens one slim merged proof layer on demand, and explains thin-support states explicitly.
</success_criteria>

<output>
After completion, create `.planning/phases/19-supplemental-evidence-disclosure/19-supplemental-evidence-disclosure-02-SUMMARY.md`
</output>
