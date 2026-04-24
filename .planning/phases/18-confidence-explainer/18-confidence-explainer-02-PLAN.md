---
phase: 18-confidence-explainer
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/components/structured-answer/types.ts
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/ui/popover.tsx
  - frontend/src/lib/__tests__/run-primary-view.test.ts
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
autonomous: true
requirements:
  - CONF-01
  - CONF-02
must_haves:
  truths:
    - "The primary answer header exposes one product-facing confidence pill instead of a lower-page technical strip."
    - "Backend confidence values map to `Good | Medium | Bad | Not rated` in one typed frontend view-model seam."
    - "The explainer opens from the header pill and renders grouped rationale without leaving chat."
  artifacts:
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Product-facing confidence mapping and explainer view-model derivation"
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Header-level confidence pill and explainer trigger on the narrative answer surface"
    - path: frontend/src/components/ui/popover.tsx
      provides: "shadcn-style disclosure primitive for the compact explainer"
  key_links:
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "The answer card consumes a product-facing confidence model instead of raw backend labels"
      pattern: "Good|Medium|Bad|Not rated|confidenceExplainer"
    - from: frontend/src/components/ui/popover.tsx
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "The compact explainer disclosure is anchored to the answer-header confidence pill"
      pattern: "Popover|Trigger|Content"
    - from: frontend/src/components/chat-shell/chat-message-list.test.tsx
      to: frontend/src/components/chat-shell/chat-shell.test.tsx
      via: "Renderer tests lock single-pill header behavior and grouped explainer visibility"
      pattern: "Evidence strength|What supports this rating|What weakens it|What limits the evidence"
---

<objective>
Move confidence into the answer header and render the compact explainer through a shadcn disclosure without yet collapsing the old caveat surfaces.

Purpose: satisfy the primary UI portion of `CONF-01` and `CONF-02` by making confidence visible at a glance and explainable in place through the narrative answer header.
Output: frontend confidence view-model mapping, header pill renderer, shadcn disclosure primitive, and renderer regression coverage.
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
@.planning/phases/18-confidence-explainer/18-CONTEXT.md
@.planning/phases/18-confidence-explainer/18-RESEARCH.md
@.planning/phases/18-confidence-explainer/18-VALIDATION.md
@.planning/phases/18-confidence-explainer/18-UI-SPEC.md
@.planning/phases/18-confidence-explainer/18-confidence-explainer-01-PLAN.md
@frontend/src/lib/run-primary-view.ts
@frontend/src/components/structured-answer/types.ts
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/ui/badge.tsx
@frontend/src/lib/__tests__/run-primary-view.test.ts
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Derive a product-facing confidence model for the narrative answer header</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/components/structured-answer/types.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</files>
  <read_first>.planning/phases/18-confidence-explainer/18-CONTEXT.md
.planning/phases/18-confidence-explainer/18-RESEARCH.md
.planning/phases/18-confidence-explainer/18-UI-SPEC.md
frontend/src/lib/api/types.ts
frontend/src/lib/run-primary-view.ts
frontend/src/components/structured-answer/types.ts
frontend/src/lib/__tests__/run-primary-view.test.ts</read_first>
  <behavior>
    - The primary answer view must map backend `high | medium | low | null` to `Good | Medium | Bad | Not rated`.
    - The answer view must expose grouped explainer content and a short optional inline rider.
    - Raw `critic/report` technical status labels must stop being required by the primary chat answer header.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add exact exported types for a product-facing confidence header model that includes `label`, `tone`, `supports`, `weakens`, `limits`, and `shortRider`. Map backend `confidence_explainer.rating` values to exact product labels `Good`, `Medium`, `Bad`, and `Not rated`; map tones to semantic values that the answer card can style consistently. Extend `ChatAnswerCardView` so it carries one derived confidence object for the header and no longer depends on raw `criticPhaseStatus` or `reportPhaseStatus` to explain confidence in the primary answer. Keep the existing raw confidence/status fields available for secondary surfaces if they are still needed elsewhere, but do not require them for the header contract. In `frontend/src/components/structured-answer/types.ts`, add or update any shared prop types needed for the new confidence-header view. In `frontend/src/lib/__tests__/run-primary-view.test.ts`, add exact cases proving `high -> Good`, `medium -> Medium`, `low -> Bad`, and `null -> Not rated`, and assert that grouped `supports`, `weakens`, `limits`, plus `shortRider`, are derived from the safe preview contract.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains `Good`.
`frontend/src/lib/run-primary-view.ts` contains `Medium`.
`frontend/src/lib/run-primary-view.ts` contains `Bad`.
`frontend/src/lib/run-primary-view.ts` contains `Not rated`.
`frontend/src/lib/run-primary-view.ts` contains `shortRider`.
`frontend/src/lib/run-primary-view.ts` contains `supports`.
`frontend/src/lib/run-primary-view.ts` contains `weakens`.
`frontend/src/lib/run-primary-view.ts` contains `limits`.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains `high -> Good` or equivalent assertions for `Good`, `Medium`, `Bad`, and `Not rated`.
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts</automated>
  </verify>
  <done>The primary answer view now has one product-facing confidence model that the chat header can render directly.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Render the header confidence pill and compact explainer with a shadcn disclosure</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/ui/popover.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx</files>
  <read_first>.planning/phases/18-confidence-explainer/18-CONTEXT.md
.planning/phases/18-confidence-explainer/18-RESEARCH.md
.planning/phases/18-confidence-explainer/18-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/ui/badge.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - The answer header must show exactly one compact `Evidence strength` pill with semantic styling and built-in chevron.
    - Opening the pill must reveal grouped support, weakness, and limits content without leaving chat.
    - The primary answer header must no longer show raw `critic: success` or `report: success` labels.
  </behavior>
  <action>In `frontend/src/components/ui/`, add a local shadcn-style `popover.tsx` primitive if one is not already present, following the repo’s current shadcn conventions and Radix-backed composition. In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, move confidence rendering into the answer header so the exact header row contains the quiet `Answer` label on the left and one clickable pill on the right. The pill text must use the exact prefix `Evidence strength:` and the derived product label, and it must include a chevron affordance. Style the pill with semantic tones from the derived confidence model: green for `Good`, amber for `Medium`, red for `Bad`, and neutral for `Not rated`. Use the new popover as the preferred disclosure primitive and render three grouped sections with the exact headings `What supports this rating`, `What weakens it`, and `What limits the evidence`. Each section should render concise list items from the grouped rationale arrays. Remove any inline `critic: success` and `report: success` text from the primary answer header and explainer trigger area. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` and `frontend/src/components/chat-shell/chat-shell.test.tsx` so they assert the presence of the single `Evidence strength:` pill, the grouped explainer headings, and the absence of raw `critic:` / `report:` labels in the primary answer surface.</action>
  <acceptance_criteria>`frontend/src/components/ui/popover.tsx` exists.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Evidence strength:`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `What supports this rating`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `What weakens it`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `What limits the evidence`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain `critic:`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain `report:`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Evidence strength:`.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains `What supports this rating`.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx</automated>
  </verify>
  <done>The primary answer header now exposes one semantic confidence pill that opens a compact grouped explainer in place.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` after both tasks land.
</verification>

<success_criteria>
Phase 18 has a sound second wave once the narrative answer header shows a single semantic confidence pill, the explainer opens in place from that pill, and raw technical confidence labels no longer dominate the primary answer surface.
</success_criteria>

<output>
After completion, create `.planning/phases/18-confidence-explainer/18-confidence-explainer-02-SUMMARY.md`
</output>
