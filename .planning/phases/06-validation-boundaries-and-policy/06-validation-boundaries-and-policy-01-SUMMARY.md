---
phase: 06-validation-boundaries-and-policy
plan: 01
subsystem: evaluation
tags: [pydantic, benchmarks, validation-policy]
requires: []
provides:
  - "Typed validation policy, observation, and degradation fields in evaluation schemas"
  - "Explicit live smoke manifest contract with freshness window and operator-only policy"
  - "Regression coverage for fixture compatibility and live-policy validation"
affects: [runner, summaries, cli]
tech-stack:
  added: []
  patterns: ["typed evaluation policy metadata", "explicit live-manifest validation"]
key-files:
  created:
    - tests/test_evaluation_policy_contract.py
  modified:
    - edgar_project/evaluation/schemas.py
    - edgar_project/evaluation/benchmarks/suite_smoke.json
key-decisions:
  - "Kept lifecycle status separate from degradation routing by adding a dedicated degradation enum on EvaluationResult."
  - "Made live and hybrid manifests require explicit policy metadata instead of relying on comments or skipped-message conventions."
  - "Changed the bare BenchmarkInput default mode to fixture so the new live-policy validator does not make default model construction invalid."
patterns-established:
  - "Live and hybrid evaluation cases must declare operator-only policy metadata, including fairness policy and freshness window."
  - "Evaluation result contracts can evolve with additive typed fields before the control plane or persisted case-results phase lands."
requirements-completed: [VALID-02, VALID-03]
duration: 3min
completed: 2026-04-18
---

# Phase 06: Validation Boundaries and Policy Summary

**Typed live-validation policy contract with explicit freshness metadata and fixture-safe schema regressions**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-18T09:56:00Z
- **Completed:** 2026-04-18T09:59:18Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added typed validation policy, observation, and degradation fields to the evaluation schema surface.
- Locked live and hybrid manifests behind explicit operator-only policy validation.
- Updated the live smoke scaffold and added schema-level regressions for fixture compatibility and live policy enforcement.

## Task Commits

1. **Task 1-2: Schema contract and live smoke scaffold** - `198c038` (`feat(06-01): add validation policy contract`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `edgar_project/evaluation/schemas.py` - added validation policy, observation, and degradation result types plus live-manifest validation rules
- `edgar_project/evaluation/benchmarks/suite_smoke.json` - added explicit live policy metadata and freshness window to the smoke scaffold
- `tests/test_evaluation_policy_contract.py` - added regression coverage for fixture compatibility, live policy requirements, and stable enum values

## Decisions Made

- Changed `BenchmarkInput.mode` default from `live` to `fixture` so default model construction stays valid under the new live-policy validator and matches the current fixture-first benchmark posture.
- Enforced `normal_user_visible: false`, `allow_merge_blocking: false`, and non-null `freshness_window_seconds` for live or hybrid inputs so the schema itself carries the guardrail.

## Deviations from Plan

### Auto-fixed Issues

**1. Default-model validity under new live policy validator**
- **Found during:** Task 1 (schema contract implementation)
- **Issue:** The existing `BenchmarkInput` default `mode = live` would make plain default model construction invalid as soon as live or hybrid cases required an explicit `policy` block.
- **Fix:** Changed the default mode to `fixture`, which matches the repo’s existing fixture-first benchmark posture and keeps default model construction valid.
- **Files modified:** `edgar_project/evaluation/schemas.py`
- **Verification:** `python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short`
- **Committed in:** `198c038`

---

**Total deviations:** 1 auto-fixed
**Impact on plan:** No scope creep. The deviation made the schema contract internally consistent and better aligned with the existing default evaluation path.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Runner and summary layers can now classify and surface degradation explicitly in Wave 2.
- CLI guardrails in Wave 3 can rely on the manifest-level `requires_explicit_live_opt_in` contract already being present.

## Self-Check

- All targeted schema and manifest regressions passed.
- The live smoke scaffold validates against the new policy contract.
- Fixture manifests remain valid without a `policy` block.

---
*Phase: 06-validation-boundaries-and-policy*
*Completed: 2026-04-18*
