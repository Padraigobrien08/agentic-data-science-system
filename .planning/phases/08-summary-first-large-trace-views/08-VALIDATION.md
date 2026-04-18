---
phase: 08
slug: summary-first-large-trace-views
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
---

# Phase 08 - Validation Strategy

> Per-phase validation contract for summary-first trace opening, bounded collection navigation, and privileged on-demand raw expansion.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` + `vitest run` |
| **Config file** | `pytest.ini` + `frontend/vitest.config.ts` |
| **Quick run command** | `python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short && cd frontend && npm run test` |
| **Estimated runtime** | ~20 seconds quick, ~180 seconds full |

## Sampling Rate

- **After every task commit:** Run the relevant backend or frontend focused command for that task
- **After every plan wave:** Run the full quick command
- **Before `$gsd-verify-work`:** Full backend and frontend test suites must be green
- **Max feedback latency:** 20 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01 | 01 | 1 | TRACE-01 | backend contract | `python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short` | ❌ Wave 0 | ✅ green |
| 08-02 | 02 | 2 | TRACE-01, TRACE-02 | frontend render/query-state | `cd frontend && npm run test -- run-trace-summary-view.test.tsx run-step-trace.test.tsx` | ❌ Wave 0 | ✅ green |
| 08-03 | 03 | 3 | TRACE-02, TRACE-03 | auth-bound raw expansion | `python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- model-call-summary-card.test.tsx run-step-trace.test.tsx` | ⚠️ extend + Wave 0 | ✅ green |

*Status: ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [x] `tests/test_trace_summary_api.py` — trace-shell response, bounded collection query params, and item-scoped raw gating
- [x] Extend `tests/test_sprint3_transparency_api.py` — compatibility checks for existing slim transparency responses after the new summary-first contract lands
- [x] `frontend/src/components/trace/run-trace-summary-view.test.tsx` — overview-first rendering, collection separation, and timeline-spine expectations
- [x] `frontend/src/components/runs/run-step-trace.test.tsx` — step JSON stays collapsed until explicit interaction or raw fetch state
- [x] Extend `frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx` — bounded raw payload rendering still stays opt-in and local to one model-call card

## Manual-Only Verifications

- Open a seeded or large historical run in the trace page and confirm the first render loads the overview and collection summaries without any default raw JSON panes.
- As an admin user, open one step or model call raw payload and verify only that item fetches privileged data.
- As a non-admin user, verify the trace page still renders summary data while raw expansion controls remain unavailable or denied.

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers both backend contract work and frontend summary-first rendering work
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
