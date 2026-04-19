---
phase: 15-evidence-navigation-in-chat
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/chat-shell/chat-message-list.tsx
  - frontend/src/components/structured-answer/top-findings-list.tsx
  - frontend/src/components/structured-answer/finding-cards.tsx
  - frontend/src/components/structured-answer/confidence-strip.tsx
  - frontend/src/components/structured-answer/caveat-badge-group.tsx
  - frontend/src/components/structured-answer/evidence-summary.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
autonomous: true
requirements:
  - CHAT-02
  - NAV-01
must_haves:
  truths:
    - "The chat-native answer becomes a complete bounded reading surface with inline findings, confidence, caveats, and one compact evidence-navigation area."
    - "The Phase 15 rendering path reuses existing structured-answer primitives or narrowly adapted variants instead of duplicating the run page."
    - "Repeated per-finding chip rows no longer dominate the chat answer."
  artifacts:
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Expanded Phase 15 chat card with inline findings, confidence/caveats, and compact navigation"
    - path: frontend/src/components/structured-answer/top-findings-list.tsx
      provides: "Chat-safe bounded findings rendering"
    - path: frontend/src/components/structured-answer/evidence-summary.tsx
      provides: "Compact navigation surface adapted for chat"
    - path: frontend/src/components/chat-shell/chat-message-list.test.tsx
      provides: "Regression coverage for inline findings and compact nav in chat"
  key_links:
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/top-findings-list.tsx
      via: "Top findings are rendered inline in the chat card using the existing structured-answer seam"
      pattern: "TopFindingsList|FindingCards"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/confidence-strip.tsx
      via: "Confidence and caveats remain in the same semantics as the run page"
      pattern: "ConfidenceStrip|CaveatBadgeGroup"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/evidence-summary.tsx
      via: "Report, evidence, artifacts, critic, and trace are reachable from one compact nav area"
      pattern: "EvidenceSummary|DeepDiveActions"
---

<objective>
Render inline findings, confidence, caveats, and compact evidence navigation inside the chat-native answer card.

Purpose: satisfy the visible-answer half of `CHAT-02` and `NAV-01` so a user can read and first-pass verify the answer without leaving chat.
Output: an expanded chat answer card, compact reuse of structured-answer primitives, and component-level regression coverage.
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
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/components/structured-answer/top-findings-list.tsx
@frontend/src/components/structured-answer/finding-cards.tsx
@frontend/src/components/structured-answer/confidence-strip.tsx
@frontend/src/components/structured-answer/caveat-badge-group.tsx
@frontend/src/components/structured-answer/evidence-summary.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Expand the chat answer card with inline findings and bounded confidence/caveats</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/structured-answer/top-findings-list.tsx
frontend/src/components/structured-answer/finding-cards.tsx
frontend/src/components/structured-answer/confidence-strip.tsx
frontend/src/components/structured-answer/caveat-badge-group.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/15-evidence-navigation-in-chat/15-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/runs/run-primary-answer.tsx
frontend/src/components/structured-answer/top-findings-list.tsx
frontend/src/components/structured-answer/finding-cards.tsx
frontend/src/components/structured-answer/confidence-strip.tsx
frontend/src/components/structured-answer/caveat-badge-group.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - Top findings and structured critic/alignment findings must render inline in chat.
    - Confidence and caveats must render inline in a bounded form.
    - The chat card must stay compact; it cannot become a run-page clone.
  </behavior>
  <action>Expand `frontend/src/components/chat-shell/chat-run-answer-card.tsx` so, after the conclusion and goal sections, it renders a bounded `Top findings` section plus a compact `Confidence & caveats` section. Reuse the existing structured-answer primitives directly where possible; where the current primitives are too page-oriented, add narrow props or variants rather than duplicating them. Keep overflow bounded and route larger caveat sets toward deep-dive targets instead of expanding the transcript indefinitely. Update `frontend/src/components/chat-shell/chat-message-list.test.tsx` so completed assistant replies now assert the presence of inline findings and confidence/caveat content.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Top findings`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Confidence & caveats`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` reuses structured-answer primitives rather than duplicating their logic.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` asserts findings and confidence/caveat rendering.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>The chat card now carries the main answer-reading content beyond the summary layer.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add one compact evidence-navigation area to the chat card</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/structured-answer/evidence-summary.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <read_first>.planning/phases/15-evidence-navigation-in-chat/15-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/structured-answer/evidence-summary.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</read_first>
  <behavior>
    - Report, evidence, artifacts, critic, and trace must be reachable from one compact navigation area.
    - The compact nav area must be calmer than the old repeated chip rows and link footers.
    - The run strip remains separate and unchanged as the terminal section.
  </behavior>
  <action>Adapt or extend the existing navigation/evidence primitives so `ChatRunAnswerCard` exposes one compact `Open evidence` area with access to report, evidence, artifacts, critic, and trace. Keep the `Open run` strip separate at the bottom. Avoid introducing another footer cluster or large action stack. Update the rendering tests so the chat card asserts the compact nav area and the expected labels.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains a compact evidence-navigation section.
The compact nav exposes report, evidence, artifacts, critic, and trace entry points.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` asserts the compact nav labels.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>The chat card now offers one coherent evidence-navigation surface rather than scattered repeated links.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` after both tasks land.
</verification>

<success_criteria>
Phase 15 has a valid second wave once the chat card renders inline findings, confidence/caveats, and one compact evidence-navigation area in a bounded reading surface.
</success_criteria>

<output>
After completion, create `.planning/phases/15-evidence-navigation-in-chat/15-evidence-navigation-in-chat-02-SUMMARY.md`
</output>
