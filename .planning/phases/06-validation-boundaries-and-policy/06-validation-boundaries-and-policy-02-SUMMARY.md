---
phase: 06-validation-boundaries-and-policy
plan: 02
subsystem: evaluation
tags: [runner, reporting, degradation]
requires:
  - phase: 06-validation-boundaries-and-policy
    provides: "Typed validation policy and degradation schema contract from Plan 01"
provides:
  - "Runner-level degradation classification for policy, stale-source, upstream, and product-regression paths"
  - "Degradation-aware CLI, console, markdown, and JSON summary output"
  - "Updated example evaluation JSON that matches the real structured result contract"
affects: [cli, documentation, control-plane]
tech-stack:
  added: []
  patterns: ["policy-aware result enrichment", "degradation counts derived at summary time"]
key-files:
  created:
    - tests/test_evaluation_runner_policy.py
  modified:
    - edgar_project/evaluation/runner.py
    - edgar_project/evaluation/summary_report.py
    - examples/evaluation_results.example.json
    - examples/evaluation_summary.example.json
key-decisions:
  - "Kept degradation counts and augmented failure-brief output inside summary_report instead of widening EvaluationSummary schema in this wave."
  - "Reserved stale-source and upstream-degraded mappings through deterministic metadata and observation hooks even though live execution remains deferred."
patterns-established:
  - "Evaluation runner populates policy and observation context on results before later control-plane persistence exists."
  - "Operator-facing summary surfaces derive degradation routing from structured result fields rather than free-form messages."
requirements-completed: [VALID-02]
duration: 4min
completed: 2026-04-18
---

# Phase 06: Validation Boundaries and Policy Summary

**Runner-level degradation routing with policy-aware summaries and example outputs**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-18T09:59:19Z
- **Completed:** 2026-04-18T10:03:13Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added deterministic degradation classification for policy skips, stale-source cases, upstream SEC degradation, and product regressions.
- Surfaced degradation counts and labels through CLI, console, markdown, and JSON summary outputs.
- Updated the static example evaluation JSON files to match the structured result contract introduced by Phase 06.

## Task Commits

1. **Task 1-2: Runner degradation classification and summary/report surfacing** - `41a7c3c` (`feat(06-02): surface validation degradation context`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `edgar_project/evaluation/runner.py` - added live opt-in awareness, observation seeding, and deterministic degradation classification
- `edgar_project/evaluation/summary_report.py` - added degradation counts plus degradation-aware CLI, console, and markdown rendering
- `examples/evaluation_results.example.json` - updated per-case example output with policy and observation fields
- `examples/evaluation_summary.example.json` - added degradation counts to the summary shape
- `tests/test_evaluation_runner_policy.py` - added regression coverage for classification and report output

## Decisions Made

- Kept `EvaluationSummary` unchanged in the schema layer for this wave and derived `degradation_counts` inside `summary_report.py` so the runner/report surfacing stayed additive and localized.
- Treated the current live or hybrid execution path with `--allow-live` as "not implemented yet" but not `policy_skipped`, preserving a clear distinction between missing implementation and intentional policy refusal.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CLI and script entrypoints can now pass through explicit live opt-in without inventing new result semantics.
- Documentation updates in Wave 3 can reference concrete degradation output shapes instead of speculative policy text.

## Self-Check

- `python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short` passed.
- Policy-skipped and product-regression routing now appear in summary helpers and example outputs.
- The runner keeps current live implementation limits distinct from policy-skip behavior.

---
*Phase: 06-validation-boundaries-and-policy*
*Completed: 2026-04-18*
