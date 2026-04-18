---
phase: 11
slug: milestone-audit-traceability-cleanup
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
---

# Phase 11 - Validation Strategy

> Per-phase validation contract for repairing summary traceability metadata, reconciling Nyquist bookkeeping, and proving the milestone audit is clean.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `python3` standard library checks + `node gsd-tools` + focused `pytest`/`vitest` audit slice |
| **Config file** | `pytest.ini`, `frontend/vitest.config.ts`, and existing `.planning/` frontmatter conventions |
| **Quick run command** | `python3 - <<'PY'\nfrom pathlib import Path\nimport re\n\ndef collect_requirements(phase_dir):\n    reqs = set()\n    for path in Path(phase_dir).glob('*-SUMMARY.md'):\n        text = path.read_text()\n        match = re.search(r'^requirements-completed:\\s*\\[([^\\]]*)\\]', text, re.M)\n        if match:\n            reqs.update(item.strip() for item in match.group(1).split(',') if item.strip())\n    return reqs\n\nphase9 = collect_requirements('.planning/phases/09-evaluation-control-plane')\nphase10 = collect_requirements('.planning/phases/10-live-hybrid-execution-hardening')\nassert {'VALID-01', 'EVAL-01'} <= phase9, phase9\nassert {'EVAL-02', 'OPS-01'} <= phase10, phase10\nfor phase in ['06', '07', '08', '09', '10']:\n    validation = next(Path('.planning/phases').glob(f'{phase}-*/*-VALIDATION.md')).read_text()\n    assert 'status: complete' in validation\n    assert 'wave_0_complete: true' in validation\n    assert '⬜ pending' not in validation\n    assert '- [ ]' not in validation\nprint('phase-11-quick-check ok')\nPY` |
| **Full suite command** | `python3 - <<'PY'\nfrom pathlib import Path\nimport re\ntext = Path('.planning/v1.1-MILESTONE-AUDIT.md').read_text()\nassert 'status: passed' in text\nassert 'tech_debt: []' in text\nassert 'compliant_phases: [06, 07, 08, 09, 10]' in text\nassert 'partial_phases: []' in text\nassert 'overall: compliant' in text\nprint('audit-doc ok')\nPY && python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_live_hybrid_execution.py tests/test_trace_summary_api.py tests/test_artifact_content_delivery.py tests/test_backend_health.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx` |
| **Estimated runtime** | ~5 seconds quick, ~25 seconds full |

## Sampling Rate

- **After every task commit:** Run that task's focused automated command
- **After every plan wave:** Run the quick run command
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01 | 01 | 1 | traceability cleanup | docs/frontmatter | `python3 - <<'PY'\nfrom pathlib import Path\nimport re\n\ndef collect_requirements(phase_dir):\n    reqs = set()\n    for path in Path(phase_dir).glob('*-SUMMARY.md'):\n        text = path.read_text()\n        match = re.search(r'^requirements-completed:\\s*\\[([^\\]]*)\\]', text, re.M)\n        if match:\n            reqs.update(item.strip() for item in match.group(1).split(',') if item.strip())\n    return reqs\n\nassert {'VALID-01', 'EVAL-01'} <= collect_requirements('.planning/phases/09-evaluation-control-plane')\nassert {'EVAL-02', 'OPS-01'} <= collect_requirements('.planning/phases/10-live-hybrid-execution-hardening')\nprint('summary-frontmatter ok')\nPY` | ✅ existing summaries | ⬜ pending |
| 11-02 | 02 | 1 | nyquist cleanup | docs/frontmatter | `python3 - <<'PY'\nfrom pathlib import Path\nfor phase in ['06', '07', '08', '09', '10']:\n    text = next(Path('.planning/phases').glob(f'{phase}-*/*-VALIDATION.md')).read_text()\n    assert 'status: complete' in text\n    assert 'wave_0_complete: true' in text\n    assert '⬜ pending' not in text\n    assert '- [ ]' not in text\nprint('validation-bookkeeping ok')\nPY` | ✅ existing validation docs | ⬜ pending |
| 11-03 | 03 | 2 | audit closure | docs + regression slice | `python3 - <<'PY'\nfrom pathlib import Path\ntext = Path('.planning/v1.1-MILESTONE-AUDIT.md').read_text()\nassert 'status: passed' in text\nassert 'tech_debt: []' in text\nassert 'compliant_phases: [06, 07, 08, 09, 10]' in text\nassert 'partial_phases: []' in text\nassert 'overall: compliant' in text\nprint('audit-refresh ok')\nPY && python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_live_hybrid_execution.py tests/test_trace_summary_api.py tests/test_artifact_content_delivery.py tests/test_backend_health.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx` | ✅ existing audit + regressions | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [x] Existing summary, validation, audit, and regression infrastructure already covers this cleanup phase

## Manual-Only Verifications

All phase behaviors have automated verification.

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or existing infrastructure coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
