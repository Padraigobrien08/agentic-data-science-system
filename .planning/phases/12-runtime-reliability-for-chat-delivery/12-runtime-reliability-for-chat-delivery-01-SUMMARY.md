---
phase: 12-runtime-reliability-for-chat-delivery
plan: 01
subsystem: runtime
tags: [worker, imports, compose, smoke, queue]
provides:
  - "Worker boot is import-safe again in the documented local stack"
  - "Compose smoke now exercises synchronous execution plus worker-claimed queued execution"
  - "Focused regressions cover import safety, queued status progression, and single-attempt worker completion"
affects: [backend, worker, observability, orchestration, tests, scripts]
tech-stack:
  added: []
  patterns: ["lazy package surfaces", "queue claim smoke", "runtime boot regression"]
key-files:
  created:
    - .planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-01-SUMMARY.md
    - tests/test_worker_runtime_boot.py
  modified:
    - backend/services/__init__.py
    - backend/observability/__init__.py
    - backend/agents/__init__.py
    - backend/worker/__init__.py
    - edgar_project/orchestration/__init__.py
    - scripts/smoke-compose.sh
    - tests/test_async_run_queue.py
    - tests/test_worker_job_lifecycle.py
key-decisions:
  - "Fixed the worker boot path by making package-level service, observability, worker, agent, and orchestration exports lazy instead of importing the heavy pipeline graph at import time."
  - "Kept the existing queued execution lifecycle intact; the smoke path now proves claim progress instead of introducing any alternate background runtime."
  - "Treated the run-workspace permission regression as a live-stack smoke concern, not just a unit-test concern, by requiring sync and queued runs through Compose."
patterns-established:
  - "Package `__init__` files that sit on hot runtime paths should stay import-light and lazy-load heavy surfaces."
  - "Compose smoke must validate real run movement, not just container health and login."
requirements-completed: [RUN-01, RUN-02]
completed: 2026-04-18
---

# Phase 12: Runtime Reliability for Chat Delivery Summary

**Worker boot repair and stack-level execution smoke**

## Accomplishments

- Removed the worker boot circular import by slimming `backend.services` and making the `backend.observability`, `backend.agents`, `backend.worker`, and `edgar_project.orchestration` package surfaces lazy.
- Added `tests/test_worker_runtime_boot.py` so the worker entrypoint, loop, and metrics modules are validated together as an import-safe surface.
- Extended `scripts/smoke-compose.sh` to create or reuse a project, execute one synchronous run, enqueue one background run, and fail loudly on `Permission denied`, synchronous run errors, or queued runs that never leave their initial `queued`/`pending` state.
- Added queue-status and worker lifecycle regressions so the smoke path is backed by focused tests rather than only manual Compose checks.

## Verification

- `python3 -m pytest tests/test_worker_runtime_boot.py tests/test_worker_lease_heartbeat.py -q --tb=short`
- `bash -n scripts/smoke-compose.sh`
- `python3 -m pytest tests/test_async_run_queue.py tests/test_worker_job_lifecycle.py -q --tb=short`
- `EDGAR_BACKEND_JWT_SECRET=... EDGAR_BACKEND_OPS_API_TOKEN=... EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN=... EDGAR_SMOKE_ADMIN_EMAIL=smoke-admin@example.com EDGAR_SMOKE_ADMIN_PASSWORD=Smokepass12! ./scripts/smoke-compose.sh`

## Notes

- The live smoke after rebuilding `api` and `worker` passed and confirmed the queued run left its initial state with `run_status='queued'` and `latest_job_status='running'`, which is the claim boundary this wave needed to prove.
- This wave intentionally did not change chat or onboarding behavior; it only restored the runtime foundation those later surfaces depend on.
