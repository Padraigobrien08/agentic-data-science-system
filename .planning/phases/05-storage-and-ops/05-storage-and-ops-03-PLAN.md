---
phase: 05-storage-and-ops
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/config/settings.py
  - backend/models/analysis_run.py
  - backend/models/model_call.py
  - backend/schemas/api_phase_a.py
  - backend/repositories/analysis_run_repository.py
  - backend/repositories/model_call_repository.py
  - backend/maintenance/__init__.py
  - backend/maintenance/retention.py
  - alembic/versions/010_storage_ops_retention.py
  - tests/test_retention_maintenance.py
autonomous: true
requirements:
  - OPER-03
must_haves:
  truths:
    - "Operators can run an explicit dry-run retention workflow and see exactly which runs and model calls are candidates before any mutation is applied."
    - "After retention runs, analysis-run rows and model-call rows still expose audit-visible timestamps instead of disappearing."
    - "Retention policy windows and apply behavior are configured explicitly rather than running implicitly inside normal API or worker traffic."
  artifacts:
    - path: backend/maintenance/retention.py
      provides: "Explicit dry-run or apply retention workflow with JSON reporting"
    - path: alembic/versions/010_storage_ops_retention.py
      provides: "Additive run and model-call retention columns and supporting indexes"
    - path: backend/schemas/api_phase_a.py
      provides: "API-visible retention timestamps for runs and model calls"
    - path: tests/test_retention_maintenance.py
      provides: "Regression coverage for run or model retention schema surfacing, dry-run, apply, and idempotent retention runs"
  key_links:
    - from: backend/maintenance/retention.py
      to: backend/repositories/analysis_run_repository.py
      via: "maintenance workflow selects compactable terminal runs"
      pattern: "list_compaction_candidates|compacted_at"
    - from: backend/maintenance/retention.py
      to: backend/repositories/model_call_repository.py
      via: "maintenance workflow redacts raw model payload JSON"
      pattern: "payloads_redacted_at|list_payload_redaction_candidates"
---

<objective>
Add the run and model-call retention foundation: explicit policy settings, additive audit-preserving schema, and the maintenance workflow that compacts or redacts retained history.

Purpose: satisfy the first half of `OPER-03` without hard-deleting audit rows, so Phase 05 can bound payload-heavy run and model history while preserving traceability.
Output: retention settings, additive timestamps for compacted runs and redacted model calls, repository candidate selectors, an operator-invoked maintenance command, and retention regressions.
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
@.planning/phases/05-storage-and-ops/05-CONTEXT.md
@.planning/phases/05-storage-and-ops/05-RESEARCH.md
@.planning/phases/05-storage-and-ops/05-VALIDATION.md
@.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md
@.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md
@backend/config/settings.py
@backend/models/analysis_run.py
@backend/models/model_call.py
@backend/schemas/api_phase_a.py
@backend/repositories/analysis_run_repository.py
@backend/repositories/model_call_repository.py
@backend/services/recorded_chat_completion_service.py

<interfaces>
From `backend/models/analysis_run.py`:
```python
class AnalysisRun(Base):
    input_payload_json: Mapped[dict | list | None]
    output_payload_json: Mapped[dict | list | None]
    finished_at: Mapped[datetime | None]
```

From `backend/models/model_call.py`:
```python
class ModelCall(Base):
    analysis_run_id: Mapped[uuid.UUID | None]
    request_payload_json: Mapped[dict | list | None]
    response_payload_json: Mapped[dict | list | None]
    created_at: Mapped[datetime]
```

From `backend/schemas/api_phase_a.py`:
```python
class AnalysisRunDetailResponse(AnalysisRunSummary):
    input_payload_json: dict | list | None = None
    output_payload_json: dict | list | None = None
    meta_json: dict | list | None = None

class ModelCallApiItem(BaseModel):
    request_payload_json: dict | list | None = None
    response_payload_json: dict | list | None = None
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add retention-state schema, policy settings, and response-surface timestamps</name>
  <files>backend/config/settings.py
backend/models/analysis_run.py
backend/models/model_call.py
backend/schemas/api_phase_a.py
alembic/versions/010_storage_ops_retention.py
tests/test_retention_maintenance.py</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md
.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md
backend/config/settings.py
backend/models/analysis_run.py
backend/models/model_call.py
backend/schemas/api_phase_a.py</read_first>
  <behavior>
    - Per D-05, retention policy windows are explicit settings under the `EDGAR_BACKEND_` env prefix.
    - Per D-06, additive timestamps mark compacted runs and redacted model payloads without deleting the rows themselves.
    - The default owner-scoped response surfaces remain intact, but they now expose run and model retention timestamps so audit tooling can explain what was intentionally trimmed.
  </behavior>
  <action>Extend `backend/config/settings.py` with the exact integer settings `retention_run_payload_days`, `retention_model_payload_days`, `retention_artifact_blob_days`, and `retention_batch_size`, documented so `0` disables that tier. Add nullable `compacted_at` to `AnalysisRun` and `payloads_redacted_at` to `ModelCall`. Update `backend/schemas/api_phase_a.py` so `AnalysisRunDetailResponse` and `ModelCallApiItem` surface those timestamps additively without changing auth or payload gating semantics. Create Alembic revision `010_storage_ops_retention.py` that adds `compacted_at` and `payloads_redacted_at` plus supporting selection indexes for `analysis_runs.finished_at` and `model_calls.created_at`; do not add artifact-blob retention columns in this plan. Create `tests/test_retention_maintenance.py` with a first slice of tests that asserts the new settings fields exist, the ORM models expose the run and model retention timestamps, and the API serializers retain those timestamps when rows are model-validated.</action>
  <acceptance_criteria>`backend/config/settings.py` contains `retention_run_payload_days`.
`backend/config/settings.py` contains `retention_model_payload_days`.
`backend/config/settings.py` contains `retention_artifact_blob_days`.
`backend/config/settings.py` contains `retention_batch_size`.
`backend/models/analysis_run.py` contains `compacted_at`.
`backend/models/model_call.py` contains `payloads_redacted_at`.
`backend/schemas/api_phase_a.py` contains `compacted_at`.
`backend/schemas/api_phase_a.py` contains `payloads_redacted_at`.
`alembic/versions/010_storage_ops_retention.py` exists.
`tests/test_retention_maintenance.py` contains `compacted_at`.
`tests/test_retention_maintenance.py` contains `payloads_redacted_at`.
`tests/test_retention_maintenance.py` contains `serializer`.
`tests/test_retention_maintenance.py` contains `settings`.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_retention_maintenance.py -k "settings or schema or serializer" -q --tb=short</automated>
  </verify>
  <done>The run and model retention data model, env settings, migration, and API-facing timestamps exist and are regression-covered.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add repository selectors and the explicit retention maintenance workflow</name>
  <files>backend/repositories/analysis_run_repository.py
backend/repositories/model_call_repository.py
backend/maintenance/__init__.py
backend/maintenance/retention.py
tests/test_retention_maintenance.py</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
backend/repositories/analysis_run_repository.py
backend/repositories/model_call_repository.py
backend/maintenance/retention.py
tests/test_retention_maintenance.py
backend/services/recorded_chat_completion_service.py</read_first>
  <behavior>
    - Per D-05, the maintenance workflow can select run-payload compaction and model-payload redaction candidates separately.
    - Per D-06, apply mode clears only payload-heavy run or model fields and stamps explicit retention timestamps rather than deleting rows.
    - Per D-08, the workflow is operator-invoked with dry-run default, `--apply` opt-in, and JSON reporting; it does not run implicitly inside request or worker paths.
  </behavior>
  <action>Extend the repositories with explicit selectors named or equivalent to `list_compaction_candidates` and `list_payload_redaction_candidates`, scoped to `analysis_run_id`-backed history in this plan. Create `backend/maintenance/__init__.py` plus `backend/maintenance/retention.py` so `python -m backend.maintenance.retention` works with argparse flags `--dry-run`, `--apply`, `--limit`, and `--json`. In apply mode, set `analysis_runs.input_payload_json = None`, `analysis_runs.output_payload_json = None`, and `analysis_runs.compacted_at = now`; set `model_calls.request_payload_json = None`, `model_calls.response_payload_json = None`, and `model_calls.payloads_redacted_at = now`. Do not add artifact blob deletion behavior in this plan; that follow-on work lands in `05-04` per D-07. Extend `tests/test_retention_maintenance.py` with dry-run no-op coverage, apply-mode mutation coverage, idempotent second-run coverage, and JSON report assertions for the exact top-level keys `dry_run`, `run_candidates`, `model_call_candidates`, `runs_compacted`, `model_calls_redacted`, and `errors`.</action>
  <acceptance_criteria>`backend/repositories/analysis_run_repository.py` contains `list_compaction_candidates`.
`backend/repositories/model_call_repository.py` contains `list_payload_redaction_candidates`.
`backend/maintenance/retention.py` contains `--dry-run`.
`backend/maintenance/retention.py` contains `--apply`.
`backend/maintenance/retention.py` contains `--limit`.
`backend/maintenance/retention.py` contains `--json`.
`backend/maintenance/retention.py` contains `runs_compacted`.
`backend/maintenance/retention.py` contains `model_calls_redacted`.
`tests/test_retention_maintenance.py` contains `dry_run`.
`tests/test_retention_maintenance.py` contains `runs_compacted`.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_retention_maintenance.py -q --tb=short</automated>
  </verify>
  <done>The explicit retention workflow now selects, reports, and applies run or model compaction and redaction without deleting audit rows.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_retention_maintenance.py -k "settings or schema or serializer" -q --tb=short` after Task 1, then `python3 -m pytest tests/test_retention_maintenance.py -q --tb=short` after Task 2 so the retention foundation stays executable at each step.
</verification>

<success_criteria>
Phase 05 has a viable run and model retention foundation once the data model exposes explicit retention state, operators can dry-run or apply compaction and redaction explicitly, and regression tests prove that audit rows survive the workflow.
</success_criteria>

<output>
After completion, create `.planning/phases/05-storage-and-ops/05-storage-and-ops-03-SUMMARY.md`
</output>
