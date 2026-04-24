---
phase: 19-supplemental-evidence-disclosure
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/components/structured-answer/types.ts
  - frontend/src/lib/__tests__/run-primary-view.test.ts
autonomous: true
requirements:
  - ANSR-03
  - EVID-01
  - EVID-02
must_haves:
  truths:
    - "The chat answer has one unified supplemental-evidence model instead of separate takeaway and alignment render paths."
    - "The answer view can describe strong evidence, limited evidence, and empty evidence without hiding the disclosure seam."
    - "The evidence layer remains subordinate to the narrative answer because the view model separates answer content from proof-on-demand content."
  artifacts:
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Unified supplemental evidence rows and limited-evidence disclosure state"
    - path: frontend/src/components/structured-answer/types.ts
      provides: "Shared prop contracts for the merged evidence-row renderer"
    - path: frontend/src/lib/__tests__/run-primary-view.test.ts
      provides: "Regression coverage for merged rows and limited-evidence derivation"
  key_links:
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "One answer-card seam now exposes narrative content separately from disclosure-bound evidence rows"
      pattern: "supplementalEvidence|limitedEvidence|navigationItems"
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/structured-answer/types.ts
      via: "The merged evidence-row contract becomes the single frontend support shape"
      pattern: "title|reason|jump"
    - from: frontend/src/lib/__tests__/run-primary-view.test.ts
      to: frontend/src/lib/run-primary-view.ts
      via: "View-model tests lock the answer-first hierarchy before renderer work begins"
      pattern: "takeawayRows|alignmentFindings|limited evidence"
---

<objective>
Create the Phase 19 frontend data contract for supplemental evidence before changing the chat renderer.

Purpose: satisfy the foundation of `ANSR-03`, `EVID-01`, and `EVID-02` by replacing the current split support model with one merged supplemental-evidence view that can be disclosed, limited, or empty without changing the narrative answer contract.
Output: unified supplemental evidence rows in the frontend view model, shared prop types, and regression tests proving the merged support layer and limited-evidence states.
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
@frontend/src/lib/run-primary-view.ts
@frontend/src/components/structured-answer/types.ts
@frontend/src/lib/__tests__/run-primary-view.test.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Unify takeaway and alignment support into one supplemental evidence list</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/components/structured-answer/types.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</files>
  <read_first>.planning/phases/19-supplemental-evidence-disclosure/19-CONTEXT.md
.planning/phases/19-supplemental-evidence-disclosure/19-RESEARCH.md
.planning/phases/19-supplemental-evidence-disclosure/19-UI-SPEC.md
frontend/src/lib/run-primary-view.ts
frontend/src/components/structured-answer/types.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</read_first>
  <behavior>
    - The primary chat answer must no longer require separate `takeawayRows` and `alignmentFindings` sections to explain support.
    - Supporting rows must normalize to one horizontally friendly shape with a short title, one reason sentence, and one exact jump.
    - Existing evidence links and exact jump targets must survive the merge.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add an exact exported supplemental-evidence row type that carries one short `title`, one `reason`, and one exact `jump` link target derived from the current support data. Refactor the chat-answer derivation so takeaway content and alignment-finding content both normalize into one ordered `supplementalEvidence` list, while preserving existing artifact or trace jumps. Do not remove existing legacy fields yet if other surfaces still rely on them, but make the new merged list the preferred path for chat answers. In `frontend/src/components/structured-answer/types.ts`, add shared prop types for the merged evidence row and any disclosure-state fields the renderer will need next. Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` so it proves both takeaway-driven and alignment-driven content collapse into the same row model and that each row keeps one exact jump.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains `supplementalEvidence`.
`frontend/src/lib/run-primary-view.ts` contains `title`.
`frontend/src/lib/run-primary-view.ts` contains `reason`.
`frontend/src/lib/run-primary-view.ts` contains `jump`.
`frontend/src/components/structured-answer/types.ts` contains the merged row prop contract.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains `supplementalEvidence`.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains assertions covering both takeaway and alignment content.
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts</automated>
  </verify>
  <done>The chat answer now has one merged supplemental-evidence list that later renderer work can disclose instead of permanently displaying two support sections.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Derive explicit limited-evidence and empty-evidence disclosure states</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</files>
  <read_first>.planning/phases/19-supplemental-evidence-disclosure/19-CONTEXT.md
.planning/phases/19-supplemental-evidence-disclosure/19-RESEARCH.md
.planning/phases/19-supplemental-evidence-disclosure/19-VALIDATION.md
frontend/src/lib/run-primary-view.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</read_first>
  <behavior>
    - The evidence disclosure must remain present even when support is sparse or missing.
    - The view model must make it explicit whether evidence is strong, limited, or empty.
    - Thin-support cases must explain that support was checked but remains limited rather than looking like a rendering failure.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add disclosure-state derivation that distinguishes at least the following modes for the supplemental evidence layer: evidence available, limited evidence, and empty evidence. Use existing signals such as `emptyStateReason`, `evidenceProvenanceHint`, evidence-link counts, weak-evidence signals, and sparse-support conditions to decide which mode applies. Expose the exact label copy and supporting explanatory text needed by the chat renderer so the renderer does not need to guess. Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` so it asserts the merged support model still exposes a disclosure state when evidence is thin, and that empty-evidence cases return explicit copy rather than null.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains explicit disclosure-state handling for limited or empty evidence.
`frontend/src/lib/run-primary-view.ts` contains copy or fields for a limited-evidence explanation.
`frontend/src/lib/run-primary-view.ts` contains copy or fields for an empty-evidence explanation.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains a limited-evidence case.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains an empty-evidence case.
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts</automated>
  </verify>
  <done>The view model can now tell the renderer when to show real support rows, a limited-support explanation, or an empty-support explanation while keeping the disclosure seam intact.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts` after both tasks land.
</verification>

<success_criteria>
Phase 19 has a sound first wave once the frontend view model exposes one merged supplemental-evidence list and explicit limited/empty disclosure states without disturbing the narrative answer contract.
</success_criteria>

<output>
After completion, create `.planning/phases/19-supplemental-evidence-disclosure/19-supplemental-evidence-disclosure-01-SUMMARY.md`
</output>
