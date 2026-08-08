# Phase 33 Validation

## Commands

- `python3 -m pytest tests/agentic -q --tb=short`
- `python3 -m pytest -q --tb=short`
- `python3 -m agentic.evaluation`
- `python3 -m agentic.evaluation --tier hard`
- `python3 -m backend.dev.agency_bench --policy fixture --trials 2 --tier all --format md`
- `python3 -m ruff check .`
- `python3 -m mypy backend`

## Must Hold True

- An investigation with two hypotheses over two metrics resolves **both**; neither ends at
  `proposed`.
- Experiment parameters come from the metric of the hypothesis the experiment targets.
- `sufficient_evidence` requires every hypothesis to be terminal, with the challenge requirement
  still applying to each supported one.
- A run with one supported and one refuted claim reports a **mixed** disposition, not
  `supported`.
- A two-claim investigation completes under the default budget, or terminates with a typed
  reason rather than silently truncating.
- Candidate ordering is a pure function of hypothesis order and tool priority — never set or
  dict iteration order — so ids, batching, replay and diff stay deterministic.
- A multi-claim investigation is resumable, and resuming reproduces the same subsequent state.
- `fit_simple_regression` and `analyze_correlation` still work; the two-metric and parameterless
  tools are not forced through a single-metric path.
- `python3 -m agentic.evaluation` runs offline, free, and deterministic, core 13/13, exit 0.
- No database migration is required — `HypothesisRow.metric_refs_json` already persists this.

## The Load-Bearing Constraint

**The published core-tier paths must not change.** `docs/agent/agency-scoreboard.md` and
`data/evaluation/agency/scoreboard-2026-08-07*.json` report measurements over the frozen
`suite_agency_v1` cases. A planning change that reorders candidates alters tool paths, which
alters ids, which alters diffs — and the core tier could still score 13/13 while no longer being
the same investigation.

`tests/agentic/test_core_tier_equivalence.py` (33-01 Task 1) pins the paths themselves — tool
sequence, termination, disposition, confidence — as literal data, written and passing **before**
any planner change. If it diverges at any point in this phase, that is not a test to update: it
means the published scoreboard needs re-measuring, and the phase stops to decide.

## Mutation Checks Required

Following the discipline established in phases 31 and 32, where two of four guards were vacuous
on first write:

- The equivalence test: change a tool's priority, confirm it fails, revert.
- The multi-claim termination test: restore the "first supported claim wins" branch, confirm the
  partially-resolved case fails.
- The mixed disposition test: route a split outcome back to `supported`, confirm it fails.
- The new hard case (33-03): confirm it fails `FixtureAgentPolicy` *and* passes a policy that
  raises both claims — the second half is what proves it is winnable rather than merely hard.

## Out of Scope

New experiment tools, new adapters, the nine `AgencyProperty` definitions, `score_case`'s
existing scoring blocks, and the frozen core tier's membership. Cross-metric *relationship*
claims ("does margin explain revenue?") are a different shape and are deferred.

## Carried From Earlier Phases (not addressed here)

- `ModelCall` persistence for agentic policy calls (31-01)
- Cached-input pricing tier — reported cost remains a slight over-estimate (31-03)
- `--max-cost-usd` truncation still unproven against a real ceiling (32-03)
- The `select_experiment` exclusion from the hard tier, which this phase does not lift
