---
phase: 05
slug: storage-and-ops
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-17
---

# Phase 05 - Validation Strategy

> Per-phase validation contract for storage, retention, and ops truthfulness work.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest tests/test_backend_health.py tests/test_artifact_storage.py -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~10 seconds quick, ~90 seconds full |

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_backend_health.py tests/test_artifact_storage.py -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/test_backend_health.py tests/test_artifact_storage.py tests/test_artifact_content_delivery.py tests/test_retention_maintenance.py -q --tb=short`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds for targeted backend regressions

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01 | 01 | 1 | OPER-01 | integration | `python -m pytest tests/test_backend_health.py -q --tb=short` | ✅ | ⬜ pending |
| 05-02 | 02 | 1 | OPER-02 | integration | `python -m pytest tests/test_artifact_storage.py -q --tb=short` | ✅ | ⬜ pending |
| 05-03 | 03 | 1 | OPER-03 | unit/integration | `python -m pytest tests/test_retention_maintenance.py -q --tb=short` | ❌ Wave 0 | ⬜ pending |
| 05-04 | 04 | 2 | OPER-03 | integration/docs | `python -m pytest tests/test_artifact_content_delivery.py -q --tb=short` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `tests/test_backend_health.py` - degraded-path assertions for nullable JSON fields, explicit status, and metrics `NaN` / `_up` behavior
- [ ] `tests/test_artifact_storage.py` or `tests/test_artifact_ingest_streaming.py` - temp-file cleanup, streamed write path usage, and digest correctness for large-source ingest
- [ ] `tests/test_artifact_content_delivery.py` - intentional retention behavior once blob tombstones exist
- [ ] `tests/test_retention_maintenance.py` - dry-run reporting, payload redaction, blob pruning, audit markers, and idempotent reruns
- [ ] Retention-specific API/type assertions updated if additive tombstone fields surface on run, model-call, or artifact responses

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Operator retention workflow is understandable and safe to run in a local stack | OPER-03 | Dry-run and apply ergonomics are partly an operator workflow concern, not just a unit-test concern | 1. Start the documented local stack. 2. Run the retention command in dry-run mode with an intentionally small cutoff window. 3. Confirm the report identifies candidate rows and blobs without modifying them. 4. Re-run in apply mode and confirm the same records now expose audit-visible redaction or prune markers instead of appearing silently broken. |

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 gaps
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 names the missing retention and streaming coverage references
- [x] No watch-mode commands
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
