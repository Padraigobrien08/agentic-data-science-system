---
phase: 13-analyst-prompt-routing
plan: 01
subsystem: api
tags: [orchestration, routing, deterministic, pytest, prompt-scope]
requires:
  - phase: 12-runtime-reliability-for-chat-delivery
    provides: "A stable chat execution baseline for the prompt-routing milestone"
provides:
  - "Planner-level narrowing to prompt-named in-workspace ticker subsets"
  - "Explicit rejection of out-of-scope ticker mentions without silent scope expansion"
  - "Broader deterministic analyst-language and peer-relative routing coverage"
affects: [orchestration, backend, chat, tests]
tech-stack:
  added: []
  patterns: ["planner-level prompt scope narrowing", "deterministic analyst-language intent cues", "explicit peer-relative phrase routing"]
key-files:
  created:
    - .planning/phases/13-analyst-prompt-routing/13-analyst-prompt-routing-01-SUMMARY.md
    - edgar_project/orchestration/prompt_scope.py
    - tests/orchestration/test_prompt_scope.py
  modified:
    - edgar_project/orchestration/planner.py
    - edgar_project/orchestration/intent.py
    - edgar_project/orchestration/goal_preferences.py
    - tests/orchestration/test_planner.py
    - tests/orchestration/test_intent.py
    - tests/orchestration/test_planner_alignment_regression.py
key-decisions:
  - "Prompt scope narrowing happens inside the planner so chat, API, and CLI callers all share the same ticker-subset behavior."
  - "Analyst-language expansion stays inside the existing deterministic intent enum and phrase rules rather than introducing a new intent class or any model-led routing."
patterns-established:
  - "Prompt-named uppercase ticker tokens can narrow the effective workspace scope before plan-template selection."
  - "Peer routing requires explicit comparison framing such as vs, versus, weaker, stronger, underperform, outperform, or which company rather than multiple tickers alone."
requirements-completed: [PROMPT-01, PROMPT-02]
duration: 7 min
completed: 2026-04-18
---

# Phase 13 Plan 01: Analyst Prompt Routing Summary

**Deterministic analyst-language routing with prompt-scoped ticker narrowing and explicit peer-relative phrase support**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-18T22:28:30Z
- **Completed:** 2026-04-18T22:36:15Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added a pure `prompt_scope` helper that narrows planner execution to prompt-named in-workspace ticker subsets and records out-of-scope symbols without silently expanding the run.
- Wired planner scope extraction ahead of template selection so prompt-named subsets affect both granular and `run_pipeline` plans consistently.
- Broadened deterministic routing so ordinary analyst deterioration language and explicit peer-relative phrasing land on the existing supported templates.
- Locked the new behavior with prompt-scope, intent, planner, and planner-alignment regressions tied to live product phrasing.

## Task Commits

Each task was committed atomically through the TDD cycle:

1. **Task 1 RED: prompt-scope narrowing tests** - `4949523` (`test`)
2. **Task 1 GREEN: planner prompt-scope narrowing** - `1f34dc7` (`feat`)
3. **Task 2 RED: analyst-language routing tests** - `504a92f` (`test`)
4. **Task 2 GREEN: deterministic analyst and peer-language routing** - `8050c7c` (`feat`)

## Files Created/Modified

- `edgar_project/orchestration/prompt_scope.py` - Extracts prompt-named in-scope tickers, out-of-scope symbols, and the effective planner ticker list.
- `edgar_project/orchestration/planner.py` - Applies prompt scope before template selection and rejects out-of-scope symbol expansion.
- `edgar_project/orchestration/intent.py` - Broadens deterministic analyst-language and peer-relative intent eligibility rules.
- `edgar_project/orchestration/goal_preferences.py` - Extends preference cues so newly admitted prompts still map to the intended existing templates.
- `tests/orchestration/test_prompt_scope.py` - Covers in-scope narrowing and out-of-scope symbol detection.
- `tests/orchestration/test_planner.py` - Verifies narrowed effective tickers and confirms multiple tickers alone do not force peer routing.
- `tests/orchestration/test_intent.py` - Locks thesis-style analyst phrasing and explicit relative-language peer routing.
- `tests/orchestration/test_planner_alignment_regression.py` - Anchors live user phrasing to `trend_deterioration` and `peer_comparison`.

## Decisions Made

- Narrow prompt-named ticker subsets inside the planner rather than chat-only so all orchestration callers preserve the same workspace-scope contract.
- Keep the routing expansion deterministic and phrase-based, reusing the existing intent enum and plan-template selection flow instead of broadening into fuzzy symbol lookup or model-assisted routing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Extended preference cues to preserve template alignment for new analyst phrasing**
- **Found during:** Task 2 (Broaden deterministic analyst-language and peer-language routing without changing the intent enum)
- **Issue:** Widening the intent gate alone made new analyst phrases supported, but some of those prompts still lacked deterministic time and metric cues needed to reliably land on the intended existing templates.
- **Fix:** Added `last 8 quarters` / `last eight quarters`, `cash flow quality`, `slipping`, and related preference cues in `goal_preferences.py`.
- **Files modified:** `edgar_project/orchestration/goal_preferences.py`
- **Verification:** `python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py -q --tb=short`
- **Committed in:** `8050c7c`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The auto-fix was required for deterministic correctness and kept the work inside the planned routing foundation with no architectural drift.

## Issues Encountered

None - the only failing states were the expected TDD RED-phase failures before implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 13 plan 02 can build the deterministic preview and rewrite-guidance contract on top of the new `prompt_scope` helper and the broader intent coverage already present in the planner core.
- Out-of-scope ticker mentions now fail planning explicitly instead of expanding silently, so the next guidance layer has concrete scope information to surface back to chat.

---
*Phase: 13-analyst-prompt-routing*
*Completed: 2026-04-18*
