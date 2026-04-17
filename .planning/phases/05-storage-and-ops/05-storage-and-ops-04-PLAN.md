---
phase: 05-storage-and-ops
plan: 04
type: execute
wave: 2
depends_on:
  - 05-03
files_modified:
  - backend/models/artifact.py
  - backend/schemas/api_phase_a.py
  - backend/repositories/artifact_repository.py
  - backend/maintenance/retention.py
  - backend/api/routes/artifacts.py
  - alembic/versions/011_storage_ops_artifact_retention.py
  - tests/test_retention_maintenance.py
  - tests/test_artifact_content_delivery.py
  - docs/local-stack.md
  - docs/artifact-delivery.md
autonomous: true
requirements:
  - OPER-03
must_haves:
  truths:
    - "Retention-pruned artifact blobs are distinguishable from accidental storage loss when clients request content or preview."
    - "Artifact retention is coupled to explicit tombstone metadata and maintenance reporting instead of silent blob deletion."
    - "Operators can find the documented retention env vars and exact dry-run or apply commands in the local stack runbook."
    - "Artifact-delivery docs explain the new retention-expired response instead of treating policy-driven pruning like a generic 404."
  artifacts:
    - path: backend/maintenance/retention.py
      provides: "Artifact-blob prune extension for the explicit retention workflow"
    - path: alembic/versions/011_storage_ops_artifact_retention.py
      provides: "Artifact blob tombstone schema for retention-aware delivery"
    - path: backend/api/routes/artifacts.py
      provides: "Explicit retention-expired response for pruned artifact content"
    - path: tests/test_artifact_content_delivery.py
      provides: "Regression coverage for retention-pruned artifact delivery semantics"
    - path: tests/test_retention_maintenance.py
      provides: "Regression coverage for artifact prune candidates and blob tombstone reporting"
    - path: docs/local-stack.md
      provides: "Operator runbook for retention env vars and maintenance commands"
    - path: docs/artifact-delivery.md
      provides: "Artifact delivery contract that documents retention-pruned content behavior"
  key_links:
    - from: backend/maintenance/retention.py
      to: backend/repositories/artifact_repository.py
      via: "maintenance workflow selects and tombstones artifact blob prune candidates"
      pattern: "list_blob_prune_candidates|artifact_blobs_pruned|blob_deleted_at"
    - from: backend/api/routes/artifacts.py
      to: backend/models/artifact.py
      via: "artifact delivery checks `blob_deleted_at` before attempting storage reads"
      pattern: "blob_deleted_at|status_code=410"
    - from: docs/local-stack.md
      to: backend/maintenance/retention.py
      via: "runbook documents the exact maintenance entrypoint and env vars"
      pattern: "python -m backend.maintenance.retention --dry-run --json|EDGAR_BACKEND_RETENTION_RUN_PAYLOAD_DAYS"
---

<objective>
Finish the artifact side of the retention contract by adding blob tombstones, retention-aware delivery behavior, and operator documentation.

Purpose: complete `OPER-03` by ensuring policy-driven blob pruning is coupled to explicit metadata and visible to clients and operators instead of looking like accidental storage corruption.
Output: artifact retention schema and maintenance extensions, retention-aware artifact content semantics, regression coverage, and operator-facing documentation for the workflow.
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
@.planning/phases/05-storage-and-ops/05-storage-and-ops-03-PLAN.md
@backend/models/artifact.py
@backend/schemas/api_phase_a.py
@backend/repositories/artifact_repository.py
@backend/maintenance/retention.py
@backend/api/routes/artifacts.py
@alembic/versions/010_storage_ops_retention.py
@tests/test_retention_maintenance.py
@tests/test_artifact_content_delivery.py
@docs/local-stack.md
@docs/artifact-delivery.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add artifact blob tombstones and make delivery report retention-pruned blobs explicitly</name>
  <files>backend/models/artifact.py
backend/schemas/api_phase_a.py
backend/repositories/artifact_repository.py
backend/maintenance/retention.py
backend/api/routes/artifacts.py
alembic/versions/011_storage_ops_artifact_retention.py
tests/test_retention_maintenance.py
tests/test_artifact_content_delivery.py</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
.planning/phases/05-storage-and-ops/05-storage-and-ops-03-PLAN.md
backend/models/artifact.py
backend/schemas/api_phase_a.py
backend/repositories/artifact_repository.py
backend/maintenance/retention.py
backend/api/routes/artifacts.py
alembic/versions/010_storage_ops_retention.py
tests/test_retention_maintenance.py
tests/test_artifact_content_delivery.py</read_first>
  <behavior>
    - Per D-07, artifact blob cleanup is coupled to explicit tombstone metadata and retention reporting instead of silent deletion.
    - Per D-06 and D-07, `blob_deleted_at` means the blob was intentionally pruned by policy, not accidentally lost.
    - Content and preview routes return `410` with the exact detail `Artifact content expired by retention policy` when the artifact row is tombstoned.
    - Missing blobs without `blob_deleted_at` still follow the current generic missing-storage path so real storage bugs are not masked as retention.
  </behavior>
  <action>Create follow-on migration `alembic/versions/011_storage_ops_artifact_retention.py` that adds nullable `blob_deleted_at` to artifacts plus any supporting selection index needed for blob pruning. Update `backend/models/artifact.py`, `backend/repositories/artifact_repository.py`, and `backend/schemas/api_phase_a.py` so artifact rows can store and surface `blob_deleted_at` additively. Extend `backend/maintenance/retention.py` so artifact blob pruning is now part of the explicit workflow: add `list_blob_prune_candidates`, include `artifact_candidates` and `artifact_blobs_pruned` in the JSON report, call `delete_at_uri()` for selected blobs, and set `artifacts.blob_deleted_at = now` only after delete succeeds. Update `backend/api/routes/artifacts.py` so both `/v1/artifacts/{artifact_id}/content` and `/v1/artifacts/{artifact_id}/preview` check `row.blob_deleted_at` before `_verify_storage_openable(...)` or `open_reader(...)`; when the field is non-null, raise `HTTPException(status_code=410, detail="Artifact content expired by retention policy")`. Keep the existing `404` behavior for untombstoned missing blobs and the existing `502` behavior for unsupported backends or invalid locators. Extend `tests/test_retention_maintenance.py` with artifact prune candidate and tombstone-report coverage, and extend `tests/test_artifact_content_delivery.py` with a tombstoned artifact case that asserts `410`, confirms the exact detail string, and checks that no filesystem path leaks into the error body.</action>
  <acceptance_criteria>`backend/models/artifact.py` contains `blob_deleted_at`.
`backend/schemas/api_phase_a.py` contains `blob_deleted_at`.
`backend/repositories/artifact_repository.py` contains `list_blob_prune_candidates`.
`backend/maintenance/retention.py` contains `artifact_candidates`.
`backend/maintenance/retention.py` contains `artifact_blobs_pruned`.
`backend/maintenance/retention.py` contains `delete_at_uri(`.
`backend/api/routes/artifacts.py` contains `status_code=410`.
`backend/api/routes/artifacts.py` contains `Artifact content expired by retention policy`.
`alembic/versions/011_storage_ops_artifact_retention.py` exists.
`tests/test_retention_maintenance.py` contains `artifact_candidates`.
`tests/test_retention_maintenance.py` contains `artifact_blobs_pruned`.
`tests/test_artifact_content_delivery.py` contains `status_code == 410`.
`tests/test_artifact_content_delivery.py` contains `Artifact content expired by retention policy`.
`tests/test_artifact_content_delivery.py` contains `blob_deleted_at`.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_retention_maintenance.py tests/test_artifact_content_delivery.py -q --tb=short</automated>
  </verify>
  <done>Artifact blob pruning is now coupled to explicit tombstone metadata, maintenance reporting, and retention-aware delivery semantics.</done>
</task>

<task type="auto">
  <name>Task 2: Document the retention operator workflow and delivery contract</name>
  <files>docs/local-stack.md
docs/artifact-delivery.md</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
.planning/phases/05-storage-and-ops/05-storage-and-ops-03-PLAN.md
docs/local-stack.md
docs/artifact-delivery.md
backend/maintenance/retention.py
backend/api/routes/artifacts.py</read_first>
  <behavior>
    - Per D-08, the operator runbook documents explicit dry-run and apply invocation, not hidden cleanup behavior.
    - The local stack docs name the exact retention env vars and the exact maintenance commands operators should run.
    - The artifact-delivery docs distinguish policy-driven `410` retention expiry from the existing generic missing-storage `404`.
  </behavior>
  <action>Update `docs/local-stack.md` with a retention section that names the exact env vars `EDGAR_BACKEND_RETENTION_RUN_PAYLOAD_DAYS`, `EDGAR_BACKEND_RETENTION_MODEL_PAYLOAD_DAYS`, `EDGAR_BACKEND_RETENTION_ARTIFACT_BLOB_DAYS`, and `EDGAR_BACKEND_RETENTION_BATCH_SIZE`, plus the exact commands `python -m backend.maintenance.retention --dry-run --json` and `python -m backend.maintenance.retention --apply --json`. Update `docs/artifact-delivery.md` so the content and preview route documentation explicitly says tombstoned blobs return `410` with `Artifact content expired by retention policy`, while untombstoned missing blobs still return generic missing-storage `404` behavior.</action>
  <acceptance_criteria>`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_RUN_PAYLOAD_DAYS`.
`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_MODEL_PAYLOAD_DAYS`.
`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_ARTIFACT_BLOB_DAYS`.
`docs/local-stack.md` contains `EDGAR_BACKEND_RETENTION_BATCH_SIZE`.
`docs/local-stack.md` contains `python -m backend.maintenance.retention --dry-run --json`.
`docs/local-stack.md` contains `python -m backend.maintenance.retention --apply --json`.
`docs/artifact-delivery.md` contains `410`.
`docs/artifact-delivery.md` contains `Artifact content expired by retention policy`.
`docs/artifact-delivery.md` contains `404`.</acceptance_criteria>
  <verify>
    <automated>rg -n "EDGAR_BACKEND_RETENTION_RUN_PAYLOAD_DAYS|EDGAR_BACKEND_RETENTION_MODEL_PAYLOAD_DAYS|EDGAR_BACKEND_RETENTION_ARTIFACT_BLOB_DAYS|EDGAR_BACKEND_RETENTION_BATCH_SIZE|python -m backend.maintenance.retention --dry-run --json|python -m backend.maintenance.retention --apply --json|Artifact content expired by retention policy|410" docs/local-stack.md docs/artifact-delivery.md</automated>
  </verify>
  <done>The operator runbook and artifact-delivery docs now explain the retention workflow and the retention-expired artifact contract clearly.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_retention_maintenance.py tests/test_artifact_content_delivery.py -q --tb=short` after Task 1, then use the `rg` verification command in Task 2 so the delivery contract and docs stay aligned.
</verification>

<success_criteria>
Phase 05 fully closes `OPER-03` once the retention workflow exists, pruned artifact content returns an explicit expired-policy response, and the operator docs show exactly how to configure and run retention safely.
</success_criteria>

<output>
After completion, create `.planning/phases/05-storage-and-ops/05-storage-and-ops-04-SUMMARY.md`
</output>
