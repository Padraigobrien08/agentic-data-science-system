---
phase: 05-storage-and-ops
plan: 04
subsystem: api
tags: [artifact-retention, fastapi, alembic, retention, docs]
requires:
  - phase: 05-storage-and-ops-03
    provides: Explicit retention settings and the dry-run or apply maintenance workflow used for blob pruning
  - phase: 01-run-isolation-03
    provides: Stable artifact storage URIs and run-scoped artifact metadata that retention can tombstone safely
provides:
  - Artifact blob tombstones via `artifacts.blob_deleted_at`
  - Retention-aware `410` responses for artifact content and preview routes
  - Artifact retention reporting and blob-prune selection in the maintenance workflow
  - Operator docs for retention env vars, dry-run/apply commands, and delivery semantics
affects: [artifact-delivery, backend, ops, docs, retention]
tech-stack:
  added: []
  patterns:
    - tombstone retained artifact metadata instead of treating blob pruning like accidental storage loss
    - check retention tombstones before any artifact storage backend read
    - keep retention operator-visible through dry-run/apply reporting and docs
key-files:
  created:
    - alembic/versions/011_storage_ops_artifact_retention.py
  modified:
    - backend/models/artifact.py
    - backend/schemas/api_phase_a.py
    - backend/repositories/artifact_repository.py
    - backend/maintenance/retention.py
    - backend/api/routes/artifacts.py
    - tests/test_retention_maintenance.py
    - tests/test_artifact_content_delivery.py
    - docs/local-stack.md
    - docs/artifact-delivery.md
key-decisions:
  - "Artifact blob pruning now stamps `artifacts.blob_deleted_at` and preserves the row so expired content is auditable instead of looking corrupted."
  - "Artifact content and preview routes treat tombstoned blobs as `410 Artifact content expired by retention policy` before touching storage backends."
  - "The retention runbook stays explicit: operators configure `EDGAR_BACKEND_RETENTION_*` env vars and invoke dry-run or apply maintenance directly."
patterns-established:
  - "Retention reporting now includes `artifact_candidates` and `artifact_blobs_pruned` alongside run and model counts."
  - "Artifact-delivery error handling distinguishes policy expiry (`410`) from untombstoned missing storage (`404`) and backend/configuration failures (`502`)."
requirements-completed: [OPER-03]
duration: 10min
completed: 2026-04-17
---

# Phase 05 Plan 04: Artifact Retention Delivery Summary

**Artifact blob tombstones with retention-aware `410` delivery semantics and explicit operator retention runbook commands**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-17T21:09:35Z
- **Completed:** 2026-04-17T21:19:33Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added additive artifact blob tombstones through `artifacts.blob_deleted_at`, surfaced them in API schema responses, and created a follow-on Alembic revision for retention-aware delivery.
- Extended `backend.maintenance.retention` with artifact prune candidate selection, blob deletion, and JSON/plaintext reporting fields so artifact cleanup is explicit and auditable.
- Made `/v1/artifacts/{artifact_id}/content` and `/preview` return `410` with `Artifact content expired by retention policy` for tombstoned blobs, then documented the exact retention env vars and operator commands in the runbook.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add artifact blob tombstones and make delivery report retention-pruned blobs explicitly**
   `b929ed0` (`test`) failing tombstone, retention-report, and `410` delivery regressions
   `1c21b47` (`feat`) artifact tombstones, retention maintenance/reporting, delivery guards, and Alembic revision
2. **Task 2: Document the retention operator workflow and delivery contract**
   `3f6d2a4` (`docs`) retention env vars, maintenance commands, and artifact `410`/`404` contract docs

## Files Created/Modified

- `backend/models/artifact.py` - Adds `blob_deleted_at` so pruned blobs remain distinguishable from broken storage.
- `backend/schemas/api_phase_a.py` - Surfaces `blob_deleted_at` in artifact metadata/detail responses.
- `backend/repositories/artifact_repository.py` - Adds bounded artifact blob prune candidate selection.
- `backend/maintenance/retention.py` - Extends retention reporting and apply mode to prune artifact blobs and stamp tombstones.
- `backend/api/routes/artifacts.py` - Returns `410` for tombstoned content/preview requests before any storage read.
- `alembic/versions/011_storage_ops_artifact_retention.py` - Adds the artifact tombstone column and blob-prune selection index.
- `tests/test_retention_maintenance.py` - Covers artifact retention schema surfacing, reporting, pruning, and idempotence.
- `tests/test_artifact_content_delivery.py` - Covers tombstoned artifact `410` responses without leaking storage details.
- `docs/local-stack.md` - Documents the exact retention env vars and dry-run/apply maintenance commands.
- `docs/artifact-delivery.md` - Documents tombstoned `410` responses versus untombstoned missing-storage `404`s.

## Decisions Made

- Preserved artifact rows and original storage URIs after retention pruning so policy-driven expiry stays inspectable in metadata and maintenance reports.
- Checked `blob_deleted_at` before previewability or storage-open checks so all tombstoned artifact reads converge on one stable `410` contract.
- Kept the operator workflow explicit and documented rather than adding hidden cleanup into API or worker request paths.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- A transient `.git/index.lock` remained after an accidental parallel `git add`; staging was retried serially once the stale lock cleared.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 05 now fully closes `OPER-03`: retention preserves audit metadata for runs, model calls, and artifacts while clients can distinguish policy expiry from storage bugs.
- Operators have the exact env vars and commands needed to run retention safely in local or deployed stacks.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/05-storage-and-ops/05-storage-and-ops-04-SUMMARY.md`.
- Task commits verified in git history: `b929ed0`, `1c21b47`, and `3f6d2a4`.
- Verification passed: `python3 -m pytest tests/test_retention_maintenance.py tests/test_artifact_content_delivery.py -q --tb=short` and the Task 2 `rg` contract check for docs alignment.
