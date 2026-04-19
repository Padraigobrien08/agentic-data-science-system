---
phase: 17-narrative-answer-contract
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/agents/output_schemas.py
  - backend/agents/phase_outputs.py
  - backend/agents/prompts/report/1.2.0.md
  - backend/agents/traceability_summary.py
  - backend/agents/traceable_analysis_pipeline.py
  - backend/config/settings.py
  - backend/schemas/run_transparency.py
  - frontend/src/lib/api/types.ts
  - tests/test_phase_outputs.py
  - tests/test_run_transparency_builders.py
  - tests/test_sprint3_transparency_api.py
  - tests/test_traceability_summary.py
  - tests/test_traceable_pipeline.py
autonomous: true
requirements:
  - ANSR-01
  - ANSR-02
must_haves:
  truths:
    - "GET /v1/runs/{id}?include_transparency=true returns a safe `narrative_answer` preview with `mode`, `thesis`, and bounded section data."
    - "Successful report-backed runs can expose a full narrative preview without requiring chat to read raw payload JSON."
    - "When evidence is limited or the report preview is incomplete, the backend still emits a partial narrative preview with an explicit fallback reason."
  artifacts:
    - path: backend/schemas/run_transparency.py
      provides: "Typed `NarrativeAnswerPreview` and `NarrativeAnswerSection` models on `RunTransparencySummary`."
    - path: backend/agents/traceability_summary.py
      provides: "Backend helper that derives a full or partial `narrative_answer` preview from report results and critic caveats."
    - path: frontend/src/lib/api/types.ts
      provides: "Frontend wire mirror for the new safe narrative preview contract."
  key_links:
    - "backend/agents/traceable_analysis_pipeline.py persists report results that backend/agents/traceability_summary.py converts into `traceability.report.narrative_answer`."
    - "backend/schemas/run_transparency.py and frontend/src/lib/api/types.ts use the same `narrative_answer` field names so chat can consume the safe preview without raw payload access."
---

<objective>
Define the backend-safe narrative answer contract for chat and expose it through the existing transparency seam.

Purpose: satisfy the contract half of `ANSR-01` and the fallback semantics required by `ANSR-02` without creating a new endpoint or bypassing the safe preview boundary.
Output: a typed `narrative_answer` preview on run transparency, backed by report-agent output when available and partial fallback generation when support is limited.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
@.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
@backend/agents/output_schemas.py
@backend/agents/traceability_summary.py
@backend/agents/traceable_analysis_pipeline.py
@backend/schemas/run_transparency.py
@backend/api/routes/runs.py
@frontend/src/lib/api/types.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend the report-side narrative contract and persisted traceability preview</name>
  <files>backend/agents/output_schemas.py
backend/agents/phase_outputs.py
backend/agents/prompts/report/1.2.0.md
backend/agents/traceability_summary.py
backend/agents/traceable_analysis_pipeline.py
backend/config/settings.py
tests/test_phase_outputs.py
tests/test_traceability_summary.py
tests/test_traceable_pipeline.py</files>
  <read_first>.planning/ROADMAP.md
.planning/REQUIREMENTS.md
.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
.planning/phases/17-narrative-answer-contract/17-RESEARCH.md
backend/agents/output_schemas.py
backend/agents/phase_outputs.py
backend/agents/prompts/report/1.1.0.md
backend/agents/traceability_summary.py
backend/agents/traceable_analysis_pipeline.py
backend/config/settings.py
tests/test_phase_outputs.py
tests/test_traceability_summary.py
tests/test_traceable_pipeline.py</read_first>
  <behavior>
    - Full narrative previews follow D-01 and D-02: one thesis plus short `What’s happening`, `Why we think that`, and `What weakens the claim` sections.
    - The report prompt and schema target the analyst-memo voice from D-07 and D-08 and the bounded 120-220 word default from D-09.
    - Limited-support cases follow D-05 and D-06 by producing `mode="partial"` with a concrete limitation statement and fallback reason instead of generic success text.
  </behavior>
  <action>Create `backend/agents/prompts/report/1.2.0.md` and switch `backend/config/settings.py` default `agent_report_prompt_version` to `1.2.0`. Extend `ReportAgentLLMOutput` with a bounded nested narrative preview object that can carry `mode`, `thesis`, ordered section rows, `limitation_statement`, and `fallback_reason`. Update `build_report_phase_output`, `traceable_analysis_pipeline.py`, and `traceability_summary.py` so successful report runs persist the structured narrative preview into safe traceability metadata, while incomplete or weakly supported runs synthesize a `partial` preview from report takeaways, orchestration outcome text, and critic caveats instead of failing the run. Keep existing `key_takeaways_preview`, prompt-version persistence, and report markdown behavior intact for auditability and compatibility.</action>
  <acceptance_criteria>`backend/agents/prompts/report/1.2.0.md` exists and declares version `1.2.0`.
`backend/config/settings.py` defaults `agent_report_prompt_version` to `1.2.0`.
`backend/agents/traceability_summary.py` contains narrative-preview logic that can emit both `mode=\"full\"` and `mode=\"partial\"`.
`python3 -m pytest tests/test_phase_outputs.py tests/test_traceability_summary.py tests/test_traceable_pipeline.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_phase_outputs.py tests/test_traceability_summary.py tests/test_traceable_pipeline.py -q --tb=short</automated>
  </verify>
  <done>Report-backed runs persist a structured narrative preview, and weak-support runs still yield a concrete partial preview without breaking existing report markdown storage.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Surface the safe narrative preview through run transparency and the frontend wire contract</name>
  <files>backend/schemas/run_transparency.py
frontend/src/lib/api/types.ts
tests/test_run_transparency_builders.py
tests/test_sprint3_transparency_api.py</files>
  <read_first>.planning/ROADMAP.md
.planning/REQUIREMENTS.md
.planning/phases/17-narrative-answer-contract/17-CONTEXT.md
backend/schemas/run_transparency.py
backend/schemas/api_phase_a.py
backend/api/routes/runs.py
frontend/src/lib/api/types.ts
tests/test_run_transparency_builders.py
tests/test_sprint3_transparency_api.py</read_first>
  <behavior>
    - `RunTransparencySummary` exposes the new `narrative_answer` preview while retaining the current takeaways, caveats, and confidence slices for compatibility.
    - The API contract stays additive on `GET /v1/runs/{id}?include_transparency=true`; no new chat-only endpoint is introduced per D-03 and D-04.
    - The frontend wire type mirrors the backend field names exactly so downstream chat work can consume the safe preview without extra translation.
  </behavior>
  <action>Add `NarrativeAnswerSection` and `NarrativeAnswerPreview` models to `backend/schemas/run_transparency.py`, parse the persisted traceability narrative data into `RunTransparencySummary.narrative_answer`, and leave the existing transparency fields untouched for brownfield safety. Mirror the same types and field names in `frontend/src/lib/api/types.ts`. Extend the backend builder and API tests to cover a full narrative preview, a `partial` fallback preview, and additive compatibility with the existing transparency payload.</action>
  <acceptance_criteria>`backend/schemas/run_transparency.py` defines `NarrativeAnswerPreview` and `RunTransparencySummary.narrative_answer`.
`frontend/src/lib/api/types.ts` defines matching `NarrativeAnswerPreview` and `NarrativeAnswerSection` interfaces.
`python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short</automated>
  </verify>
  <done>The run-detail transparency payload exposes a backend-authored narrative preview contract that frontend code can consume directly.</done>
</task>

</tasks>

<verification>
Run the two backend slices after each task, then rerun both together before marking the plan complete:
`python3 -m pytest tests/test_phase_outputs.py tests/test_traceability_summary.py tests/test_traceable_pipeline.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short`
</verification>

<success_criteria>
Phase 17 has a stable, additive backend narrative-preview contract. Full runs expose thesis + sections through transparency, and limited-support runs expose a partial answer with explicit weakness/fallback metadata instead of vague placeholder text.
</success_criteria>

<output>
After completion, create `.planning/phases/17-narrative-answer-contract/17-narrative-answer-contract-01-SUMMARY.md`
</output>
