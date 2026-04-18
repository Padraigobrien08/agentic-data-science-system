---
phase: 06-validation-boundaries-and-policy
plan: 03
subsystem: evaluation
tags: [cli, docs, guardrails]
requires:
  - phase: 06-validation-boundaries-and-policy
    provides: "Policy and degradation semantics from Plans 01-02"
provides:
  - "Explicit --allow-live guardrails on both evaluation entrypoints"
  - "Fixture-first documentation that keeps live and hybrid validation operator-only"
  - "Regression coverage for parser defaults and written policy language"
affects: [cli, documentation]
tech-stack:
  added: []
  patterns: ["explicit operator opt-in", "docs-enforced policy boundary"]
key-files:
  created:
    - tests/test_evaluate_cli_guardrails.py
  modified:
    - edgar_project/cli.py
    - edgar_project/evaluation/scripts/run_suite.py
    - edgar_project/evaluation/README.md
    - README.md
    - data/README.md
key-decisions:
  - "Kept fixture evaluation as the default path on both entrypoints and required a literal --allow-live acknowledgement for live or hybrid manifests."
  - "Locked the operator-only policy in both docs and tests so live validation cannot drift into normal user or merge workflows by accident."
patterns-established:
  - "CLI entrypoints pass allow_live_cases explicitly into EvaluationRunner instead of relying on suite semantics alone."
  - "Documentation and regression tests share the same language for operator-invoked, non-merge-blocking live evaluation."
requirements-completed: [VALID-03]
duration: 5min
completed: 2026-04-18
---

# Phase 06: Validation Boundaries and Policy Summary

**Explicit live-evaluation guardrails on CLI entrypoints and docs**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-18T10:24:00Z
- **Completed:** 2026-04-18T10:29:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `--allow-live` to both supported evaluation entrypoints and threaded the flag into `EvaluationRunner`.
- Kept fixture evaluation as the default regression path and documented live or hybrid evaluation as operator-invoked and non-merge-blocking by default.
- Added regression coverage that locks parser defaults and the required policy language in the docs.

## Task Commits

1. **Task 1-2: CLI and docs guardrails for live evaluation** - `9356dec` (`feat(06-03): add explicit live evaluation guardrails`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `edgar_project/cli.py` - added the root `evaluate --allow-live` flag and passed explicit opt-in into the runner
- `edgar_project/evaluation/scripts/run_suite.py` - added standalone script parity for the same live-evaluation guardrail
- `edgar_project/evaluation/README.md` - documented operator-invoked live or hybrid policy and fixture-first defaults
- `README.md` - updated benchmark guidance and CLI examples to keep live evaluation explicit
- `data/README.md` - clarified that `data/evaluation/` is benchmark traffic, not normal user-run history
- `tests/test_evaluate_cli_guardrails.py` - locked parser defaults, `--allow-live`, and the required policy phrases

## Decisions Made

- Used the same `--allow-live` spelling and help semantics on both entrypoints so operator acknowledgement is consistent regardless of how the suite is launched.
- Put doc-content assertions in the regression file to keep the written policy boundary from drifting independently of the CLI contract.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase-level verification can now treat explicit live opt-in and policy phrasing as stable entrypoint behavior.
- Later evaluation-control-plane work can build on a clear CLI/docs boundary instead of inferring live semantics from manifests alone.

## Self-Check

- `python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short` passed.
- Both CLI entrypoints now default to fixture evaluation and require `--allow-live` for live or hybrid manifests.
- Docs and tests now use the same operator-only, non-merge-blocking language.

---
*Phase: 06-validation-boundaries-and-policy*
*Completed: 2026-04-18*
