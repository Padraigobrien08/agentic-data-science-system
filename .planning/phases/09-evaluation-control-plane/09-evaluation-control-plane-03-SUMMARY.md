---
phase: 09-evaluation-control-plane
plan: 03
subsystem: backend
tags: [evaluation, api, cli, docs]
requires: ["09-02"]
provides:
  - "Dedicated case-review API routes for stored evaluation history"
  - "Supported `--suite-id` and `--project-id` CLI compatibility path"
  - "Docs that distinguish API-backed supported evaluation from raw manifest fallback"
affects: [backend, api, cli, docs, evaluation]
tech-stack:
  added: []
  patterns: ["case-level reopenability", "project-scoped CLI delegation", "supported-suite id workflow"]
key-files:
  created:
    - tests/test_evaluation_cli_compat.py
  modified:
    - backend/api/routes/evaluations.py
    - backend/schemas/evaluation_case_result.py
    - edgar_project/cli.py
    - edgar_project/evaluation/README.md
    - README.md
    - tests/test_evaluation_control_plane_api.py
    - tests/test_evaluate_cli_guardrails.py
key-decisions:
  - "Stored evaluation history reopens through dedicated `/cases` resources instead of requiring consumers to parse `results_json`."
  - "The supported CLI surface now centers on curated `--suite-id` values, while `--suite` remains an explicit developer fallback."
  - "Supplying `--project-id` switches the CLI into the persisted API-backed compatibility path rather than a separate execution engine."
patterns-established:
  - "Operator-facing evaluation review should always flow through aggregate-plus-child resources."
  - "Supported evaluation launches should use stable suite IDs even when a lower-level raw manifest path remains available for dev work."
requirements-completed: []
duration: 14min
completed: 2026-04-18
---

# Phase 09: Evaluation Control Plane Summary

**Case review, CLI compatibility, and workflow docs**

## Performance

- **Duration:** 14 min
- **Completed:** 2026-04-18T16:22:13Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added dedicated case-review routes so stored evaluation history can be reopened, filtered, and inspected without reparsing aggregate blobs.
- Updated the CLI to default to `--suite-id suite_fixtures_v1`, retain `--suite` as a developer fallback, and delegate persisted project-scoped runs through the shared control-plane service when `--project-id` is supplied.
- Updated the evaluation docs and root README so the supported workflow is clearly API-backed and project-scoped.

## Task Commits

1. **Task 1-2: Case review routes, CLI compatibility, and docs** - `b4643cf` (`feat(09-03): add evaluation review and cli compatibility`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `backend/api/routes/evaluations.py` - case list/detail routes with owner-scoped filtering by `status`, `input_mode`, and `degradation_class`
- `backend/schemas/evaluation_case_result.py` - read helper for stored case-result responses
- `edgar_project/cli.py` - supported `--suite-id` resolution and `--project-id` compatibility delegation
- `edgar_project/evaluation/README.md` - explicit API-backed workflow and dev fallback guidance
- `README.md` - updated benchmark examples to prefer suite IDs and project-scoped persisted starts
- `tests/test_evaluation_control_plane_api.py` - reopening/filtering regressions for stored evaluation history
- `tests/test_evaluation_cli_compat.py` - parser and delegation coverage for the new CLI contract
- `tests/test_evaluate_cli_guardrails.py` - updated parser/docs guardrails for the new supported suite-id surface

## Decisions Made

- The CLI compatibility path creates and starts a persisted evaluation row locally instead of inventing a second control-plane implementation.
- Case history filtering stays bounded and summary-safe: stored `policy_json` and `observation_json` are returned directly, but there is no new raw-payload expansion surface here.

## Deviations from Plan

- **[Rule 3 - Blocking] Existing `STATE.md` milestone regression still quarantined** — Found during: ongoing phase execution | Issue: the earlier `state begin-phase` helper mutation still leaves `.planning/STATE.md` dirty with bad milestone metadata | Fix: kept that file out of the Wave 3 commits and will repair it during phase closeout | Files modified: none committed in this wave | Verification: `git status --short` still shows `.planning/STATE.md` as a separate uncommitted change | Commit hash: n/a

**Total deviations:** 1 inherited planning-state issue. **Impact:** no product-code impact; manual state repair still required before final phase completion.

## Issues Encountered

- The initial CLI delegation test used a fake status object that was not hashable, while the real code compares against enum members. Switching the stub to `EvaluationRunStatus.passed` aligned the test with production behavior.

## User Setup Required

None.

## Next Phase Readiness

- Phase closeout can now treat `EvaluationRun` plus `/cases` as the supported operator review surface.
- Phase 10 can build live or hybrid child-run linking on top of an already-supported control plane instead of needing to invent suite identity or review APIs.

## Self-Check

- `python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py tests/test_evaluate_cli_guardrails.py -q --tb=short`

---
*Phase: 09-evaluation-control-plane*
*Completed: 2026-04-18*
