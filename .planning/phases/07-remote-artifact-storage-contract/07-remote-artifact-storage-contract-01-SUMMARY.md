---
phase: 07-remote-artifact-storage-contract
plan: 01
subsystem: infra
tags: [s3, boto3, moto, storage, resolver]
requires: []
provides:
  - "S3-compatible object store with logical `s3:` artifact locators"
  - "Settings-driven artifact backend selection with mixed local or remote reads"
  - "Moto-backed regressions for remote storage contract and resolver dispatch"
affects: [artifact-service, retention, artifact-delivery]
tech-stack:
  added: [boto3, moto]
  patterns: ["logical s3 uri contract", "configured-write plus mixed-read storage resolution"]
key-files:
  created:
    - backend/storage/s3.py
    - tests/test_artifact_storage_s3.py
  modified:
    - requirements-backend.txt
    - requirements-dev.txt
    - backend/config/settings.py
    - backend/storage/factory.py
    - backend/storage/resolver.py
key-decisions:
  - "Persisted remote locators use `s3:{logical_key}` so artifact metadata stays opaque and does not expose bucket names."
  - "Resolver dispatch stays scheme-based: `local:` always works, while `s3:` is available only when the deployment is configured for the remote backend."
  - "The app continues to treat SHA-256 as the checksum contract instead of trusting provider ETag semantics."
patterns-established:
  - "Storage backends can differ by deployment while artifact identity stays rooted in logical object keys."
  - "Mixed-read rollout is implemented by URI scheme rather than by adding new user-facing routes."
requirements-completed: [STOR-01]
duration: 14min
completed: 2026-04-18
---

# Phase 07: Remote Artifact Storage Contract Summary

**S3-compatible artifact storage foundation with logical `s3:` locators, settings-based backend selection, and mixed-read resolver support**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-18T12:44:00Z
- **Completed:** 2026-04-18T12:58:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added the first S3-compatible artifact backend behind the existing storage protocol.
- Introduced explicit remote-storage settings without changing the existing local default.
- Extended the resolver so configured S3 deployments can still read legacy `local:` artifacts.

## Task Commits

1. **Task 1-2: S3 backend foundation and mixed-read resolver dispatch** - `71a0237` (`feat(07-01): add s3 artifact storage backend`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `backend/storage/s3.py` - added the S3-compatible object store with local SHA-256 hashing and logical `s3:` URIs
- `backend/config/settings.py` - added backend selection and S3 configuration settings with validation
- `backend/storage/factory.py` - added configured write-store selection and scheme-aware store lookup
- `backend/storage/resolver.py` - switched artifact reads and deletes to scheme-dispatched backend resolution
- `tests/test_artifact_storage_s3.py` - added moto-backed storage and resolver regressions
- `requirements-backend.txt` - added `boto3`
- `requirements-dev.txt` - added `moto[s3]`

## Decisions Made

- Kept bucket and prefix out of persisted `storage_uri` so metadata stays app-owned and topology-agnostic.
- Made `s3:` support conditional on deployment configuration while preserving unconditional `local:` mixed reads for brownfield rollout.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The local Python environment did not have `boto3` or `moto` installed. Installed both before running the Wave 1 regression commands.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `ArtifactService` can now be switched to the configured store without changing object-key layout or URI semantics.
- Retention and delete flows can now be hardened against local or remote divergence in Wave 2.

## Self-Check

- `python3 -m pytest tests/test_artifact_storage_s3.py -q --tb=short`
- `python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py -q --tb=short`

---
*Phase: 07-remote-artifact-storage-contract*
*Completed: 2026-04-18*
