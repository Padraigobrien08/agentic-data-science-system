---
phase: 07
slug: remote-artifact-storage-contract
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-18
---

# Phase 07 - Validation Strategy

> Per-phase validation contract for S3-compatible artifact storage, mixed local or remote reads, reconciliation-safe deletes, and auth-safe delivery.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py tests/test_artifact_content_delivery.py tests/test_retention_maintenance.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~15 seconds quick, ~150 seconds full |

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py tests/test_artifact_content_delivery.py tests/test_retention_maintenance.py -q --tb=short`
- **After every plan wave:** Run `python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py tests/test_artifact_content_delivery.py tests/test_retention_maintenance.py -q --tb=short`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01 | 01 | 1 | STOR-01 | integration/contract | `python3 -m pytest tests/test_artifact_storage_s3.py tests/test_artifact_storage.py -q --tb=short` | ❌ Wave 0 | ⬜ pending |
| 07-02 | 02 | 2 | STOR-02 | service/retention | `python3 -m pytest tests/test_artifact_storage.py tests/test_retention_maintenance.py -q --tb=short` | ⚠️ extend | ⬜ pending |
| 07-03 | 03 | 3 | STOR-01, OPS-02 | API/docs | `python3 -m pytest tests/test_artifact_content_delivery.py tests/test_artifact_storage_s3.py -q --tb=short` | ⚠️ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [ ] `tests/test_artifact_storage_s3.py` — S3 backend contract, logical `s3:` URI shape, and configured-write mixed-read resolver coverage
- [ ] Extend `tests/test_artifact_storage.py` — artifact-service S3 writes, cleanup on row-insert failure, and delete repair-state behavior
- [ ] Extend `tests/test_retention_maintenance.py` — remote prune success and failure semantics with tombstone or reconciliation assertions
- [ ] Extend `tests/test_artifact_content_delivery.py` — remote-backed content, preview, and metadata route behavior with no bucket or key leakage

## Manual-Only Verifications

- Optional operator smoke after execution: run the stack with `EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND=s3` against a disposable S3-compatible endpoint and confirm content downloads still route through `/api/artifacts/*` in the web app. This is not required for phase sign-off if the automated route coverage passes.

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers the missing remote-storage contract file plus all route or retention expansions
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
