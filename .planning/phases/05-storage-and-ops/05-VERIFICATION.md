---
phase: 05-storage-and-ops
verified: 2026-04-17T21:29:10Z
status: passed
score: 13/13 must-haves verified
---

# Phase 05: Storage and Ops Verification Report

**Phase Goal:** Make storage and observability behave truthfully and scale with sustained usage.
**Verified:** 2026-04-17T21:29:10Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Operators can tell the difference between an empty queue and an unknown queue state caused by failed DB-backed observability reads. | ✓ VERIFIED | `backend/observability/worker_queue.py:18`, `backend/api/routes/health.py:62`, `tests/test_backend_health.py:190` |
| 2 | `/v1/worker/health` returns an explicit degraded contract instead of substituting zero counts when queue reads fail. | ✓ VERIFIED | `backend/api/routes/health.py:53-95`, `backend/schemas/health.py:36-77`, `tests/test_backend_health.py:156-194` |
| 3 | `/metrics` exposes explicit queue-observability health signals and does not silently zero-fill queue gauges on refresh failure. | ✓ VERIFIED | `backend/observability/metrics.py:103-107`, `backend/observability/metrics.py:191-214`, `tests/test_backend_health.py:284-299` |
| 4 | Artifact ingestion can move large pipeline outputs into managed storage without reading the whole file into memory first. | ✓ VERIFIED | `backend/services/artifact_service.py:312-369`, `backend/storage/protocol.py:43-49`, `tests/test_artifact_storage.py:123-157` |
| 5 | The existing `local:` object-store contract, object-key layout, and artifact provenance metadata stay intact after the ingest refactor. | ✓ VERIFIED | `backend/services/artifact_service.py:79-119`, `backend/services/artifact_service.py:293-311`, `tests/test_run_isolation_execution_service.py:108-125` |
| 6 | Failed writes do not leave partially written final artifact blobs behind in the storage root. | ✓ VERIFIED | `backend/storage/local.py:90-122`, `tests/test_artifact_storage.py:81-103`, `tests/test_artifact_storage.py:159-179` |
| 7 | Operators can run an explicit dry-run retention workflow and see exactly which runs and model calls are candidates before any mutation is applied. | ✓ VERIFIED | `backend/maintenance/retention.py:45-121`, `tests/test_retention_maintenance.py:253-324`, dry-run spot-check returned the expected JSON report |
| 8 | After retention runs, analysis-run rows and model-call rows still expose audit-visible timestamps instead of disappearing. | ✓ VERIFIED | `backend/models/analysis_run.py:67-79`, `backend/models/model_call.py:59-66`, `backend/schemas/api_phase_a.py:56-98`, `backend/schemas/api_phase_a.py:201-247`, `tests/test_retention_maintenance.py:194-252` |
| 9 | Retention policy windows and apply behavior are configured explicitly rather than running implicitly inside normal API or worker traffic. | ✓ VERIFIED | `backend/config/settings.py:86-114`, `backend/maintenance/retention.py:45-185`, `docs/local-stack.md:133-149` |
| 10 | Retention-pruned artifact blobs are distinguishable from accidental storage loss when clients request content or preview. | ✓ VERIFIED | `backend/models/artifact.py:63-73`, `backend/api/routes/artifacts.py:36-41`, `tests/test_artifact_content_delivery.py:371-397` |
| 11 | Artifact retention is coupled to explicit tombstone metadata and maintenance reporting instead of silent blob deletion. | ✓ VERIFIED | `backend/repositories/artifact_repository.py:51-64`, `backend/maintenance/retention.py:112-146`, `tests/test_retention_maintenance.py:289-442` |
| 12 | Operators can find the documented retention env vars and exact dry-run or apply commands in the local stack runbook. | ✓ VERIFIED | `docs/local-stack.md:137-146` |
| 13 | Artifact-delivery docs explain the new retention-expired response instead of treating policy-driven pruning like a generic 404. | ✓ VERIFIED | `docs/artifact-delivery.md:19`, `docs/artifact-delivery.md:39`, `docs/artifact-delivery.md:58` |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/observability/worker_queue.py` | Shared queue-observability result object used by JSON and Prometheus surfaces | ✓ VERIFIED | Defines `WorkerQueueObservabilityResult` and `get_worker_queue_observability()` with explicit degraded-state return values (`:18-74`) |
| `backend/schemas/health.py` | Worker-health schema that can represent known versus unknown queue state | ✓ VERIFIED | `WorkerHealthResponse` adds `status`, `database`, `queue_state_known`, and nullable queue fields (`:36-77`) |
| `backend/observability/metrics.py` | Prometheus degraded-state gauges for queue observability | ✓ VERIFIED | Adds `_up` and `_last_error_unixtime`, reuses the shared helper, and emits `math.nan` on degraded refresh (`:103-107`, `:191-214`) |
| `tests/test_backend_health.py` | Regression coverage for degraded worker-health JSON and Prometheus NaN semantics | ✓ VERIFIED | Covers degraded JSON, degraded metrics, and queue semantics truthfulness (`:156-299`) |
| `backend/storage/protocol.py` | Storage seam for streamed writes | ✓ VERIFIED | Adds `put_fileobj()` to the object-store protocol (`:43-49`) |
| `backend/storage/local.py` | Chunked temp-file copy plus SHA-256 hashing for the local object store | ✓ VERIFIED | Uses `tempfile.mkstemp`, rolling SHA-256, and `os.replace()` in `put_fileobj()` (`:90-122`) |
| `backend/services/artifact_service.py` | Streamed pipeline-file ingest that preserves the existing artifact metadata contract | ✓ VERIFIED | `ingest_pipeline_file()` opens the source path as a file handle and delegates to `put_fileobj()` while preserving provenance metadata (`:293-369`) |
| `tests/test_artifact_storage.py` | Regression coverage for streamed ingest, digest correctness, and no `Path.read_bytes()` dependence | ✓ VERIFIED | Covers digest correctness, temp-file cleanup, and the `read_bytes should not be called` regression (`:63-179`) |
| `backend/maintenance/retention.py` | Explicit dry-run or apply retention workflow with JSON reporting and artifact prune extension | ✓ VERIFIED | Implements parser, dry-run/apply workflow, report fields, row mutation, blob deletion, and CLI entrypoint (`:45-185`) |
| `alembic/versions/010_storage_ops_retention.py` | Additive run and model-call retention columns and supporting indexes | ✓ VERIFIED | Adds `compacted_at`, `payloads_redacted_at`, and selection indexes (`:19-39`) |
| `backend/schemas/api_phase_a.py` | API-visible retention timestamps for runs, model calls, and artifacts | ✓ VERIFIED | Surfaces `compacted_at`, `payloads_redacted_at`, and `blob_deleted_at` in run/model/artifact API models (`:56-98`, `:163-247`) |
| `tests/test_retention_maintenance.py` | Regression coverage for schema surfacing, dry-run, apply mode, artifact prune reporting, and idempotence | ✓ VERIFIED | Covers settings/schema surfacing, dry-run/apply, idempotence, and CLI parser behavior (`:194-453`) |
| `backend/models/artifact.py` | Artifact blob tombstone schema for retention-aware delivery | ✓ VERIFIED | Adds nullable `blob_deleted_at` with audit intent documented in the column definition (`:63-73`) |
| `alembic/versions/011_storage_ops_artifact_retention.py` | Artifact blob tombstone migration and prune-selection index | ✓ VERIFIED | Adds `blob_deleted_at` plus `ix_artifacts_created_at_blob_deleted_at` (`:19-37`) |
| `backend/api/routes/artifacts.py` | Explicit retention-expired response for pruned artifact content | ✓ VERIFIED | Checks `blob_deleted_at` before any storage read and returns `410` with a stable detail string (`:36-41`, `:80-158`) |
| `tests/test_artifact_content_delivery.py` | Regression coverage for retention-pruned artifact delivery semantics | ✓ VERIFIED | Asserts `410` for tombstoned artifacts and no storage-path leakage in the error body (`:371-397`) |
| `docs/local-stack.md` | Operator runbook for retention env vars and maintenance commands | ✓ VERIFIED | Documents the `EDGAR_BACKEND_RETENTION_*` env vars and exact dry-run/apply commands (`:133-149`) |
| `docs/artifact-delivery.md` | Artifact delivery contract that documents retention-pruned content behavior | ✓ VERIFIED | Documents `410` for tombstoned blobs and preserves `404` semantics for untombstoned storage loss (`:19-58`) |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `backend/observability/worker_queue.py` | `backend/api/routes/health.py` | Worker-health route converts the shared result into the API response | ✓ WIRED | `get_worker_queue_observability()` is imported and mapped directly into `WorkerHealthResponse` (`backend/api/routes/health.py:12`, `:62-95`) |
| `backend/observability/worker_queue.py` | `backend/observability/metrics.py` | Metrics refresh uses the same DB-backed success or error result as worker health | ✓ WIRED | `refresh_worker_queue_gauges_from_db()` calls the same helper and branches on `queue_state_known` (`backend/observability/metrics.py:18`, `:191-214`) |
| `backend/services/artifact_service.py` | `backend/storage/protocol.py` | Pipeline ingest delegates to the streamed storage write seam | ✓ WIRED | `ArtifactService` is typed against `ArtifactObjectStore`; `ingest_pipeline_file()` calls `self._store.put_fileobj(...)` (`backend/services/artifact_service.py:58-67`, `:351-359`) |
| `backend/storage/local.py` | `backend/services/artifact_service.py` | LocalFilesystemStore returns the same `StoredObject` metadata used to persist Artifact rows | ✓ WIRED | `LocalFilesystemStore.put_fileobj()` returns `StoredObject`; `_insert_artifact_row()` persists `uri`, `byte_size`, and `sha256_hex` (`backend/storage/local.py:90-122`, `backend/services/artifact_service.py:151-176`) |
| `backend/maintenance/retention.py` | `backend/repositories/analysis_run_repository.py` | Maintenance workflow selects compactable terminal runs | ✓ WIRED | `run_retention_maintenance()` calls `list_compaction_candidates()` and stamps `row.compacted_at` in apply mode (`backend/maintenance/retention.py:96-127`, `backend/repositories/analysis_run_repository.py:59-78`) |
| `backend/maintenance/retention.py` | `backend/repositories/model_call_repository.py` | Maintenance workflow redacts raw model payload JSON | ✓ WIRED | `run_retention_maintenance()` calls `list_payload_redaction_candidates()` and stamps `row.payloads_redacted_at` (`backend/maintenance/retention.py:104-131`, `backend/repositories/model_call_repository.py:25-43`) |
| `backend/maintenance/retention.py` | `backend/repositories/artifact_repository.py` | Maintenance workflow selects and tombstones artifact blob prune candidates | ✓ WIRED | `run_retention_maintenance()` calls `list_blob_prune_candidates()`, `delete_at_uri()`, and sets `row.blob_deleted_at` (`backend/maintenance/retention.py:112-146`, `backend/repositories/artifact_repository.py:51-64`) |
| `backend/api/routes/artifacts.py` | `backend/models/artifact.py` | Artifact delivery checks `blob_deleted_at` before attempting storage reads | ✓ WIRED | `_raise_if_blob_deleted()` gates both `/content` and `/preview` before any storage access (`backend/api/routes/artifacts.py:36-41`, `:80-158`) |
| `docs/local-stack.md` | `backend/maintenance/retention.py` | Runbook documents the exact maintenance entrypoint and env vars | ✓ WIRED | Docs quote `python -m backend.maintenance.retention --dry-run --json` / `--apply --json` and the `EDGAR_BACKEND_RETENTION_*` settings implemented in `Settings` and the CLI (`docs/local-stack.md:137-146`, `backend/config/settings.py:86-114`, `backend/maintenance/retention.py:45-185`) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `backend/api/routes/health.py` | `result.snapshot` / `result.queue_state_known` | `get_worker_queue_observability()` -> `RunExecutionJobRepository.queue_observability_snapshot()` and `last_terminal_job_activity_at()` | Yes — repository issues real SQL counts and max-timestamp queries (`backend/repositories/run_execution_job_repository.py:122-200`) | ✓ FLOWING |
| `backend/observability/metrics.py` | Queue gauges + `WORKER_LAST_TERMINAL_JOB_UNIXTIME` | `refresh_worker_queue_gauges_from_db()` -> shared observability helper -> DB queries | Yes — same DB-backed helper as worker health, with NaN only on explicit degraded reads | ✓ FLOWING |
| `backend/services/artifact_service.py` | `fh` / `stored` | `path.open("rb")` -> `self._store.put_fileobj()` -> `LocalFilesystemStore.put_fileobj()` | Yes — streamed chunks are hashed and written to the final object-store path via temp-file swap (`backend/storage/local.py:90-122`) | ✓ FLOWING |
| `backend/maintenance/retention.py` | `run_candidates` / `model_call_candidates` / `artifact_candidates` | Repository selectors -> apply loop mutates rows and calls `delete_at_uri()` | Yes — selectors query persisted rows and apply mode commits real row mutations and blob deletion (`backend/maintenance/retention.py:96-146`) | ✓ FLOWING |
| `backend/api/routes/artifacts.py` | `row.blob_deleted_at` | DB-fetched `Artifact` row returned by `require_artifact_readable()` | Yes — tombstone state is persisted on the row and consulted before storage reads (`backend/api/routes/artifacts.py:39-41`, `backend/models/artifact.py:63-73`) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Degraded worker-health JSON and Prometheus unknown-state behavior | `python3 -m pytest tests/test_backend_health.py -q --tb=short` | `10 passed in 1.67s` | ✓ PASS |
| Streamed artifact ingest and run-isolation metadata compatibility | `python3 -m pytest tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q --tb=short` | `11 passed in 1.45s` | ✓ PASS |
| Retention workflow, artifact tombstones, and delivery semantics | `python3 -m pytest tests/test_retention_maintenance.py tests/test_artifact_content_delivery.py -q --tb=short` | `24 passed in 8.39s` | ✓ PASS |
| Maintenance CLI entrypoint is invocable with the documented secure-default env preconditions | `env EDGAR_BACKEND_JWT_SECRET=... EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN=... EDGAR_BACKEND_OPS_API_TOKEN=... python3 -m backend.maintenance.retention --help` | Usage text rendered and command exited `0`; `runpy` emitted a non-blocking RuntimeWarning on stderr | ✓ PASS |
| Fresh schema upgrade reaches the Phase 05 migrations on a new database | `env EDGAR_BACKEND_JWT_SECRET=... EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN=... EDGAR_BACKEND_OPS_API_TOKEN=... EDGAR_BACKEND_DATABASE_URL=sqlite:////tmp/phase05_verification.db alembic upgrade head` | Applied revisions through `011_storage_ops_artifact_retention` on a fresh SQLite DB | ✓ PASS |
| Maintenance dry-run emits a structured report on a migrated database | `env EDGAR_BACKEND_JWT_SECRET=... EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN=... EDGAR_BACKEND_OPS_API_TOKEN=... EDGAR_BACKEND_DATABASE_URL=sqlite:////tmp/phase05_verification.db python3 -m backend.maintenance.retention --dry-run --json` | Returned JSON report with `dry_run=true`, zero candidate counts, and no errors; same non-blocking RuntimeWarning on stderr | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `OPER-01` | `05-storage-and-ops-01-PLAN.md` | Health and metrics surfaces report dependency degradation explicitly instead of silently zeroing queue and worker state | ✓ SATISFIED | Shared helper + truthful JSON/Prometheus wiring in `backend/observability/worker_queue.py:18-74`, `backend/api/routes/health.py:62-95`, `backend/observability/metrics.py:191-214`; locked by `tests/test_backend_health.py:156-299` |
| `OPER-02` | `05-storage-and-ops-02-PLAN.md` | Artifact ingestion avoids full in-memory copies for large files when moving outputs into managed storage | ✓ SATISFIED | Streamed store seam and temp-file-safe local implementation in `backend/storage/protocol.py:43-49`, `backend/storage/local.py:90-122`, `backend/services/artifact_service.py:312-369`; verified by `tests/test_artifact_storage.py:63-179` |
| `OPER-03` | `05-storage-and-ops-03-PLAN.md`, `05-storage-and-ops-04-PLAN.md` | Run history and model payload retention can be bounded by policy without losing the audit trail required for supported use cases | ✓ SATISFIED | Explicit retention settings and workflow in `backend/config/settings.py:86-114`, `backend/maintenance/retention.py:45-185`, additive audit markers in `backend/models/analysis_run.py:67-79`, `backend/models/model_call.py:59-66`, `backend/models/artifact.py:63-73`, delivery semantics in `backend/api/routes/artifacts.py:36-41`, docs in `docs/local-stack.md:137-149` and `docs/artifact-delivery.md:19-58`, plus full regression coverage in `tests/test_retention_maintenance.py` and `tests/test_artifact_content_delivery.py` |

Phase 5 has no orphaned requirement IDs: all roadmap requirement IDs for the phase (`OPER-01`, `OPER-02`, `OPER-03`) appear in plan frontmatter, and `REQUIREMENTS.md` maps no additional Phase 5 requirements outside that set.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `backend/maintenance/__init__.py` | `3` | Eager re-export of `retention` causes `python -m backend.maintenance.retention` to emit a `runpy` RuntimeWarning before module execution | ℹ️ Info | The CLI still exits successfully and returns the expected help / JSON report, but operator stderr is noisy. No blocker stubs, TODOs, zero-fill fallbacks, or placeholder implementations were found in the phase-touched files. |

### Human Verification Required

No blocker human-only verification remains for phase-goal achievement. Normal operator smoke-testing in a live deployed stack is still advisable, but the phase contract, migrations, docs, and targeted regressions were all verified programmatically.

### Gaps Summary

No blocking gaps found. All 13 plan-level must-haves, all 3 roadmap success criteria, and all 3 phase requirement IDs were verified against the actual codebase, wiring, migrations, docs, and targeted behavioral checks. Phase 05 achieved its goal.

---

_Verified: 2026-04-17T21:29:10Z_
_Verifier: Claude (gsd-verifier)_
