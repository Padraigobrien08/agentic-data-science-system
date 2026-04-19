---
phase: 14-chat-native-result-contract
plan: 03
type: execute
wave: 3
depends_on:
  - 01
  - 02
files_modified:
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/chat-shell/chat-message-list.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
  - frontend/src/actions/runs.test.ts
  - frontend/src/lib/run-status-copy.ts
  - frontend/src/components/ui/technical.tsx
  - frontend/src/lib/format.ts
  - frontend/src/app/projects/[projectId]/chat/page.tsx
autonomous: true
requirements:
  - CHAT-01
  - CHAT-03
must_haves:
  truths:
    - "Each completed chat answer ends with one compact run identity strip that shows friendly status, one timestamp, a short run id, and one primary `Open run` action."
    - "Legacy `Run answer`, `Deep dive`, and `All runs` link sprawl disappears from successful structured assistant replies."
    - "Regression coverage proves persisted history, pending-to-final upgrades, and the single-action run strip all survive the Phase 14 finish line and production build."
  artifacts:
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Compact run identity strip attached to the chat-native answer card"
    - path: frontend/src/components/chat-shell/chat-message-list.tsx
      provides: "Structured-answer rendering path with the old link footer removed"
    - path: frontend/src/components/chat-shell/chat-message-list.test.tsx
      provides: "Regression coverage for `Open run`, status strip content, and absence of legacy link sprawl"
    - path: frontend/src/app/projects/[projectId]/chat/page.tsx
      provides: "Chat page copy aligned to the new inline answer-reading experience"
  key_links:
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/lib/run-status-copy.ts
      via: "The run strip uses the existing friendly run-status language instead of inventing a second status vocabulary"
      pattern: "formatRunStatusLabel|runStatusExplanation|Completed|Failed"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/ui/technical.tsx
      via: "The answer card reuses the existing status badge styling for a compact, readable run strip"
      pattern: "StatusBadge|variant=\"friendly\""
    - from: frontend/src/components/chat-shell/chat-message-list.test.tsx
      to: frontend/src/components/chat-shell/chat-message-list.tsx
      via: "Tests lock the Phase 14 contract: one `Open run` CTA, no legacy footer links, and preserved unsupported guidance behavior"
      pattern: "Open run|Run answer|Deep dive|All runs"
---

<objective>
Finish the Phase 14 chat-native result contract with the compact run identity strip, removal of legacy link sprawl, and focused regression hardening.

Purpose: complete `CHAT-01` and `CHAT-03` so chat becomes the primary answer-reading surface with one clear run-linkage affordance.
Output: run identity strip, single-action `Open run` contract, updated page copy, and green frontend regressions plus build.
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
@.planning/phases/14-chat-native-result-contract/14-CONTEXT.md
@.planning/phases/14-chat-native-result-contract/14-RESEARCH.md
@.planning/phases/14-chat-native-result-contract/14-VALIDATION.md
@.planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
@.planning/phases/14-chat-native-result-contract/14-chat-native-result-contract-01-PLAN.md
@.planning/phases/14-chat-native-result-contract/14-chat-native-result-contract-02-PLAN.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/actions/runs.test.ts
@frontend/src/lib/run-status-copy.ts
@frontend/src/components/ui/technical.tsx
@frontend/src/lib/format.ts
@frontend/src/app/projects/[projectId]/chat/page.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add the compact run identity strip and remove the legacy link footer</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/lib/run-status-copy.ts
frontend/src/components/ui/technical.tsx
frontend/src/lib/format.ts
frontend/src/app/projects/[projectId]/chat/page.tsx</files>
  <read_first>.planning/phases/14-chat-native-result-contract/14-CONTEXT.md
.planning/phases/14-chat-native-result-contract/14-RESEARCH.md
.planning/phases/14-chat-native-result-contract/14-UI-SPEC.md
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/lib/run-status-copy.ts
frontend/src/components/ui/technical.tsx
frontend/src/lib/format.ts
frontend/src/app/projects/[projectId]/chat/page.tsx</read_first>
  <behavior>
    - Completed structured assistant replies must end with one compact run strip, not a cluster of follow-up links.
    - The run strip must use existing friendly run-status language and existing badge styling.
    - The page-level copy must describe chat as the primary answer-reading surface, not as a thin shell for run-answer and deep-dive links.
  </behavior>
  <action>Update `frontend/src/components/chat-shell/chat-run-answer-card.tsx` so it renders a bottom run identity strip with exactly these elements: a `StatusBadge` using `variant=\"friendly\"`, one locale-formatted timestamp using `formatDate(...)` and preferring `runFinishedAt` over `runCreatedAt`, one short monospace run id label such as the first 8 characters of `runId`, and one shadcn `Button` labeled `Open run` that links to `runHref`. Keep this strip out of unsupported guidance replies. In `frontend/src/components/chat-shell/chat-message-list.tsx`, remove the old structured-reply footer that renders `Run answer`, `Deep dive`, and `All runs` links. Keep muted delivery notes beneath the card, but the only primary action on a structured answer should be `Open run`. If needed, extend `frontend/src/lib/run-status-copy.ts`, `frontend/src/components/ui/technical.tsx`, or `frontend/src/lib/format.ts` only enough to support the strip copy and timestamp formatting cleanly. Then update `frontend/src/app/projects/[projectId]/chat/page.tsx` intro copy so it says completed analyses appear inline in workspace chat and the standalone run page is for secondary inspection.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Open run`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `StatusBadge`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `formatDate(`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `font-mono`.
`frontend/src/components/chat-shell/chat-message-list.tsx` no longer contains `Run answer`.
`frontend/src/components/chat-shell/chat-message-list.tsx` no longer contains `Deep dive`.
`frontend/src/components/chat-shell/chat-message-list.tsx` no longer contains `All runs`.
`frontend/src/app/projects/[projectId]/chat/page.tsx` no longer contains `run answer and deep dive links`.
`frontend/src/app/projects/[projectId]/chat/page.tsx` contains `completed analyses` or `inline`.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` passes once the tests are updated.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx</automated>
  </verify>
  <done>Structured chat answers now have one compact, explicit run-linkage strip and no longer depend on the old multi-link footer.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Lock the Phase 14 contract with regression coverage and production build verification</name>
  <files>frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/actions/runs.test.ts</files>
  <read_first>.planning/phases/14-chat-native-result-contract/14-VALIDATION.md
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/actions/runs.test.ts</read_first>
  <behavior>
    - Tests must lock the single-action `Open run` contract on completed structured answers.
    - Tests must prove persisted history and in-place pending-to-final upgrades still work after the run strip lands.
    - The Phase 14 closeout must include a green production build, not just unit tests.
  </behavior>
  <action>Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` so a completed structured answer asserts `Open run` is present while `Run answer`, `Deep dive`, and `All runs` are absent. Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` so a seeded persisted history plus a new prompt still shows one visible thread and one pending assistant slot upgrading in place, not duplicate completion bubbles. Extend `frontend/src/actions/runs.test.ts` so the supported branch still returns the `answerCard` payload plus `runStatus`, `runCreatedAt`, and `runFinishedAt` used by the strip. Finish by running the full Phase 14 validation gate: `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build`.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Open run`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` asserts `Run answer` is absent.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` asserts `Deep dive` is absent.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains an assertion that only one pending assistant slot exists for a new request.
`frontend/src/actions/runs.test.ts` contains `runStatus`.
`frontend/src/actions/runs.test.ts` contains `runCreatedAt`.
`frontend/src/actions/runs.test.ts` contains `runFinishedAt`.
`cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build</automated>
  </verify>
  <done>The Phase 14 chat-native result contract is locked by tests and production build verification.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` after both tasks land.
</verification>

<success_criteria>
Phase 14 is complete once chat is the primary answer-reading surface, each completed answer carries one compact `Open run` strip, and reload-safe history plus in-place upgrades are locked by focused frontend regressions.
</success_criteria>

<output>
After completion, create `.planning/phases/14-chat-native-result-contract/14-chat-native-result-contract-03-SUMMARY.md`
</output>
