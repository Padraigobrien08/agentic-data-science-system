---
phase: 21-narrative-answer-polish
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/components/chat-shell/chat-message-list.tsx
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/lib/__tests__/run-primary-view.test.ts
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
autonomous: true
requirements:
  - ANSR-01
  - ANSR-03
must_haves:
  truths:
    - "The narrative answer remains the primary reading surface and reads like one editorial reply rather than a stack of detached sections."
    - "Link and citation polish sharpens claims without turning the answer into a report-style footnote system."
    - "Phase 21 does not reopen backend answer semantics; it refines presentation and reading rhythm."
  artifacts:
    - path: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      provides: "Final prose hierarchy, spacing, and citation/link treatment in the answer shell"
    - path: frontend/src/components/chat-shell/chat-message-list.tsx
      provides: "Transcript-level width and reading-column polish"
    - path: frontend/src/lib/__tests__/run-primary-view.test.ts
      provides: "Regression coverage that answer polish does not break the view model"
  key_links:
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "Answer view data still flows through one narrative-first renderer"
      pattern: "narrativeAnswer|summaryLine|supplementalEvidence"
    - from: frontend/src/components/chat-shell/chat-message-list.tsx
      to: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      via: "Conversation width and centered reading behavior stay aligned"
      pattern: "max-w|justify-center|ChatRunAnswerCard"
---

<objective>
Polish the answer shell so the shipped narrative answer feels like one centered analyst reply instead of a collection of recently-added sections.

Purpose: satisfy the final prose hierarchy, spacing, and citation/link polish goal from Phase 21.
Output: a calmer answer shell, sharper narrative rhythm, and tests that lock the answer-first reading hierarchy.
</objective>

<context>
@.planning/phases/21-narrative-answer-polish/21-CONTEXT.md
@.planning/phases/21-narrative-answer-polish/21-RESEARCH.md
@.planning/phases/21-narrative-answer-polish/21-UI-SPEC.md
@.planning/phases/21-narrative-answer-polish/21-VALIDATION.md
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/lib/run-primary-view.ts
@frontend/src/lib/__tests__/run-primary-view.test.ts
@frontend/src/components/chat-shell/chat-message-list.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Refine the answer shell into a calmer editorial reading surface</name>
  <files>frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx</files>
  <action>Adjust the answer-card and transcript composition so the prose reads as one centered editorial surface. Tighten section rhythm, reduce utility-label dominance, soften the feeling of stacked modules, and tune the centered conversation width so assistant replies use the available width more intentionally. Where exact-jump or source links already exist, make their styling calmer and more citation-like instead of CTA-like, but do not remove the existing access path to evidence or trace. Update tests to lock the centered answer-column behavior and preserve the answer-first hierarchy.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-run-answer-card.tsx` reflects quieter section rhythm and calmer source-link presentation.
`frontend/src/components/chat-shell/chat-message-list.tsx` reflects the final centered reading-column polish.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` is updated for the final answer-column hierarchy.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/lib/__tests__/run-primary-view.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/lib/__tests__/run-primary-view.test.ts</automated>
  </verify>
  <done>The answer reads like one centered chat reply with subordinate proof, not like assembled stacked chrome.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/lib/__tests__/run-primary-view.test.ts` after the task lands.
</verification>

<success_criteria>
Phase 21 Wave 1 is complete when the narrative answer shell feels editorial and centered, and the transcript still preserves the answer-first hierarchy.
</success_criteria>

<output>
After completion, create `.planning/phases/21-narrative-answer-polish/21-narrative-answer-polish-01-SUMMARY.md`
</output>
