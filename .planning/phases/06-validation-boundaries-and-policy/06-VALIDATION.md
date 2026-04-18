---
phase: 06
slug: validation-boundaries-and-policy
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-18
---

# Phase 06 - Validation Strategy

> Per-phase validation contract for evaluation policy, degradation taxonomy, and live-use guardrails.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluate_cli_guardrails.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~8 seconds quick, ~120 seconds full |

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluate_cli_guardrails.py -q --tb=short`
- **After every plan wave:** Run `python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluate_cli_guardrails.py -q --tb=short`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01 | 01 | 1 | VALID-02, VALID-03 | unit/schema | `python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short` | ❌ Wave 0 | ⬜ pending |
| 06-02 | 02 | 2 | VALID-02 | unit/integration | `python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short` | ❌ Wave 0 | ⬜ pending |
| 06-03 | 03 | 3 | VALID-03 | CLI/docs | `python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `tests/test_evaluation_policy_contract.py` — schema defaults, explicit live-policy validation, backward compatibility for fixture and mocked cases
- [ ] `tests/test_evaluation_runner_policy.py` — degradation classification, summary counts, and report output assertions
- [ ] `tests/test_evaluate_cli_guardrails.py` — default fixture suite behavior, `--allow-live`, and policy-skip CLI semantics

## Manual-Only Verifications

All phase behaviors have automated verification.

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers all missing evaluation-policy references
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
