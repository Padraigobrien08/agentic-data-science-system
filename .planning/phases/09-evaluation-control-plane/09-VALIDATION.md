---
phase: 09
slug: evaluation-control-plane
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
---

# Phase 09 - Validation Strategy

> Per-phase validation contract for supported suite cataloging, persisted evaluation runs and case results, API-backed launch flows, and CLI compatibility.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~12 seconds quick, ~180 seconds full |

## Sampling Rate

- **After every task commit:** Run the relevant focused `pytest` command for that task
- **After every plan wave:** Run `python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py -q --tb=short`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01 | 01 | 1 | EVAL-01 | API/contract | `python3 -m pytest tests/test_evaluation_control_plane_api.py -q --tb=short` | ❌ Wave 0 | ✅ green |
| 09-02 | 02 | 2 | VALID-01, EVAL-01 | service/integration | `python3 -m pytest tests/test_evaluation_control_plane_service.py tests/test_evaluation_control_plane_api.py -q --tb=short` | ❌ Wave 0 | ✅ green |
| 09-03 | 03 | 3 | VALID-01, EVAL-01 | API/CLI/docs | `python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py -q --tb=short` | ❌ Wave 0 | ✅ green |

*Status: ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [x] `tests/test_evaluation_control_plane_api.py` — supported suite catalog, project-scoped create/list/detail, start flow, and case review route coverage
- [x] `tests/test_evaluation_control_plane_service.py` — lifecycle transitions, case-result persistence, and policy/observation/degradation storage coverage
- [x] `tests/test_evaluation_cli_compat.py` — supported `--suite-id` compatibility path and service-delegation coverage

## Manual-Only Verifications

- Optional operator smoke after execution: create a persisted evaluation run through the API, start it with a fixture suite, and verify the returned evaluation detail plus case list match the stored JSON export. This is not required for phase sign-off if the automated API and service tests pass.

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers the new API, service, and CLI compatibility seams
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
