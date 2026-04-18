---
phase: 10
slug: live-hybrid-execution-hardening
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
---

# Phase 10 - Validation Strategy

> Per-phase validation contract for canonical child-run linkage, live/hybrid reconciliation, and truthful evaluation dependency observability.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py tests/test_backend_health.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py tests/test_backend_health.py tests/test_evaluation_policy_contract.py tests/test_async_run_queue.py tests/test_worker_job_lifecycle.py -q --tb=short` |
| **Estimated runtime** | ~15 seconds quick, ~40 seconds full |

## Sampling Rate

- **After every task commit:** Run the focused `pytest` command for the touched seam
- **After every plan wave:** Run `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py tests/test_backend_health.py -q --tb=short`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01 | 01 | 1 | EVAL-02 | service/API | `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` | ❌ Wave 0 | ✅ green |
| 10-02 | 02 | 2 | EVAL-02 | service/API/integration | `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` | ❌ Wave 0 | ✅ green |
| 10-03 | 03 | 3 | OPS-01, EVAL-02 | ops/API | `python3 -m pytest tests/test_backend_health.py tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` | ❌ Wave 0 | ✅ green |

*Status: ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [x] `tests/test_evaluation_live_hybrid_execution.py` — child-run enqueue, linkage, reconciliation, and aggregate evaluation status coverage
- [x] `tests/test_evaluation_control_plane_api.py` — case-to-run navigation, linked-run refresh, and bounded history response coverage
- [x] `tests/test_backend_health.py` — evaluation dependency degradation on `/health`, `/v1/worker/health`, and `/metrics`

## Manual-Only Verifications

- Optional operator smoke after execution: start a live or hybrid supported evaluation, poll the case result until the linked child run is terminal, and verify the run detail, trace, and artifact routes match the case’s latest run pointer. This is not required for sign-off if the automated API and observability regressions pass.

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers the new linkage, reconciliation, and observability seams
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
