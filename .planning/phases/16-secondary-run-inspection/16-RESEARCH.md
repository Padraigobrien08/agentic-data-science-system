---
phase: 16
slug: secondary-run-inspection
status: complete
created: 2026-04-19
---

# Phase 16 - Research

> Research notes for reducing the standalone run page into a secondary verification surface.

## Problem Statement

After Phase 15, chat now carries:

- the primary answer summary
- top findings
- confidence and caveats
- compact evidence navigation
- exact-jump verification links

The standalone run page still renders most of that reading stack again through `RunPrimaryAnswer`. That duplication weakens the product model: users see two competing answer surfaces instead of one primary chat answer and one secondary inspection surface.

## Current Duplication

The duplication is concentrated in:

- `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`
- `frontend/src/components/runs/run-primary-answer.tsx`

Specifically, the run page still presents:

- `Primary summary`
- full `Top findings`
- full `Confidence & caveats`
- `Evidence`
- `Next steps`

Those are now largely redundant with the chat answer.

## Surfaces That Still Matter

The run page should keep value where chat is not the right place:

- explicit run status and timestamps
- run id / technical identity
- state banner and execution-progress track
- full error summary
- verification strip
- rerun control when appropriate
- deep-dive and trace entry points

The trace page already owns the real step-by-step inspection workflow. The run page does not need to duplicate that either; it just needs to bridge users into it.

## Implementation Options Considered

### Option A - Verification-first run page

Replace the broad reading stack with a smaller inspection-oriented composition:

- compact top summary or framing note
- explicit `Back to chat`
- status and lifecycle context
- verify strip
- outcome suggestions only when the run is partial/no-data/error
- compact inspection actions

Pros:

- directly matches the milestone goal
- minimal semantics change
- clearest product hierarchy

Cons:

- requires trimming or replacing `RunPrimaryAnswer`

### Option B - Keep the current page and only change labels

Pros:

- smallest code diff

Cons:

- does not solve the real duplication problem

### Option C - Push everything to the trace page

Pros:

- extreme simplification

Cons:

- too destructive
- removes a useful intermediate inspection surface

## Recommended Direction

Option A.

The safest move is to treat the run page as a bridge between chat and trace:

1. show users they are on a verification surface
2. give them a clear return path to chat
3. keep status, error, rerun, verify, and trace access
4. remove or compress duplicated answer-reading content

## Likely File Groups

### Wave 1 - framing and inspection component seam

- `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`
- `frontend/src/components/runs/run-primary-answer.tsx` or a new inspection-specific component

### Wave 2 - duplication reduction

- `frontend/src/components/runs/run-primary-answer.tsx`
- `frontend/src/components/runs/verify-analysis-section.tsx`
- `frontend/src/components/runs/outcome-suggestions-panel.tsx`
- related tests

### Wave 3 - copy and regression hardening

- `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`
- new or extended tests
- `npm run build`

## Testing Implications

There is little existing direct test coverage for the run answer page. Phase 16 should add focused component tests around the new inspection-first composition and then close with the frontend build.

## Outcome

Phase 16 should be planned as three sequential waves:

1. establish the inspection-first run page shell
2. remove duplicated answer-reading sections while preserving verification value
3. lock the new page role with focused tests and build verification
