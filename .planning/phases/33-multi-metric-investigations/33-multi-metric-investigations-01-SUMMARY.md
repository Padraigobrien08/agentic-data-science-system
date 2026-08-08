---
phase: 33-multi-metric-investigations
plan: 01
status: completed
completed: 2026-08-08
requirements:
  - MULTI-01
  - MULTI-02
---

# Summary 33-01: Per-hypothesis parameterisation

## What shipped

- **`tests/agentic/test_core_tier_equivalence.py`** — the tripwire, written and passing *before*
  any planner change. Pins the ordered tool sequence, termination reason, disposition and
  confidence for all 13 frozen cases as literal data.
- **`InvestigationState.executed_requests`** — retains requests whose result has been filed.
- **`InvestigationPlanner._metric_for`** — resolves the metric hypothesis-first, then the
  interpretation hint, then `metrics[0]`.
- **`_params_for(..., hypothesis=None)`** — additive, so every existing call is unchanged.
- **`_executed_pairs`** and candidate generation across every open hypothesis, deduped on
  `(tool, metric)`.
- **`tests/agentic/test_planner_parameterisation.py`** — 11 tests.

## Deviation: the plan was wrong about migrations, and about the dedup key

`33-CONTEXT` D-01 asserted "the domain model is already multi-metric… **No migration is
required**", and 33-01 Task 3 specified deduping on `(tool_name, hypothesis_id)`. Both were
wrong, and the second could not have worked.

The planner receives `executed_tools: set[str]`, derived in the loop from
`completed_experiments + failed_experiments`. `ExperimentResult` records a **tool name only** —
not the metric, not the target hypothesis. So once claim A ran `analyze_time_series_trend`,
claim B could never run it, and no `(tool, hypothesis)` key was derivable from state to fix that.

Nothing else carried the linkage either:

| source | has it? |
|---|---|
| `ExperimentRequest` | tool + hypothesis + parameters — **discarded** from state on completion |
| `ReproducibilityManifest` | `parameters_hash` only |
| `Evidence` | hypothesis + metric (`locator='column=value'`) but no tool; nothing for failures |

Resolved by retaining the request (option A of three put to the user). No schema change: the
data already existed in objects the loop was holding and then throwing away.
`ExperimentRequestRow` is separately persisted, so the SQL path has it too — though rehydration
into state is unverified and matters only for backend resume.

**The key is `(tool, metric)`, not `(tool, hypothesis)`.** Two claims over the same column
produce identical experiments and should collapse to one; two claims over different columns
must each get the tool. `(tool, hypothesis)` gets the second right and the first wrong.

## Equivalence

The published scoreboard still stands. All 13 frozen cases take byte-identical routes — same
tools, same order, same termination, same disposition, same confidence — verified by the
tripwire throughout. With one open hypothesis the candidate list is unchanged in content and
order.

## Mutation checks

| Mutation | Result |
|---|---|
| Reorder a tool's intent priority | tripwire fires on tool sequence, 3+ cases |
| Ignore the hypothesis metric, use the global hint | 5 of 11 planner tests fail |
| Dedup on tool alone instead of `(tool, metric)` | 4 of 11 fail, incl. "same tool, two claims" |

## Verification

- `1091 passed, 10 skipped` (was 1066; 25 new)
- `ruff` clean; `mypy backend` 53 before/after
- `python3 -m agentic.evaluation` core green; tripwire 14/14

## Where the 28-02 probe stands

Re-run after this plan, the second hypothesis is **still `proposed`** — but for a different
reason. The planner now offers six candidates, three per claim, each on its own metric. The loop
terminates `sufficient_evidence` after two experiments because `TerminationPolicy.decide` fires
as soon as *one* claim is supported and challenged.

That is exactly the hand-off this plan anticipated: a second claim is now reachable; stopping
before reaching it is 33-02's problem.

## Next

33-02: sufficiency across every claim, a `mixed` disposition, and a budget sized for the new
shape.
