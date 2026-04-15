---
phase: 1
slug: run-isolation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 locally (`pytest>=8.0` in repo) |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/mcp/test_tools.py tests/test_mcp_orchestration_artifact_contract.py tests/orchestration/test_phase3_orchestration.py -q` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_run_isolation_workspace.py -q`
- **After every plan wave:** Run `python3 -m pytest tests/test_run_isolation_workspace.py tests/test_run_isolation_overlap.py tests/test_run_isolation_execution_service.py tests/mcp/test_tools.py tests/test_mcp_orchestration_artifact_contract.py tests/orchestration/test_phase3_orchestration.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | EXEC-01 | Wave 0 seed | `python3 -m pytest tests/test_run_isolation_overlap.py --collect-only -q` | ✅ seeded in 01-01 | ⬜ pending |
| 1-01-02 | 01 | 1 | EXEC-02 | unit/integration | `python3 -m pytest tests/test_run_isolation_workspace.py::test_run_workspace_payload_round_trip -q` | ✅ seeded in 01-01 | ⬜ pending |
| 1-01-03 | 01 | 1 | EXEC-03 | Wave 0 seed | `python3 -m pytest tests/test_run_isolation_execution_service.py --collect-only -q` | ✅ seeded in 01-01 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_run_isolation_workspace.py` — seeded in Plan 01 for shared contract builder, explicit path registry, and report/footer provenance expectations
- [x] `tests/test_run_isolation_overlap.py` — seeded in Plan 01 so later runtime plans expand overlapping-run non-collision assertions instead of introducing them at the end
- [x] `tests/test_run_isolation_execution_service.py` — seeded in Plan 01 for backend no-`chdir_repo_root()` and persisted-workspace provenance coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shared workspace volume is mounted correctly in the documented Compose stack | EXEC-01, EXEC-03 | Current CI does not exercise the full Compose topology during planning | Start the local stack from `docs/local-stack.md`, run one API-triggered and one worker-triggered analysis, confirm both write under the configured shared workspace root and that artifacts resolve from those explicit paths |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-15
