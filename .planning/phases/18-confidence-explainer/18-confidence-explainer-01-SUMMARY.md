---
phase: 18-confidence-explainer
plan: 01
subsystem: backend
tags: [fastapi, schemas, traceability, transparency, confidence]
requires:
  - phase: 18-confidence-explainer
    provides: approved grouped confidence-explainer contract
provides:
  - safe grouped confidence rationale in run transparency
  - typed frontend wire support for confidence explainer payloads
  - regression coverage for the new transparency shape
affects: [18-confidence-explainer, run-transparency, traceability]
tech-stack:
  added: []
  patterns:
    - keep backend storage semantics coarse while exposing a product-safe grouped rationale preview
    - prefer typed transparency fields over frontend inference from flat caveat lists
key-files:
  created: []
  modified:
    - backend/agents/traceability_summary.py
    - backend/schemas/run_transparency.py
    - frontend/src/lib/api/types.ts
    - frontend/src/lib/ai-agents-meta.ts
    - tests/test_run_transparency_builders.py
    - tests/test_sprint3_transparency_api.py
    - tests/test_traceability_summary.py
key-decisions:
  - "The confidence explainer is grouped into support, weaknesses, and coverage limits so the UI can explain evidence strength without exposing raw critic internals."
  - "Backend remains the source of truth for the explainer payload; the frontend only renders the safe preview."
patterns-established:
  - "Run transparency can carry additional product-facing answer metadata without exposing prompts or full phase payloads."
  - "Grouped rationale previews are now part of the stable typed API surface."
requirements-completed: []
duration: 19min
completed: 2026-04-24
---

# Phase 18 Plan 01 Summary

**Run transparency now includes a safe grouped confidence explainer that the frontend can render directly.**

## Accomplishments

- Added `confidence_explainer` to the run-transparency schema with `supports`, `weakens`, and `limits` groups.
- Built grouped rationale from the critic/report traceability inputs instead of forcing the frontend to infer confidence detail from flat caveats.
- Extended the transparency and API regression tests to lock the new grouped shape.

## Task Commits

1. **Task 1: Add grouped confidence explainer to traceability and transparency** - `15dcc1d`

## Next Phase Readiness

- The frontend now has a stable safe-preview contract for the evidence-strength header pill and its disclosure.
- Phase 18 Plan 02 can focus on product-facing label mapping and the compact explainer UI.
