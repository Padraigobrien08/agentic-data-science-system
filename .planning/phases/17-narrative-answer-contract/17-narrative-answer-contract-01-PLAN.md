---
phase: 17-narrative-answer-contract
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/agents/output_schemas.py
  - backend/agents/phase_outputs.py
  - backend/agents/traceability_summary.py
  - backend/schemas/run_transparency.py
  - backend/api/routes/runs.py
  - frontend/src/lib/api/types.ts
  - tests/test_run_transparency_builders.py
  - tests/test_sprint3_transparency_api.py
autonomous: true
requirements:
  - ANSR-01
  - ANSR-02
must_haves:
  truths:
    - "Run transparency exposes a typed backend-safe narrative answer preview instead of only takeaway and caveat fragments."
    - "Successful report output and limited-support fallback both map onto the same narrative preview contract with explicit mode and fallback reason semantics."
    - "The run detail API and frontend wire mirror surface the narrative preview without requiring chat to read raw `output_payload_json` or markdown in the browser."
  artifacts:
    - path: backend/schemas/run_transparency.py
      provides: "Typed narrative preview contract on the existing safe transparency surface"
    - path: backend/agents/traceability_summary.py
      provides: "Narrative preview assembly for both full and partial-answer modes"
    - path: tests/test_run_transparency_builders.py
      provides: "Backend regression coverage for narrative preview construction and fallback behavior"
  key_links:
    - from: backend/agents/output_schemas.py
      to: backend/agents/traceability_summary.py
      via: "Report-agent structured output feeds the safe narrative preview fields persisted into traceability"
      pattern: "narrative_thesis|narrative_whats_happening|narrative_why_we_think_that|narrative_what_weakens_claim"
    - from: backend/agents/traceability_summary.py
      to: backend/schemas/run_transparency.py
      via: "Traceability becomes the source of truth for the typed `narrative_answer` preview exposed to chat"
      pattern: "narrative_answer|mode|fallback_reason|sections"
    - from: backend/api/routes/runs.py
      to: frontend/src/lib/api/types.ts
      via: "Run-detail responses surface the new transparency field through the existing include-transparency contract"
      pattern: "RunTransparencySummary|narrative_answer|include_transparency"
---

<objective>
Define the backend-safe narrative answer contract and expose it through the current run-transparency seam before any frontend migration begins.

Purpose: satisfy the contract half of `ANSR-01` and `ANSR-02` by making thesis, support, and watchouts first-class safe-preview fields instead of summary-card fragments.
Output: report/traceability schema updates, run-transparency wire updates, and backend regression coverage.
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
@.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
@.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
@.planning/phases/17-narrative-answer-contract/17-VALIDATION.md
@.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
@backend/agents/output_schemas.py
@backend/agents/phase_outputs.py
@backend/agents/traceability_summary.py
@backend/schemas/run_transparency.py
@backend/api/routes/runs.py
@frontend/src/lib/api/types.ts
@tests/test_run_transparency_builders.py
@tests/test_sprint3_transparency_api.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend report and traceability output to author a typed narrative preview</name>
  <files>backend/agents/output_schemas.py
backend/agents/phase_outputs.py
backend/agents/traceability_summary.py
tests/test_run_transparency_builders.py</files>
  <read_first>.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
.planning/phases/17-narrative-answer-contract/17-VALIDATION.md
.planning/phases/17-narrative-answer-contract/17-UI-SPEC.md
backend/agents/output_schemas.py
backend/agents/phase_outputs.py
backend/agents/traceability_summary.py
tests/test_run_transparency_builders.py</read_first>
  <behavior>
    - Successful report-agent output must author a structured narrative preview that carries the thesis plus the three Phase 17 prose sections.
    - Runs with weak or missing support must still produce a typed `partial` narrative preview instead of dropping to generic success text.
    - Traceability must remain the backend-safe chat preview surface; the contract must not require frontend markdown parsing.
  </behavior>
  <action>In `backend/agents/output_schemas.py`, extend `ReportAgentLLMOutput` with four exact structured prose fields: `narrative_thesis`, `narrative_whats_happening`, `narrative_why_we_think_that`, and `narrative_what_weakens_claim`. In `backend/agents/phase_outputs.py`, persist those fields into `build_report_phase_output(...)` under a `narrative_answer` object with exact keys `thesis`, `whats_happening`, `why_we_think_that`, and `what_weakens_claim`. In `backend/agents/traceability_summary.py`, extend `build_runtime_traceability_bundle(...)` so `full["report"]` always includes a typed `narrative_answer` object with exact keys `mode`, `thesis`, `sections`, and `fallback_reason`. For successful report output, set `mode` to `full`, set `fallback_reason` to `None`, and emit up to three section rows with exact headings `What's happening`, `Why we think that`, and `What weakens the claim` using the new report fields. If the report phase is skipped, failed, or returns blank narrative fields, synthesize a `partial` preview instead: use the strongest safe fallback thesis from `key_takeaways_preview` or critic-safe phrasing, emit only the non-empty `What weakens the claim` section, and set `fallback_reason` to the exact string `limited_evidence` when the report ran but support is weak, or `report_unavailable` when the report phase did not produce usable narrative fields. Extend `tests/test_run_transparency_builders.py` to assert the new `narrative_answer.mode`, `narrative_answer.thesis`, `narrative_answer.sections`, and `fallback_reason` behavior for both a successful and a partial run path.</action>
  <acceptance_criteria>`backend/agents/output_schemas.py` contains `narrative_thesis`.
`backend/agents/output_schemas.py` contains `narrative_whats_happening`.
`backend/agents/output_schemas.py` contains `narrative_why_we_think_that`.
`backend/agents/output_schemas.py` contains `narrative_what_weakens_claim`.
`backend/agents/phase_outputs.py` contains `narrative_answer`.
`backend/agents/traceability_summary.py` contains `"mode": "full"` or `mode": "full"`.
`backend/agents/traceability_summary.py` contains `"partial"` or `mode": "partial"`.
`backend/agents/traceability_summary.py` contains `limited_evidence`.
`backend/agents/traceability_summary.py` contains `report_unavailable`.
`tests/test_run_transparency_builders.py` contains `narrative_answer`.
`tests/test_run_transparency_builders.py` contains `limited_evidence`.
`python3 -m pytest tests/test_run_transparency_builders.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_run_transparency_builders.py -q --tb=short</automated>
  </verify>
  <done>The backend can now author a safe narrative preview for both strong-support and limited-support runs without requiring the frontend to parse markdown.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Surface the narrative preview through run transparency and the frontend wire mirror</name>
  <files>backend/schemas/run_transparency.py
backend/api/routes/runs.py
frontend/src/lib/api/types.ts
tests/test_sprint3_transparency_api.py</files>
  <read_first>.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
backend/schemas/run_transparency.py
backend/api/routes/runs.py
frontend/src/lib/api/types.ts
tests/test_sprint3_transparency_api.py</read_first>
  <behavior>
    - `GET /v1/runs/{id}?include_transparency=true` must expose the typed narrative preview on the existing run-transparency response.
    - The frontend wire mirror must model the same nested contract and stay additive for older responses.
    - The API surface must stay backward-compatible for callers that still read the older transparency fields.
  </behavior>
  <action>In `backend/schemas/run_transparency.py`, add exact Pydantic models `NarrativeAnswerSectionPreview` and `NarrativeAnswerPreview`, then extend `RunTransparencySummary` with an optional field named `narrative_answer`. The nested preview must expose exact keys `mode`, `thesis`, `sections`, and `fallback_reason`; each section row must expose exact keys `heading` and `body`. Update `build_run_transparency_summary(...)` to read the new `traceability.report.narrative_answer` object and map it into the typed field while keeping `report_key_takeaways_preview`, `critic_blocking_caveats`, and confidence/status fields intact. In `frontend/src/lib/api/types.ts`, add matching TypeScript interfaces named `NarrativeAnswerSectionPreview` and `NarrativeAnswerPreview`, then extend `RunTransparencySummary` with `narrative_answer?: NarrativeAnswerPreview | null`. In `tests/test_sprint3_transparency_api.py`, extend the run-detail include-transparency assertions so the serialized JSON includes `narrative_answer.mode`, `narrative_answer.thesis`, and at least one `sections` item when present.</action>
  <acceptance_criteria>`backend/schemas/run_transparency.py` contains `class NarrativeAnswerSectionPreview`.
`backend/schemas/run_transparency.py` contains `class NarrativeAnswerPreview`.
`backend/schemas/run_transparency.py` contains `narrative_answer`.
`backend/schemas/run_transparency.py` contains `fallback_reason`.
`frontend/src/lib/api/types.ts` contains `export interface NarrativeAnswerPreview`.
`frontend/src/lib/api/types.ts` contains `export interface NarrativeAnswerSectionPreview`.
`frontend/src/lib/api/types.ts` contains `narrative_answer?: NarrativeAnswerPreview | null`.
`tests/test_sprint3_transparency_api.py` contains `narrative_answer`.
`tests/test_sprint3_transparency_api.py` contains `thesis`.
`python3 -m pytest tests/test_sprint3_transparency_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_sprint3_transparency_api.py -q --tb=short</automated>
  </verify>
  <done>The existing run-transparency API now carries a typed narrative preview that the frontend can consume without breaking older transparency fields.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short` after both tasks land.
</verification>

<success_criteria>
Phase 17 has a sound first wave once run transparency carries a typed safe narrative preview, distinguishes `full` and `partial` answer modes, and exposes that contract to the frontend without requiring raw payload reads.
</success_criteria>

<output>
After completion, create `.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-01-SUMMARY.md`
</output>
