---
phase: 18-confidence-explainer
plan: 03
type: execute
wave: 3
depends_on:
  - 02
files_modified:
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/structured-answer/confidence-strip.tsx
  - frontend/src/components/structured-answer/caveat-badge-group.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
autonomous: true
requirements:
  - CONF-02
  - CONF-03
must_haves:
  truths:
    - "The primary chat answer keeps at most one short inline caution rider and moves the fuller caveat burden into the explainer."
    - "The primary answer no longer renders the old lower-page confidence/caveat chrome as a competing reading block."
    - "Chat remains grounded, but the answer body is not visually dominated by caveat badges or technical confidence UI."
  artifacts:
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Final primary-answer composition with one inline rider and no redundant confidence block"
    - path: frontend/src/components/structured-answer/confidence-strip.tsx
      provides: "Reduced role or compatibility-only confidence strip after header migration"
    - path: frontend/src/components/structured-answer/caveat-badge-group.tsx
      provides: "Reduced role or compatibility-only caveat component after explainer rollout"
  key_links:
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: .planning/phases/18-confidence-explainer/18-UI-SPEC.md
      via: "The answer follows the approved one-pill header and one-rider inline caveat policy"
      pattern: "Evidence strength:|shortRider|What weakens it"
    - from: frontend/src/components/chat-shell/chat-message-list.test.tsx
      to: frontend/src/components/chat-shell/chat-shell.test.tsx
      via: "Tests lock the absence of old confidence/caveat chrome and the presence of the compact explainer path"
      pattern: "critic: success|report: success|blocking caveats"
---

<objective>
Collapse redundant confidence and caveat chrome so the primary answer stays grounded with one short rider while the fuller rationale lives inside the explainer.

Purpose: satisfy the remaining behavior in `CONF-02` and `CONF-03` by reducing duplicate confidence/caveat UI and keeping the narrative answer visually calm.
Output: cleaned chat answer composition, reduced old confidence/caveat component role, and final renderer/build hardening.
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
@.planning/phases/18-confidence-explainer/18-confidence-explainer-02-PLAN.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/structured-answer/confidence-strip.tsx
@frontend/src/components/structured-answer/caveat-badge-group.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/lib/run-primary-view.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reduce the primary answer to one inline rider plus the explainer path</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx</files>
  <read_first>.planning/phases/18-confidence-explainer/18-CONTEXT.md
.planning/phases/18-confidence-explainer/18-RESEARCH.md
.planning/phases/18-confidence-explainer/18-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/lib/run-primary-view.ts</read_first>
  <behavior>
    - The primary chat answer must keep only one short inline caveat rider when immediate caution is needed.
    - The fuller caveat rationale must be available through the explainer rather than a large permanent inline block.
    - The answer should remain grounded without becoming a wall of badges, caution lists, or repeated confidence UI.
  </behavior>
  <action>In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, remove the old lower-page confidence-and-caveats block from the primary narrative answer composition. Keep exactly one short inline caution rider using the derived `shortRider` or equivalent view-model field when the answer needs immediate grounding, and place that rider directly below the narrative prose. Do not render a second `ConfidenceStrip` block, a stacked `CaveatBadgeGroup`, or a large confidence section beneath the answer once the header pill exists. Keep the explainer trigger in the header as the canonical place to inspect fuller rationale. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` and `frontend/src/components/chat-shell/chat-shell.test.tsx` so one case asserts a short inline caution rider is present when needed, and another asserts the old lower confidence/caveat block is absent from the primary answer render.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `shortRider` or equivalent derived inline-rider field usage.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain a rendered `Confidence` section heading for the primary answer surface.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not contain a rendered `CaveatBadgeGroup` usage in the primary answer composition.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains an inline-rider assertion.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains an absence assertion for the old confidence/caveat block.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx</automated>
  </verify>
  <done>The primary answer now stays grounded with one short caution rider while the fuller rationale lives inside the explainer.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Reduce or isolate legacy confidence components so they stop driving the primary answer</name>
  <files>frontend/src/components/structured-answer/confidence-strip.tsx
frontend/src/components/structured-answer/caveat-badge-group.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/18-confidence-explainer/18-CONTEXT.md
.planning/phases/18-confidence-explainer/18-RESEARCH.md
.planning/phases/18-confidence-explainer/18-UI-SPEC.md
frontend/src/components/structured-answer/confidence-strip.tsx
frontend/src/components/structured-answer/caveat-badge-group.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - Legacy confidence/caveat components may remain for secondary surfaces, but they must not dictate the primary chat answer anymore.
    - The codebase should make the new header-prompted explainer model the default chat pattern.
    - The final frontend gate must stay green after the confidence-surface reduction.
  </behavior>
  <action>In `frontend/src/components/structured-answer/confidence-strip.tsx` and `frontend/src/components/structured-answer/caveat-badge-group.tsx`, trim or reframe these components so they are clearly secondary-surface utilities rather than the primary chat answer pattern. Remove assumptions in comments, labels, or exported prop usage that imply they still own the main answer confidence experience. In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, ensure no code path falls back to the old strip-plus-badges composition for completed narrative answers. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` so it locks the new primary composition and prevents regressions that reintroduce the old block. Finish by running the full Phase 18 frontend gate including `npm run build`.</action>
  <acceptance_criteria>`frontend/src/components/structured-answer/confidence-strip.tsx` does not contain `critic:` in user-facing primary-answer copy.
`frontend/src/components/structured-answer/confidence-strip.tsx` does not contain `report:` in user-facing primary-answer copy.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` does not render `ConfidenceStrip` for completed narrative answers.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains a regression assertion against the old confidence block.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` passes.
`cd frontend && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build</automated>
  </verify>
  <done>The primary answer is now cleanly centered on the new header pill and explainer model, while older confidence helpers are isolated to secondary roles.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` after both tasks land.
</verification>

<success_criteria>
Phase 18 has a valid final wave once the primary answer keeps only one short inline rider, the fuller caveat explanation lives in the explainer, and the old confidence/caveat chrome no longer competes with the narrative answer.
</success_criteria>

<output>
After completion, create `.planning/phases/18-confidence-explainer/18-confidence-explainer-03-SUMMARY.md`
</output>
