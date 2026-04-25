---
phase: 21
slug: narrative-answer-polish
status: complete
created: 2026-04-25
---

# Phase 21 - Research

> Final milestone-finish research for making the shipped narrative answer stack feel like one intentional product surface instead of several recently-landed UI layers.

## Research Goal

Identify the smallest coherent polish pass that improves readability, spacing, responsive behavior, and chat/trace language without reopening any of the data contracts shipped in Phases 17-20.

## Confirmed Constraints

- Narrative answer semantics are already locked in backend-safe previews from Phase 17.
- Confidence posture is already locked to a compact header pill plus explainer from Phase 18.
- Supporting evidence is already locked behind a collapsed disclosure from Phase 19.
- Inline charts are already locked to deterministic backend previews rendered inline from Phase 20.
- Trace should remain the technical surface; chat should remain the answer-reading surface.

## Current Seams Reviewed

### Answer composition
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
- `frontend/src/lib/run-primary-view.ts`

Findings:
- The component already has the correct hierarchy, but the answer still reads as several adjacent feature blocks rather than one editorial surface.
- The narrative section spacing, support-note rhythm, and transitions between prose, charts, and disclosure can be tightened without changing the answer contract.
- Inline source or jump-link polish should happen inside the answer shell, not by pushing users into trace.

### Conversation width and responsiveness
- `frontend/src/components/chat-shell/chat-message-list.tsx`
- `frontend/src/components/structured-answer/inline-evidence-charts.tsx`

Findings:
- The conversation column is already centered, but desktop and smaller-screen width behavior can be tuned so the answer uses space more intentionally.
- Charts and disclosure rows already sit in the correct order, but Phase 21 should ensure they stack cleanly and breathe consistently across common viewports.
- The right answer is not to add another layout mode; it is to keep one answer-first layout and tune the spacing/breakpoints.

### Trace wording and positioning
- `frontend/src/components/trace/run-trace-summary-view.tsx`
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`

Findings:
- The trace surface already leans technical, but some copy still needs to reinforce that it is for audit and inspection, not for re-reading the main answer.
- Navigation labels should clearly suggest “inspect” or “deep dive” rather than implying the trace is a second answer page.

## Recommended Implementation Shape

1. Polish the answer shell itself.
   - tighten section rhythm
   - improve prose hierarchy
   - refine small-copy utility styles
   - keep the answer visually central

2. Tune responsive behavior in the same shell.
   - answer remains centered on desktop
   - answer relaxes toward near-full width with clean margins on smaller screens
   - charts/disclosure/pills keep the same reading order

3. Align wording and navigation.
   - chat = answer surface
   - trace = technical deep dive
   - navigation labels and helper copy make that distinction explicit

## Rejected Directions

- Reopening narrative answer semantics or length targets
- Reintroducing side rails or multi-column answer reading
- Hiding trace completely
- Adding new exploratory chart controls or evidence states
- Moving more meaning into frontend heuristics

## Outcome

Phase 21 should be a frontend-heavy polish pass with no new backend semantics. The main execution risk is coherence across multiple already-shipped answer subcomponents, so the plan should focus on one unified answer-shell refinement, one responsive pass, and one wording/navigation alignment pass with tight regression coverage.
