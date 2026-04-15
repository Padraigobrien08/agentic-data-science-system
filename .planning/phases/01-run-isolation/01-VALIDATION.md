---
phase: 1
slug: run-isolation
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 1-01-01 | 01 | 1 | EXEC-01 | integration | `python3 -m pytest tests/test_run_isolation_overlap.py::test_overlapping_runs_keep_distinct_artifact_paths -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | EXEC-02 | unit/integration | `python3 -m pytest tests/test_run_isolation_workspace.py::test_workspace_paths_are_persisted_and_run_scoped -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | EXEC-03 | unit | `python3 -m pytest tests/test_run_isolation_execution_service.py::test_execute_analysis_run_uses_explicit_workspace_paths -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_run_isolation_workspace.py` — shared contract builder, explicit path registry, report/footer provenance expectations
- [ ] `tests/test_run_isolation_overlap.py` — overlapping run workspaces and artifact non-collision
- [ ] `tests/test_run_isolation_execution_service.py` — backend execution without `chdir_repo_root()` and with persisted workspace metadata

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shared workspace volume is mounted correctly in the documented Compose stack | EXEC-01, EXEC-03 | Current CI does not exercise the full Compose topology during planning | Start the local stack from `docs/local-stack.md`, run one API-triggered and one worker-triggered analysis, confirm both write under the configured shared workspace root and that artifacts resolve from those explicit paths |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
