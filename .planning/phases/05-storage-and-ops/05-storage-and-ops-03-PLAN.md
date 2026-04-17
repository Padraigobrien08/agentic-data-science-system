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
  - backend/models/artifact.py
  - backend/schemas/api_phase_a.py
  - backend/repositories/analysis_run_repository.py
  - backend/repositories/model_call_repository.py
  - backend/repositories/artifact_repository.py
  - backend/maintenance/__init__.py
  - backend/maintenance/retention.py
  - backend/api/routes/artifacts.py
  - alembic/versions/010_storage_ops_retention.py
  - tests/test_retention_maintenance.py
  - tests/test_artifact_content_delivery.py
  - docs/local-stack.md
  - docs/artifact-delivery.md
autonomous: true
requirements:
  - OPER-03
must_haves:
  truths:
    - "Operators can run an explicit dry-run retention workflow and see exactly what would be compacted, redacted, or pruned before any data changes are made."
    - "After retention is applied, run rows, model-call rows, and artifact rows remain auditable through explicit timestamps instead of disappearing or looking silently corrupted."
    - "Retention-pruned artifact bytes return an explicit expired policy response instead of the same error used for accidental storage loss."
  artifacts:
    - path: backend/maintenance/retention.py
      provides: "Explicit dry-run or apply retention workflow with JSON reporting"
    - path: alembic/versions/010_storage_ops_retention.py
      provides: "Additive retention-state columns and supporting indexes"
    - path: backend/schemas/api_phase_a.py
      provides: "API-visible retention timestamps for runs, model calls, and artifacts"
    - path: tests/test_retention_maintenance.py
      provides: "Regression coverage for dry-run, apply, idempotence, and API-visible retention markers"
    - path: backend/api/routes/artifacts.py
      provides: "Explicit `410` behavior for retention-pruned artifact blobs"
  key_links:
    - from: backend/maintenance/retention.py
      to: backend/repositories/analysis_run_repository.py
      via: "maintenance workflow selects compactable terminal runs"
      pattern: "list_compaction_candidates|compacted_at"
    - from: backend/maintenance/retention.py
      to: backend/repositories/model_call_repository.py
      via: "maintenance workflow redacts raw model payload JSON"
      pattern: "payloads_redacted_at|list_payload_redaction_candidates"
    - from: backend/maintenance/retention.py
      to: backend/repositories/artifact_repository.py
      via: "maintenance workflow deletes blob bytes only after a prune candidate is selected"
      pattern: "blob_deleted_at|list_blob_prune_candidates|delete_at_uri"
    - from: backend/api/routes/artifacts.py
      to: docs/artifact-delivery.md
      via: "artifact delivery documents and enforces the retention-expired content semantics"
      pattern: "410|Artifact content expired by retention policy"
---

<objective>
Add explicit retention controls that compact payload-heavy history while preserving an auditable record of what existed.

Purpose: satisfy `OPER-03` through additive schema markers, an operator-invoked maintenance workflow, and delivery semantics that distinguish policy-driven pruning from accidental storage loss.
Output: retention settings, additive tombstone or compaction columns, a `python -m backend.maintenance.retention` command with dry-run reporting, and tests or docs for the new retention-visible behavior.
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
@backend/models/artifact.py
@backend/schemas/api_phase_a.py
@backend/api/routes/artifacts.py
@backend/repositories/analysis_run_repository.py
@backend/repositories/model_call_repository.py
@backend/repositories/artifact_repository.py
@docs/local-stack.md
@docs/artifact-delivery.md
@tests/test_artifact_content_delivery.py

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

From `backend/models/artifact.py`:
```python
class Artifact(Base):
    analysis_run_id: Mapped[uuid.UUID | None]
    storage_uri: Mapped[str]
    byte_size: Mapped[int | None]
    content_sha256: Mapped[str | None]
    created_at: Mapped[datetime]
```

From `backend/schemas/api_phase_a.py`:
```python
class AnalysisRunDetailResponse(AnalysisRunSummary):
    input_payload_json: dict | list | None = None
    output_payload_json: dict | list | None = None
    meta_json: dict | list | None = None

class ArtifactDetailResponse(ArtifactMetadata):
    meta_json: dict | list | None = None

class ModelCallApiItem(BaseModel):
    request_payload_json: dict | list | None = None
    response_payload_json: dict | list | None = None
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add additive retention-state schema, settings, and the explicit maintenance workflow</name>
  <files>backend/config/settings.py
backend/models/analysis_run.py
backend/models/model_call.py
backend/models/artifact.py
backend/schemas/api_phase_a.py
backend/repositories/analysis_run_repository.py
backend/repositories/model_call_repository.py
backend/repositories/artifact_repository.py
backend/maintenance/__init__.py
backend/maintenance/retention.py
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
backend/models/artifact.py
backend/schemas/api_phase_a.py
backend/repositories/analysis_run_repository.py
backend/repositories/model_call_repository.py
backend/repositories/artifact_repository.py
backend/db/session.py
backend/worker/__main__.py
backend/dev/llm_context_compare.py</read_first>
  <behavior>
    - Per D-05, operators can configure explicit retention windows for run payload compaction, raw model payload redaction, and artifact blob pruning.
    - Per D-06 and D-07, retained rows keep audit-visible timestamps and core metadata even after raw payloads or blob bytes age out.
    - Per D-08, retention runs only through an explicit maintenance command that defaults to dry-run and emits a report before apply mode mutates anything.
  </behavior>
  <action>Extend `backend/config/settings.py` with the exact integer settings `retention_run_payload_days`, `retention_model_payload_days`, `retention_artifact_blob_days`, and `retention_batch_size`, all under the `EDGAR_BACKEND_` env prefix and documented so `0` disables that retention tier. Add additive nullable columns `compacted_at` to `AnalysisRun`, `payloads_redacted_at` to `ModelCall`, and `blob_deleted_at` to `Artifact`, then expose those timestamps in `backend/schemas/api_phase_a.py` so existing run, model-call, and artifact responses surface retention state without changing auth gates. Create Alembic revision `010_storage_ops_retention.py` that adds those three columns plus indexes on `analysis_runs.finished_at`, `model_calls.created_at`, and `artifacts.created_at` if not already present. Extend the repositories with explicit candidate selectors named or equivalent to `list_compaction_candidates`, `list_payload_redaction_candidates`, and `list_blob_prune_candidates`, scoped only to `analysis_run_id`-backed history in this phase. Create `backend/maintenance/retention.py` and `backend/maintenance/__init__.py` so `python -m backend.maintenance.retention` works with argparse flags `--dry-run` (default behavior), `--apply`, `--limit`, and `--json`. In apply mode, set `analysis_runs.input_payload_json = None`, `analysis_runs.output_payload_json = None`, and `analysis_runs.compacted_at = now`; set `model_calls.request_payload_json = None`, `model_calls.response_payload_json = None`, and `model_calls.payloads_redacted_at = now`; call `delete_at_uri()` for artifact blobs and set `artifacts.blob_deleted_at = now` only after delete succeeds. Keep `storage_uri`, `byte_size`, `content_sha256`, and existing provenance `meta_json` keys intact for pruned artifacts. Emit a JSON report with the exact top-level keys `dry_run`, `run_candidates`, `model_call_candidates`, `artifact_candidates`, `runs_compacted`, `model_calls_redacted`, `artifact_blobs_pruned`, and `errors`. Add `tests/test_retention_maintenance.py` covering dry-run no-op behavior, apply-mode compaction or redaction, idempotent second apply runs, and API-visible `compacted_at`, `payloads_redacted_at`, and `blob_deleted_at` fields on seeded rows.</action>
  <acceptance_criteria>`backend/config/settings.py` contains `retention_run_payload_days`.
`backend/config/settings.py` contains `retention_model_payload_days`.
`backend/config/settings.py` contains `retention_artifact_blob_days`.
`backend/config/settings.py` contains `retention_batch_size`.
`backend/models/analysis_run.py` contains `compacted_at`.
`backend/models/model_call.py` contains `payloads_redacted_at`.
`backend/models/artifact.py` contains `blob_deleted_at`.
`backend/maintenance/retention.py` contains `--dry-run`.
`backend/maintenance/retention.py` contains `--apply`.
`backend/maintenance/retention.py` contains `--json`.
`backend/maintenance/retention.py` contains `runs_compacted`.
`backend/maintenance/retention.py` contains `model_calls_redacted`.
`backend/maintenance/retention.py` contains `artifact_blobs_pruned`.
`alembic/versions/010_storage_ops_retention.py` exists.
`tests/test_retention_maintenance.py` contains `compacted_at`.
`tests/test_retention_maintenance.py` contains `payloads_redacted_at`.
`tests/test_retention_maintenance.py` contains `blob_deleted_at`.
`python3 -m pytest tests/test_retention_maintenance.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_retention_maintenance.py -q --tb=short</automated>
  </verify>
  <done>The codebase has additive retention-state columns, configurable policy windows, an explicit dry-run or apply maintenance command, and regressions that prove audit rows survive compaction or pruning.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Distinguish retention-pruned artifact content from accidental storage loss and document the operator workflow</name>
  <files>backend/api/routes/artifacts.py
tests/test_artifact_content_delivery.py
docs/local-stack.md
docs/artifact-delivery.md</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
backend/api/routes/artifacts.py
backend/models/artifact.py
backend/schemas/api_phase_a.py
backend/maintenance/retention.py
tests/test_artifact_content_delivery.py
docs/local-stack.md
docs/artifact-delivery.md</read_first>
  <behavior>
    - Per D-06 and D-07, pruned artifact blobs are visibly marked as retention-expired rather than treated like a generic missing-file error.
    - Per D-08, the operator docs show the exact dry-run and apply commands plus the retention env vars needed to invoke the maintenance workflow safely.
    - Missing blobs without a retention tombstone still follow the current generic `404` or `502` paths so real storage bugs are not misclassified as policy actions.
  </behavior>
  <action>Update `backend/api/routes/artifacts.py` so both `/v1/artifacts/{artifact_id}/content` and `/v1/artifacts/{artifact_id}/preview` short-circuit with `HTTPException(status_code=410, detail="Artifact content expired by retention policy")` whenever `row.blob_deleted_at` is non-null, before attempting `open_reader(...)`. Keep the existing `404` path for blobs that are missing but do not have a retention tombstone. Extend `tests/test_artifact_content_delivery.py` with a tombstoned artifact case that sets `blob_deleted_at`, asserts `410`, and confirms the JSON detail does not leak storage paths. Update `docs/local-stack.md` with a retention section naming the exact env vars `EDGAR_BACKEND_RETENTION_RUN_PAYLOAD_DAYS`, `EDGAR_BACKEND_RETENTION_MODEL_PAYLOAD_DAYS`, `EDGAR_BACKEND_RETENTION_ARTIFACT_BLOB_DAYS`, and `EDGAR_BACKEND_RETENTION_BATCH_SIZE`, plus the exact commands `python -m backend.maintenance.retention --dry-run --json` and `python -m backend.maintenance.retention --apply --json`. Update `docs/artifact-delivery.md` so content and preview document `410` for retention-pruned blobs distinctly from generic missing-storage `404` behavior.</action>
  <acceptance_criteria>`backend/api/routes/artifacts.py` contains `status_code=410`.
`backend/api/routes/artifacts.py` contains `Artifact content expired by retention policy`.
`tests/test_artifact_content_delivery.py` contains `status_code == 410`.
`tests/test_artifact_content_delivery.py` contains `Artifact content expired by retention policy`.
`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_RUN_PAYLOAD_DAYS`.
`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_MODEL_PAYLOAD_DAYS`.
`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_ARTIFACT_BLOB_DAYS`.
`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_BATCH_SIZE`.
`docs/local-stack.md` contains `python -m backend.maintenance.retention --dry-run --json`.
`docs/local-stack.md` contains `python -m backend.maintenance.retention --apply --json`.
`docs/artifact-delivery.md` contains `410`.
`docs/artifact-delivery.md` contains `Artifact content expired by retention policy`.
`python3 -m pytest tests/test_retention_maintenance.py tests/test_artifact_content_delivery.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_retention_maintenance.py tests/test_artifact_content_delivery.py -q --tb=short</automated>
  </verify>
  <done>Retention-pruned artifact bytes now have an explicit delivery contract and the operator runbook documents how to preview, apply, and understand the retention workflow safely.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_retention_maintenance.py -q --tb=short` after Task 1, then `python3 -m pytest tests/test_retention_maintenance.py tests/test_artifact_content_delivery.py -q --tb=short` after Task 2 so the maintenance workflow and artifact-delivery semantics stay aligned.
</verification>

<success_criteria>
Phase 05 closes its retention boundary once operators can explicitly dry-run or apply policy-driven compaction, the remaining rows still show what was retained versus pruned, and pruned artifact content is distinguishable from accidental storage breakage.
</success_criteria>

<output>
After completion, create `.planning/phases/05-storage-and-ops/05-storage-and-ops-03-SUMMARY.md`
</output>
