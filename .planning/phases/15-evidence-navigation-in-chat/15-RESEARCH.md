---
phase: 15
slug: evidence-navigation-in-chat
status: complete
created: 2026-04-19
---

# Phase 15 - Research

> Research notes for moving findings, caveats, and evidence navigation from the standalone run page into the chat-native answer.

## Problem Statement

Phase 14 made chat the primary place where a run result appears, but the answer is still incomplete there. The current `ChatRunAnswerCard` stops after the conclusion, goal, and compact run strip. The richer reading surface still lives in `RunPrimaryAnswer`, which means users must leave chat to inspect:

- top findings
- critic or alignment findings
- confidence and caveats
- report, evidence, artifacts, critic, and trace navigation

That split conflicts with the milestone goal: the chat transcript should be the primary answer-reading surface, while the run page should become secondary inspection later in Phase 16.

## Existing Seams

### Data seam

`frontend/src/lib/run-primary-view.ts` already derives the answer model needed for Phase 15:

- `takeawayRows`
- `alignmentFindings`
- `overallConfidence`
- `blockingCaveats`
- `criticPhaseStatus`
- `reportPhaseStatus`
- `weakEvidenceSignals`
- `contextSignals`
- `evidenceLinks`
- `extraArtifactCount`
- `reportArtifactId`
- `evidenceProvenanceHint`

That means the phase should extend the existing chat answer contract rather than deriving a second model elsewhere.

### Rendering seam

`frontend/src/components/runs/run-primary-answer.tsx` already composes the current answer-reading sections:

- `TopFindingsList`
- `FindingCards`
- `EvidenceSummary`
- `ConfidenceStrip`
- `CaveatBadgeGroup`
- `DeepDiveActions`
- `VerifyAnalysisSection`

This is the right reuse boundary. Phase 15 should selectively reuse these primitives or extract smaller chat-safe wrappers from them, not duplicate their logic in the chat shell.

### Current chat seam

`frontend/src/components/chat-shell/chat-run-answer-card.tsx` is already the shell for:

- conclusion
- conclusion rider
- goal
- orchestration disclosure
- run strip

So the safest move is to expand this existing card, not replace it.

## Design Constraints

From Phase 15 context and earlier phases:

- chat remains summary-first and bounded
- the run page is not simplified in this phase
- navigation should be compact and centralized, not repeated everywhere
- exact jumps still matter, but should be secondary affordances
- deep-dive and trace remain the place for large or raw detail

## Implementation Options Considered

### Option A - Reuse `PrimaryAnswerView` and expand the chat answer card

Use the same answer builder as the run page, introduce a richer chat answer view, and render bounded findings, confidence, caveats, and navigation inside `ChatRunAnswerCard`.

Pros:

- minimal new derivation logic
- stable semantics across run page and chat
- lowest brownfield risk
- easiest to test against current view model

Cons:

- requires care to avoid importing full run-page sprawl into chat

### Option B - Keep chat compact and add only navigation links

Leave findings and caveats on the run page, but add better chat links.

Pros:

- less code

Cons:

- does not satisfy the milestone problem
- still forces users out of chat for normal reading

### Option C - Create a new chat-only answer model

Build separate chat-specific derivation for findings, caveats, and nav.

Pros:

- freedom to tailor the chat UI

Cons:

- duplicated semantics
- higher regression risk
- drifts from the run page data contract

## Recommended Direction

Option A.

Phase 15 should:

1. add a richer chat answer view derived from `PrimaryAnswerView`
2. reuse the existing structured-answer primitives where they already fit
3. add one compact navigation surface for report, evidence, artifacts, critic, and trace
4. keep exact evidence jumps on finding and caveat rows as secondary actions

## Likely File Groups

### Wave 1 - data contract

- `frontend/src/lib/run-primary-view.ts`
- `frontend/src/actions/runs.ts`
- `frontend/src/lib/chat-run-history.ts`
- `frontend/src/components/chat-shell/types.ts`
- associated tests

### Wave 2 - chat rendering

- `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
- `frontend/src/components/structured-answer/*`
- `frontend/src/components/chat-shell/chat-message-list.tsx`
- associated tests

### Wave 3 - exact jumps and hardening

- `frontend/src/lib/run-primary-view.ts`
- `frontend/src/components/structured-answer/*`
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/actions/runs.test.ts`

## Testing Implications

Frontend-focused validation is sufficient for this phase:

- `vitest` component tests for rendered inline findings, confidence, caveats, and compact nav
- action/history tests for richer answer payloads
- `npm run build` to catch server/client contract breakage

## Outcome

Phase 15 should be planned as three sequential waves:

1. rich answer contract for chat
2. inline evidence-reading UI in the chat card
3. exact-jump and compact-navigation hardening
