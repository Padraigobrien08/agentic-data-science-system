---
phase: 18-confidence-explainer
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/schemas/run_transparency.py
  - backend/agents/traceability_summary.py
  - frontend/src/lib/api/types.ts
  - tests/test_run_transparency_builders.py
  - tests/test_traceability_summary.py
  - tests/test_sprint3_transparency_api.py
autonomous: true
requirements:
  - CONF-01
  - CONF-02
  - CONF-03
must_haves:
  truths:
    - "Run transparency exposes a typed safe confidence-explainer preview instead of only coarse confidence and flat caveat strings."
    - "Backend traceability continues to store `high | medium | low | null`, while the grouped rationale needed by chat is available in one structured preview."
    - "The run detail API and frontend wire mirror can consume grouped support, weakness, and limits data without reading raw critic payloads."
  artifacts:
    - path: backend/schemas/run_transparency.py
      provides: "Typed confidence-explainer preview on the existing safe transparency surface"
    - path: backend/agents/traceability_summary.py
      provides: "Grouped rationale assembly from safe critic/report/traceability data"
    - path: tests/test_sprint3_transparency_api.py
      provides: "API regression coverage for the new explainer fields"
  key_links:
    - from: backend/agents/traceability_summary.py
      to: backend/schemas/run_transparency.py
      via: "Traceability becomes the source of truth for grouped confidence rationale exposed to chat"
      pattern: "supports|weakens|limits|confidence_explainer"
    - from: backend/schemas/run_transparency.py
      to: frontend/src/lib/api/types.ts
      via: "The frontend wire mirror matches the safe grouped rationale contract exactly"
      pattern: "ConfidenceExplainerPreview|rating|supports|weakens|limits"
    - from: tests/test_run_transparency_builders.py
      to: tests/test_sprint3_transparency_api.py
      via: "Builder and API tests lock serialization and transport of the new explainer preview"
      pattern: "confidence_explainer|critic_overall_confidence|blocking_caveats"
---

<objective>
Define the backend-safe confidence-explainer contract and expose it through the current run-transparency seam before any primary-answer UI migration begins.

Purpose: satisfy the contract half of `CONF-01`, `CONF-02`, and `CONF-03` by making grouped support, weakness, and evidence-limit rationale first-class safe-preview fields instead of forcing the frontend to infer them from flat caveat lists.
Output: transparency schema updates, traceability-summary assembly, frontend wire mirrors, and backend regression coverage.
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
@backend/schemas/run_transparency.py
@backend/agents/output_schemas.py
@backend/agents/traceability_summary.py
@frontend/src/lib/api/types.ts
@tests/test_run_transparency_builders.py
@tests/test_traceability_summary.py
@tests/test_sprint3_transparency_api.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add a typed confidence-explainer preview to run transparency</name>
  <files>backend/schemas/run_transparency.py
frontend/src/lib/api/types.ts
tests/test_run_transparency_builders.py
tests/test_sprint3_transparency_api.py</files>
  <read_first>.planning/phases/18-confidence-explainer/18-CONTEXT.md
.planning/phases/18-confidence-explainer/18-RESEARCH.md
.planning/phases/18-confidence-explainer/18-VALIDATION.md
.planning/phases/18-confidence-explainer/18-UI-SPEC.md
backend/schemas/run_transparency.py
frontend/src/lib/api/types.ts
tests/test_run_transparency_builders.py
tests/test_sprint3_transparency_api.py</read_first>
  <behavior>
    - The safe run-transparency surface must expose grouped confidence rationale for the chat answer.
    - The backend must continue using `high | medium | low | null` for stored and serialized rating semantics in this phase.
    - The frontend wire mirror must model the new preview without removing existing transparency fields.
  </behavior>
  <action>In `backend/schemas/run_transparency.py`, add an exact Pydantic model named `ConfidenceExplainerPreview` with exact fields `rating`, `supports`, `weakens`, and `limits`. `rating` must allow the exact values `high`, `medium`, `low`, or `None`; `supports`, `weakens`, and `limits` must each default to an empty list of strings. Extend `RunTransparencySummary` with an optional field named `confidence_explainer`. Update the parsing helpers in the same file so `build_run_transparency_summary(...)` can deserialize a nested `traceability.critic.confidence_explainer` object while preserving the existing `critic_overall_confidence`, `critic_blocking_caveats`, `critic_phase_status`, and `report_phase_status` fields. In `frontend/src/lib/api/types.ts`, add a matching TypeScript interface named `ConfidenceExplainerPreview` with exact keys `rating`, `supports`, `weakens`, and `limits`, and extend `RunTransparencySummary` with `confidence_explainer?: ConfidenceExplainerPreview | null`. Extend `tests/test_run_transparency_builders.py` and `tests/test_sprint3_transparency_api.py` so they assert the serialized JSON includes `confidence_explainer.rating`, `supports`, `weakens`, and `limits` when present.</action>
  <acceptance_criteria>`backend/schemas/run_transparency.py` contains `class ConfidenceExplainerPreview`.
`backend/schemas/run_transparency.py` contains `confidence_explainer`.
`backend/schemas/run_transparency.py` contains `supports: list[str]`.
`backend/schemas/run_transparency.py` contains `weakens: list[str]`.
`backend/schemas/run_transparency.py` contains `limits: list[str]`.
`frontend/src/lib/api/types.ts` contains `export interface ConfidenceExplainerPreview`.
`frontend/src/lib/api/types.ts` contains `confidence_explainer?: ConfidenceExplainerPreview | null`.
`tests/test_run_transparency_builders.py` contains `confidence_explainer`.
`tests/test_sprint3_transparency_api.py` contains `confidence_explainer`.
`python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short</automated>
  </verify>
  <done>The existing run-transparency wire now carries a typed safe confidence-explainer preview that the frontend can consume directly.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build grouped support, weakness, and limits rationale from safe traceability data</name>
  <files>backend/agents/traceability_summary.py
tests/test_traceability_summary.py
tests/test_run_transparency_builders.py</files>
  <read_first>.planning/phases/18-confidence-explainer/18-CONTEXT.md
.planning/phases/18-confidence-explainer/18-RESEARCH.md
backend/agents/output_schemas.py
backend/agents/traceability_summary.py
tests/test_traceability_summary.py
tests/test_run_transparency_builders.py</read_first>
  <behavior>
    - The backend must synthesize grouped confidence rationale from already safe critic/report/traceability fields.
    - The grouped rationale must explain what supports the rating, what weakens it, and what evidence limits matter.
    - The explainer contract must not require exposing raw prompts, raw markdown, or unfiltered phase output blobs.
  </behavior>
  <action>In `backend/agents/traceability_summary.py`, add helper logic that builds a `confidence_explainer` object under the critic traceability payload using exact group keys `supports`, `weakens`, and `limits`. Populate `supports` from safe positive signals already present in the traceability layer, such as strong coverage phrasing, successful report/critic phases, non-empty report takeaways, or high-confidence critic outcomes when those cues exist. Populate `weakens` from blocking caveats, weak evidence indicators, low or medium confidence, and explicit degraded/partial-review signals. Populate `limits` from data/coverage-limit language such as missing peer coverage, sparse history, missing manual validation, truncated context, or skipped report/critic conditions when those safe cues exist. Cap each list at a short bounded size, keep strings concise, and persist the exact backend rating in `confidence_explainer.rating` using the current `critic_overall_confidence` value. Extend `tests/test_traceability_summary.py` so one case asserts a `low` or `medium` critic path yields grouped `weakens` and `limits`, and extend `tests/test_run_transparency_builders.py` so a built summary round-trips the grouped explainer data.</action>
  <acceptance_criteria>`backend/agents/traceability_summary.py` contains `confidence_explainer`.
`backend/agents/traceability_summary.py` contains `supports`.
`backend/agents/traceability_summary.py` contains `weakens`.
`backend/agents/traceability_summary.py` contains `limits`.
`tests/test_traceability_summary.py` contains `confidence_explainer`.
`tests/test_traceability_summary.py` contains `weakens`.
`tests/test_traceability_summary.py` contains `limits`.
`tests/test_run_transparency_builders.py` contains `supports`.
`python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py -q --tb=short</automated>
  </verify>
  <done>The backend now produces a compact grouped rationale that can explain confidence posture in chat without exposing raw internals.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short` after both tasks land.
</verification>

<success_criteria>
Phase 18 has a sound first wave once run transparency carries a typed confidence-explainer preview, grouped rationale is built from safe traceability data, and the frontend wire mirror can consume that contract without breaking older confidence fields.
</success_criteria>

<output>
After completion, create `.planning/phases/18-confidence-explainer/18-confidence-explainer-01-SUMMARY.md`
</output>
