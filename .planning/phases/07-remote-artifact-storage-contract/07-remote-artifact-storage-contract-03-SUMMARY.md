---
phase: 07-remote-artifact-storage-contract
plan: 03
subsystem: api
tags: [artifacts, delivery, docs, compose, s3]
requires:
  - phase: 07-01
    provides: "S3 backend selection and mixed-read resolver support"
  - phase: 07-02
    provides: "Truthful artifact write, delete, and retention reconciliation semantics"
provides:
  - "S3-backed metadata, content, and preview route coverage"
  - "Optional remote-storage env pass-through for the local stack"
  - "Artifact delivery docs that treat `storage_uri` as a logical opaque locator"
affects: [frontend, ops, local-stack]
tech-stack:
  added: []
  patterns: ["app-owned remote artifact delivery", "opaque storage locator documentation"]
key-files:
  created: []
  modified:
    - backend/api/routes/artifacts.py
    - tests/test_artifact_content_delivery.py
    - .env.example
    - docker-compose.yml
    - docs/local-stack.md
    - docs/artifact-delivery.md
key-decisions:
  - "Preview now uses the same generic unsupported-backend wording as content so remote misconfiguration is consistent across routes."
  - "Compose passes through remote-storage env vars without changing the local filesystem default or adding MinIO."
  - "Metadata docs explicitly describe `storage_uri` as a logical locator rather than a raw transport contract."
patterns-established:
  - "Remote-backed artifacts must keep the same authenticated route surface as local artifacts."
  - "Operator docs can expose remote backend configuration without exposing bucket or object identifiers to product consumers."
requirements-completed: [STOR-01, OPS-02]
duration: 3min
completed: 2026-04-18
---

# Phase 07: Remote Artifact Storage Contract Summary

**S3-backed artifact metadata, content, and preview routes using the same app-owned delivery path, plus optional remote-storage env wiring for the local stack**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-18T13:02:20Z
- **Completed:** 2026-04-18T13:05:19Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added end-to-end S3 delivery regressions for artifact metadata, content, and preview routes.
- Unified generic remote-backend error wording across content and preview endpoints.
- Documented optional S3-compatible env wiring in `.env.example`, Compose, and the local-stack runbook without changing the local default.

## Task Commits

1. **Task 1-2: Remote delivery route coverage and operator docs wiring** - `13f82ec` (`feat(07-03): wire remote artifact delivery contract`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `backend/api/routes/artifacts.py` - aligned preview-side unsupported-backend wording with content delivery
- `tests/test_artifact_content_delivery.py` - added S3-backed metadata, content, preview, and missing-blob regressions
- `.env.example` - documented optional remote-storage env vars
- `docker-compose.yml` - passed remote-storage env vars into the API and worker services
- `docs/local-stack.md` - documented external S3-compatible setup while keeping local disk as the default
- `docs/artifact-delivery.md` - clarified that `storage_uri` is a logical opaque locator and not a raw bucket or object path

## Decisions Made

- Kept the route contract fully app-owned, with no direct bucket access or signed-URL rollout in this phase.
- Documented remote storage as an external opt-in and explicitly left MinIO out of the local stack.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Large-trace work in Phase 8 can rely on stable local or remote artifact delivery semantics.
- Later evaluation-control-plane work can reference artifact metadata without taking a dependency on raw bucket topology.

## Self-Check

- `python3 -m pytest tests/test_artifact_content_delivery.py tests/test_artifact_storage_s3.py -q --tb=short`
- `rg -n "EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND|EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET|EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ENDPOINT_URL|EDGAR_BACKEND_ARTIFACT_STORAGE_S3_FORCE_PATH_STYLE|s3:|opaque locator|bucket or object" .env.example docker-compose.yml docs/local-stack.md docs/artifact-delivery.md`

---
*Phase: 07-remote-artifact-storage-contract*
*Completed: 2026-04-18*
