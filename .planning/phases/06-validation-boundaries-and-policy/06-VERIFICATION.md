---
phase: 06-validation-boundaries-and-policy
verified: 2026-04-18T10:35:00Z
status: passed
score: 8/8 must-haves verified
---

# Phase 06: Validation Boundaries and Policy Verification Report

**Phase Goal:** Operators can interpret validation outcomes with explicit degradation taxonomy and keep live validation intentionally gated away from default user and merge workflows.
**Verified:** 2026-04-18T10:35:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Fixture and orchestration-mocked manifests remain valid without a live-policy block. | ✓ VERIFIED | `edgar_project/evaluation/schemas.py:84-118`, `tests/test_evaluation_policy_contract.py:14-36` |
| 2 | Live or hybrid manifests require explicit fair-access policy metadata instead of relying on prose or implicit defaults. | ✓ VERIFIED | `edgar_project/evaluation/schemas.py:84-118`, `edgar_project/evaluation/benchmarks/suite_smoke.json:15-19`, `tests/test_evaluation_policy_contract.py:39-70` |
| 3 | Case results now keep lifecycle status separate from typed degradation routing. | ✓ VERIFIED | `edgar_project/evaluation/schemas.py:351-367`, `tests/test_evaluation_policy_contract.py:88-93` |
| 4 | Runner results distinguish `policy_skipped`, `product_regression`, `stale_source`, and `upstream_sec_degraded` deterministically. | ✓ VERIFIED | `edgar_project/evaluation/runner.py:104-115`, `edgar_project/evaluation/runner.py:290`, `edgar_project/evaluation/runner.py:656-683`, `tests/test_evaluation_runner_policy.py:40-113` |
| 5 | Operator-facing summary surfaces expose degradation counts and labels instead of hiding them in free-form messages. | ✓ VERIFIED | `edgar_project/evaluation/summary_report.py:32-176`, `tests/test_evaluation_runner_policy.py:116-154` |
| 6 | The root `evaluate` CLI stays fixture-first by default and requires explicit `--allow-live` acknowledgement for live or hybrid suites. | ✓ VERIFIED | `edgar_project/cli.py:258-261`, `edgar_project/cli.py:387-391`, `tests/test_evaluate_cli_guardrails.py:14-24` |
| 7 | The standalone `run_suite.py` entrypoint enforces the same explicit live opt-in contract as the root CLI. | ✓ VERIFIED | `edgar_project/evaluation/scripts/run_suite.py:14-52`, `edgar_project/evaluation/scripts/run_suite.py:60-64`, `tests/test_evaluate_cli_guardrails.py:27-37` |
| 8 | Project docs keep evaluation traffic separate from normal runs and describe live or hybrid validation as operator-invoked and non-merge-blocking by default. | ✓ VERIFIED | `edgar_project/evaluation/README.md:28-57`, `README.md:24`, `README.md:55-61`, `data/README.md:11`, `tests/test_evaluate_cli_guardrails.py:40-52` |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `edgar_project/evaluation/schemas.py` | Typed policy, observation, and degradation contract for evaluation manifests and results | ✓ VERIFIED | Adds `ValidationDegradationClass`, `ValidationPolicy`, `ValidationObservation`, and live-policy validation rules |
| `edgar_project/evaluation/benchmarks/suite_smoke.json` | Example live-case manifest using the explicit policy scaffold | ✓ VERIFIED | Includes fair-access, visibility, and freshness-window fields for the live smoke case |
| `edgar_project/evaluation/runner.py` | Policy-aware live guardrail and degradation classification | ✓ VERIFIED | Seeds policy/observation on results and classifies policy/upstream/stale/product routes |
| `edgar_project/evaluation/summary_report.py` | Degradation-aware CLI, markdown, and JSON summary output | ✓ VERIFIED | Adds degradation counts plus routed follow-up reporting |
| `edgar_project/cli.py` | Root CLI `--allow-live` guardrail for operator-invoked evaluation | ✓ VERIFIED | Passes `allow_live_cases=args.allow_live` into `EvaluationRunner` |
| `edgar_project/evaluation/scripts/run_suite.py` | Standalone script parity for the same explicit live opt-in contract | ✓ VERIFIED | Adds testable `parse_args(argv)` and the same `--allow-live` wiring |
| `tests/test_evaluation_policy_contract.py` | Schema-level regression coverage for explicit live policy metadata | ✓ VERIFIED | Covers fixture compatibility, live-policy requirements, and result defaults |
| `tests/test_evaluation_runner_policy.py` | Runner and summary regression coverage for degradation routing | ✓ VERIFIED | Covers policy-skip, stale-source, upstream, and product-regression paths |
| `tests/test_evaluate_cli_guardrails.py` | CLI/docs regression coverage for fixture defaults and `--allow-live` | ✓ VERIFIED | Covers both entrypoints and the written policy boundary in the docs |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Schema policy contract and default degradation fields | `python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short` | `6 passed in 1.05s` | ✓ PASS |
| Runner classification and degradation-aware summaries | `python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short` | `4 passed in 0.80s` | ✓ PASS |
| CLI defaults and docs guardrails | `python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short` | `5 passed in 0.77s` | ✓ PASS |
| Phase 06 regression gate | `python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluate_cli_guardrails.py -q --tb=short` | `15 passed in 1.03s` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `VALID-02` | `06-01`, `06-02` | Operators can inspect case-level outcomes with explicit degradation classes that separate upstream freshness/availability issues from product regressions | ✓ SATISFIED | Typed schema contract in `edgar_project/evaluation/schemas.py:31-118`, deterministic classification in `edgar_project/evaluation/runner.py:656-683`, and degradation-aware summaries in `edgar_project/evaluation/summary_report.py:32-176`, all covered by `tests/test_evaluation_policy_contract.py` and `tests/test_evaluation_runner_policy.py` |
| `VALID-03` | `06-01`, `06-03` | Live SEC validation enforces explicit fair-access controls and does not become a default merge-blocking or user-run path | ✓ SATISFIED | Live-policy manifest validation in `edgar_project/evaluation/schemas.py:104-118`, explicit `--allow-live` on both entrypoints in `edgar_project/cli.py:387-391` and `edgar_project/evaluation/scripts/run_suite.py:44-48`, and docs/tests that keep the path operator-invoked and non-merge-blocking by default |

### Anti-Patterns Found

No blocker anti-patterns were found in the phase-touched files. Phase 06 stayed additive and did not widen into control-plane persistence, child analysis runs, or live execution rollout before the policy boundary was explicit.

### Human Verification Required

No blocker human-only verification remains for Phase 06. The phase contract is schema-, runner-, CLI-, and docs-backed, and the targeted regression gate passed.

### Gaps Summary

No blocking gaps found. All 8 phase must-haves, both roadmap success-criteria themes, and both Phase 06 requirement IDs were verified against the implemented schema, runner, CLI, docs, and targeted regressions. Phase 06 achieved its goal.

---

_Verified: 2026-04-18T10:35:00Z_
_Verifier: Codex_
