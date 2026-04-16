---
phase: 02
slug: worker-resilience
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-15
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` 8.4.2 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_backend_health.py tests/test_worker_lease_heartbeat.py tests/test_worker_attempt_history.py tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py tests/test_run_lifecycle_production.py -q` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~8 seconds quick, ~90 seconds full |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_worker_lease_heartbeat.py tests/test_run_lifecycle_production.py -q`
- **After every plan wave:** Run `python3 -m pytest tests/test_backend_health.py tests/test_worker_lease_heartbeat.py tests/test_worker_attempt_history.py tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py tests/test_run_lifecycle_production.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds for quick checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01 | 01 | 1 | WORK-01 | integration | `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_worker_lease_heartbeat.py -q` | ✅ | ✅ green |
| 02-02 | 02 | 2 | WORK-02 | integration | `python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py tests/test_run_lifecycle_production.py tests/test_worker_attempt_history.py -q` | ✅ | ✅ green |
| 02-03 | 03 | 3 | WORK-01, WORK-02 | integration + postgres | `python3 -m pytest tests/test_backend_health.py tests/test_worker_job_lifecycle_postgres.py tests/test_worker_lease_heartbeat.py tests/test_worker_attempt_history.py tests/test_run_lifecycle_api.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_worker_job_lifecycle_postgres.py` — real Postgres `SKIP LOCKED` claim and reclaim concurrency coverage for WORK-01
- [x] `tests/test_worker_lease_heartbeat.py` — heartbeat renewal plus lost-ownership abort/finalize coverage for WORK-01
- [x] `tests/test_worker_attempt_history.py` — durable retry/reclaim history visibility on the same `analysis_run_id` for WORK-02
- [x] Shared Postgres fixture or Compose-backed helper for queue concurrency validation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Worker lease and retry metrics read truthfully under a live API + worker stack | WORK-01, WORK-02 | Automated API regressions cover DB-backed semantics, but repo CI still does not exercise the documented multi-process Compose stack continuously | 1. Start the local stack with API, worker, and Postgres. 2. Queue a long-running run. 3. Confirm `/v1/worker/health` and `/metrics` reflect active lease ownership, retries, and stale-lease recovery truthfully during and after the run. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
