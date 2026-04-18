---
phase: 07-remote-artifact-storage-contract
plan: 02
type: execute
wave: 2
depends_on:
  - 07-01
files_modified:
  - backend/services/artifact_service.py
  - backend/maintenance/retention.py
  - tests/test_artifact_storage.py
  - tests/test_retention_maintenance.py
autonomous: true
requirements:
  - STOR-02
must_haves:
  truths:
    - "ArtifactService writes preserve the same logical key layout, lineage metadata, and SHA-256 contract across local and S3 backends."
    - "Row-backed delete and retention prune flows do not claim success before the blob operation succeeds."
    - "Repairable delete or prune divergence is explicit in operator-visible artifact metadata or maintenance output instead of becoming a silent orphan or false tombstone."
  artifacts:
    - path: backend/services/artifact_service.py
      provides: "Configured-write artifact persistence with cleanup and reconciliation-aware delete behavior"
    - path: backend/maintenance/retention.py
      provides: "Remote-aware prune workflow that preserves truthful tombstone semantics"
    - path: tests/test_artifact_storage.py
      provides: "Artifact service regressions for S3 writes, upload cleanup, and delete repair-state behavior"
    - path: tests/test_retention_maintenance.py
      provides: "Retention regressions for remote prune success and failure semantics"
  key_links:
    - from: backend/services/artifact_service.py
      to: backend/storage/factory.py
      via: "artifact writes now use the configured store instead of the local-only factory"
      pattern: "get_object_store|save_bytes|ingest_pipeline_file"
    - from: backend/maintenance/retention.py
      to: backend/models/artifact.py
      via: "prune behavior updates `blob_deleted_at` only after the underlying delete succeeds"
      pattern: "blob_deleted_at|delete_at_uri|storage_reconciliation"
---

<objective>
Make artifact write, delete, and retention flows truthful across local and S3 backends.

Purpose: satisfy the reconciliation and checksum parts of `STOR-02` before route-level delivery and docs are finalized.
Output: configured-write artifact service, upload cleanup on row failure, delete and prune ordering that avoids false success, and regressions for repairable divergence.
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
@.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
@.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
@.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
@.planning/phases/07-remote-artifact-storage-contract/07-remote-artifact-storage-contract-01-PLAN.md
@backend/models/artifact.py
@backend/services/artifact_service.py
@backend/maintenance/retention.py
@backend/storage/factory.py
@backend/storage/resolver.py
@tests/test_artifact_storage.py
@tests/test_retention_maintenance.py

<interfaces>
From `backend/services/artifact_service.py`:
```python
class ArtifactService:
    def save_bytes(...) -> Artifact: ...
    def ingest_pipeline_file(...) -> Artifact: ...
    def delete(self, artifact_id: UUID) -> None: ...
```

From `backend/models/artifact.py`:
```python
class Artifact(Base):
    storage_uri: Mapped[str]
    content_sha256: Mapped[str | None]
    meta_json: Mapped[dict | list | None]
    blob_deleted_at: Mapped[datetime | None]
```

From `backend/maintenance/retention.py`:
```python
def run_retention_maintenance(...) -> dict[str, Any]: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Route ArtifactService writes through the configured backend and clean up failed row inserts</name>
  <files>backend/services/artifact_service.py
tests/test_artifact_storage.py</files>
  <read_first>.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
.planning/phases/07-remote-artifact-storage-contract/07-remote-artifact-storage-contract-01-PLAN.md
backend/services/artifact_service.py
backend/storage/factory.py
backend/storage/resolver.py
tests/test_artifact_storage.py
tests/test_artifact_storage_s3.py</read_first>
  <behavior>
    - Per D-03, all new artifact writes go through the configured backend, but the logical object key layout for analysis-run and evaluation-run artifacts remains unchanged.
    - Per D-08, `content_sha256` remains app-computed and persists for S3-backed artifacts the same way it does for local ones.
    - If object upload succeeds and row insertion or flush fails afterward, the service attempts cleanup of the uploaded object and does not leave an unreported success path behind.
  </behavior>
  <action>Update `backend/services/artifact_service.py` so the default store comes from `get_object_store(self._settings)` instead of the local-only helper. Keep `_build_object_key(...)`, `source_filename`, and `source_workspace_relative_path` unchanged so lineage and key layout stay stable. Wrap `_insert_artifact_row(...)` callers so when the DB insert or flush fails after `stored = ...`, the service attempts `delete_at_uri(stored.uri, settings=self._settings)` before re-raising; if cleanup also fails, emit a structured log event that names the operation and logical `storage_uri` without leaking bucket details. Extend `tests/test_artifact_storage.py` with S3-backed `save_bytes(...)` and `ingest_pipeline_file(...)` coverage that asserts `storage_uri.startswith("s3:")`, `content_sha256` is populated, `load_bytes()` round-trips, and a simulated row-insert failure removes the uploaded object from the S3 backend.</action>
  <acceptance_criteria>`backend/services/artifact_service.py` no longer defaults to `get_local_object_store(`.
`backend/services/artifact_service.py` contains `get_object_store(`.
`backend/services/artifact_service.py` contains `delete_at_uri(stored.uri`.
`backend/services/artifact_service.py` still contains `source_workspace_relative_path`.
`tests/test_artifact_storage.py` contains `storage_uri.startswith("s3:")`.
`tests/test_artifact_storage.py` contains `content_sha256`.
`tests/test_artifact_storage.py` contains a cleanup assertion for failed row insertion or flush.
`python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py -q --tb=short</automated>
  </verify>
  <done>Artifact writes now honor the configured backend while keeping the existing logical key and checksum contract intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Make delete and retention prune flows leave explicit repair state instead of false success</name>
  <files>backend/services/artifact_service.py
backend/maintenance/retention.py
tests/test_artifact_storage.py
tests/test_retention_maintenance.py</files>
  <read_first>.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
backend/services/artifact_service.py
backend/maintenance/retention.py
backend/models/artifact.py
tests/test_artifact_storage.py
tests/test_retention_maintenance.py</read_first>
  <behavior>
    - Per D-07, row-backed delete and prune flows never set final state before the blob delete actually succeeds.
    - Per D-08, repair-needed divergence is visible through artifact metadata or maintenance reporting instead of silent row removal or false tombstones.
    - Successful retries clear or replace stale repair metadata so operators can tell whether the artifact is still divergent.
  </behavior>
  <action>Refactor `ArtifactService.delete()` so it attempts `delete_at_uri(row.storage_uri, settings=self._settings)` before permanently removing the row. When delete fails, keep the row and merge a dict entry `storage_reconciliation` into `meta_json` with the exact fields `status: "repair_required"`, `operation: "delete"`, `uri_scheme`, and `updated_at`; do not delete the row. Update `backend/maintenance/retention.py` similarly: when artifact prune succeeds, set `blob_deleted_at` and clear any stale `storage_reconciliation` patch; when prune fails, append the error to the report, leave `blob_deleted_at` unchanged, and patch `meta_json.storage_reconciliation` with `operation: "retention_prune"` and the same `repair_required` status. Extend `tests/test_artifact_storage.py` with delete-failure coverage that asserts the artifact row still exists and now carries `meta_json["storage_reconciliation"]`. Extend `tests/test_retention_maintenance.py` with remote prune success and failure cases that assert tombstones only land after successful delete, failure leaves the blob row untombstoned, and reconciliation metadata or report errors identify the repair-needed state.</action>
  <acceptance_criteria>`backend/services/artifact_service.py` no longer flushes row deletion before `delete_at_uri(` succeeds.
`backend/services/artifact_service.py` contains `storage_reconciliation`.
`backend/services/artifact_service.py` contains `"repair_required"`.
`backend/maintenance/retention.py` contains `storage_reconciliation`.
`backend/maintenance/retention.py` sets `blob_deleted_at` only after successful delete.
`tests/test_artifact_storage.py` asserts the artifact row still exists after simulated delete failure.
`tests/test_artifact_storage.py` asserts `storage_reconciliation` is present.
`tests/test_retention_maintenance.py` contains `retention_prune`.
`tests/test_retention_maintenance.py` asserts prune failure leaves `blob_deleted_at` as `None`.
`python3 -m pytest tests/test_artifact_storage.py tests/test_retention_maintenance.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_artifact_storage.py tests/test_retention_maintenance.py -q --tb=short</automated>
  </verify>
  <done>Delete and prune flows now remain truthful when storage operations fail, with repairable divergence left visible instead of silently lost.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py -q --tb=short` after Task 1, then `python3 -m pytest tests/test_artifact_storage.py tests/test_retention_maintenance.py -q --tb=short` after Task 2 so configured-write behavior and repair-state semantics stay locked.
</verification>

<success_criteria>
Phase 07 closes the hardest part of `STOR-02` once S3-backed artifacts preserve the existing checksum and lineage contract, and row-backed delete or prune paths can fail without pretending the DB and object store stayed perfectly in sync.
</success_criteria>

<output>
After completion, create `.planning/phases/07-remote-artifact-storage-contract/07-remote-artifact-storage-contract-02-SUMMARY.md`
</output>
