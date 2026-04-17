---
phase: 05-storage-and-ops
plan: 03
subsystem: database
tags: [retention, alembic, sqlalchemy, maintenance, ops]
requires:
  - phase: 01-run-isolation-03
    provides: Persisted backend runs anchored to stable `analysis_run_id` identities and audit metadata
  - phase: 03-secure-defaults-02
    provides: Summary-first raw payload surfaces that retention can trim without reopening broad payload access
provides:
  - Explicit retention policy settings for run payloads, model payloads, artifact blobs, and batch sizing
  - Additive audit timestamps for compacted runs and redacted model payloads
  - Repository selectors and an explicit dry-run or apply maintenance workflow for retention
  - Regression coverage for retention schema surfacing, reporting, apply mode, and idempotent reruns
affects: [05-04, backend, ops, retention, maintenance]
tech-stack:
  added: []
  patterns:
    - additive audit-preserving retention timestamps instead of hard deletes
    - explicit operator-invoked maintenance workflow with dry-run default
    - repository selector pattern for bounded retention batches
key-files:
  created:
    - backend/maintenance/__init__.py
    - backend/maintenance/retention.py
    - alembic/versions/010_storage_ops_retention.py
    - tests/test_retention_maintenance.py
  modified:
    - backend/config/settings.py
    - backend/models/analysis_run.py
    - backend/models/model_call.py
    - backend/schemas/api_phase_a.py
    - backend/repositories/analysis_run_repository.py
    - backend/repositories/model_call_repository.py
key-decisions:
  - "Retention defaults stay disabled until operators set explicit day windows, with one shared batch-size cap for each maintenance tier."
  - "Run and model retention compact or redact payload-heavy fields in place and stamp audit-visible timestamps instead of deleting rows."
  - "This plan only redacts `analysis_run_id`-backed model history; artifact-blob deletion remains deferred to 05-04."
patterns-established:
  - "Operators trigger retention through `python -m backend.maintenance.retention`, with dry-run as the default and JSON/plaintext reporting from the same report object."
  - "Repository candidate selectors filter oldest eligible rows first and skip already compacted or redacted history so apply runs are idempotent."
requirements-completed: [OPER-03]
duration: 5min
completed: 2026-04-17
---

# Phase 05 Plan 03: Retention Maintenance Summary

**Audit-preserving run compaction and model-payload redaction with explicit retention settings, Alembic markers, and a dry-run maintenance CLI**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-17T21:02:07Z
- **Completed:** 2026-04-17T21:07:24Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added explicit retention settings for run payloads, model payloads, artifact blobs, and batch size, with additive `compacted_at` and `payloads_redacted_at` audit markers.
- Surfaced retention timestamps through the Phase A API schemas so compacted runs and redacted model calls remain explainable without changing payload-gating behavior.
- Built an operator-invoked retention workflow with repository selectors, dry-run default, apply mode, JSON reporting, and idempotent regression coverage.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add retention-state schema, policy settings, and response-surface timestamps**
   `6016a9b` (`test`) failing retention schema/settings/serializer tests
   `e03ca09` (`feat`) retention settings, audit timestamps, API surfacing, and Alembic revision
2. **Task 2: Add repository selectors and the explicit retention maintenance workflow**
   `0da7cdd` (`test`) failing retention workflow, selector, and CLI parser tests
   `aa78b41` (`feat`) repository selectors plus explicit dry-run/apply maintenance workflow

## Files Created/Modified

- `backend/config/settings.py` - Adds explicit retention window and batch-size settings under the existing `EDGAR_BACKEND_` prefix.
- `backend/models/analysis_run.py` and `backend/models/model_call.py` - Add audit timestamps for compacted runs and redacted model payloads.
- `backend/schemas/api_phase_a.py` - Exposes retention timestamps while keeping payload visibility gated by the existing include flags.
- `backend/repositories/analysis_run_repository.py` and `backend/repositories/model_call_repository.py` - Add bounded selectors for compaction and payload-redaction candidates.
- `backend/maintenance/retention.py` and `backend/maintenance/__init__.py` - Add the explicit maintenance entrypoint, report formatting, and CLI parser.
- `alembic/versions/010_storage_ops_retention.py` - Adds retention columns plus selection indexes for `analysis_runs.finished_at` and `model_calls.created_at`.
- `tests/test_retention_maintenance.py` - Covers settings/schema surfacing, dry-run no-op behavior, apply-mode mutation, JSON reporting, and idempotent reruns.

## Decisions Made

- Defaulted the new retention policy windows to `0` so no retention tier runs implicitly until an operator opts in with explicit day values.
- Compacted `AnalysisRun` payload JSON and redacted `ModelCall` payload JSON in place so audit rows survive and later routes can explain intentional trimming.
- Scoped model-call retention to `analysis_run_id`-backed history in this plan to avoid broadening artifact or evaluation retention behavior before `05-04`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- SQLite round-trips timezone-aware timestamps as naive datetimes in the targeted regression suite, so the apply-mode test normalizes the instant before comparing audit timestamps.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase `05-04` can build artifact-blob pruning and delivery semantics on top of the new `compacted_at` and `payloads_redacted_at` audit contract.
- Operators now have an explicit retention seam that can be scheduled externally without moving deletion behavior into API or worker request paths.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/05-storage-and-ops/05-storage-and-ops-03-SUMMARY.md`.
- Task commits verified in git history: `6016a9b`, `e03ca09`, `0da7cdd`, and `aa78b41`.
- Verification passed: `python3 -m pytest tests/test_retention_maintenance.py -k "settings or schema or serializer" -q --tb=short` and `python3 -m pytest tests/test_retention_maintenance.py -q --tb=short`.
