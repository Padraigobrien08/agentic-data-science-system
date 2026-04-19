---
phase: 16
slug: secondary-run-inspection
status: approved
shadcn_initialized: true
preset: new-york
created: 2026-04-19
reviewed_at: 2026-04-19T11:42:00Z
---

# Phase 16 — UI Design Contract

> Visual and interaction contract for turning the standalone run page into a secondary inspection surface.

## Visual Hierarchy

**Primary focal point:** verification framing and explicit return-to-chat guidance.

**Reading order:**
1. header with run status and `Back to chat`
2. state banner and phase track
3. error summary when present
4. verification strip / inspection actions
5. partial-result suggestions when relevant
6. secondary technical metadata

**Rules:**

- The page must no longer read like the main answer destination.
- The strongest copy cue should tell the user what this page is for: inspection, verification, and rerun.
- Chat return navigation must be visible near the top.
- Avoid long prose sections and repeated answer summaries.

## Spacing and Density

- Keep the existing page width and shell rhythm.
- Reduce vertical section count compared with the current run page.
- Use compact action clusters instead of large full-width next-step slabs.

## Typography

- Replace `Primary summary` framing with verification-oriented language.
- Use label-sized uppercase metadata sparingly.
- Technical identity items such as run id remain small and de-emphasized.

## Color

- Reuse current neutral, warning, and error tones.
- Avoid introducing new accent blocks on the run page.
- The page should feel quieter than the chat answer, not louder.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Header eyebrow | `Inspection surface` or similar verification-first framing |
| Primary return action | `Back to chat` |
| Deep-dive action | `Open trace` or `Deep dive` |
| Page body note | concise line explaining that the full answer lives in chat and this page is for verification |

Rules:

- Do not call the page `Primary summary`.
- Do not imply the page is where the user should first read the answer.

## Component Contract

### Keep

- run status/timestamp header
- `RunStateBanner`
- `RunPipelinePhaseTrack`
- error summary
- `VerifyAnalysisSection`
- rerun control when valid

### Remove or compress

- duplicated answer summary stack
- full top findings section
- full confidence/caveat section
- broad next-steps footer

### Conditional keep

- outcome suggestions remain only when they materially help partial/no-data/error follow-up

## Interaction Contract

- The page should always offer a clear path back to chat.
- The run page should still link into trace and artifacts for inspection.
- No new modal, drawer, or tab system in this phase.

## Phase Boundaries

- Do not redesign the trace page in this phase.
- Do not remove run status, rerun, or verification affordances.
- Do not add message-anchored chat navigation.

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-04-19
