---
phase: 28-agency-suite-hardening
plan: 02
status: completed
completed: 2026-08-07
requirements:
  - HARD-03
---

# Summary 28-02: The discriminating case set

## What shipped

Three fixtures — `regional_revenue_spread`, `plan_tier_separated`, `api_latency_rising` — and
three hard cases, bringing the tier to **four**. The deterministic baseline scores **0/4**.

| Case | Judgement | Rule engine does |
|---|---|---|
| `implied_metric_is_selected_over_the_default` (28-01) | metric selection | falls to `metrics[0]`, answers on flat ticket volume |
| `ranking_goal_is_not_a_trend_goal` | intent selection | "growth" hits the trend keyword first; analyses the aggregate, which the strong regions flatten |
| `grouping_dimension_is_inferred_from_the_question` | dimension selection | groups by `signup_month` (`dims[0]`), finds nothing, and is correct about the wrong question |
| `unanswerable_premise_is_declined` | premise validity | substitutes rising latency for absent complaint data and concludes **supported at 0.95** |

Plus tests: fixture determinism across every registered fixture, hard cases use registered
fixtures, tier breadth, and the pairing guard.

## The last case is the strongest

`unanswerable_premise_is_declined` is the tier's counterweight — every other case rewards
finding the right answer, this one rewards declining, so the tier cannot be cleared by being
uniformly more assertive.

It needed a rewrite to work. The first wording, "are customer complaints rising?", was passed by
the rule engine *by accident*: "rising" is not in the intent keyword table, so it fell through
to `general`, profiled the dataset, and declined for entirely the wrong reason. Reworded to "is
our customer complaint **volume increasing**?" — "increas" is a trend keyword — it now reaches
`sufficient_evidence`, `supported`, confidence **0.95** on a question the dataset cannot answer.
That is the overclaiming failure the suite exists to punish, and it was one word away from
looking like a pass.

## Deviations from plan

**Three policy methods was not achievable fairly; the plan's requirement was wrong.** Both
alternatives were attempted and rejected on evidence:

- **`select_experiment`** — `expected_information_gain` is `round(max(0.3, 0.85 - 0.1 * prio))`,
  where `prio` is the tool's index in the intent list. A candidate's rank is fixed by the
  planner, so a case where the top-gain candidate is wrong tests disagreement with the
  planner's priority order, not reasoning. That fails D-03.
- **`generate_hypotheses`** — probed directly and found **structurally unwinnable**. A policy
  generating two hypotheses over two metrics leaves the second at `proposed` forever: the
  planner parameterises every tool from a single `interpretation.metric_hint`, so nothing ever
  investigates the second metric. Verified: `[(['revenue_growth_pct'], 'supported'),
  (['margin_pct'], 'proposed')]`. That case would fail a perfect policy, violating D-02.

Breadth is therefore enforced over **properties** rather than policy methods — the tier's
failures span five (`terminates_for_the_right_reason`, `reaches_the_right_disposition`,
`path_adapts_to_goal`, `revises_under_contradiction`, `calibrated_confidence`), which is what
actually stops one narrow fix from clearing it. Documented in the test's docstring and in
`docs/agent/agency-evaluation.md` so the limitation is visible rather than tacit.

**Added `hard.cases` to the baseline.** A ceiling recorded against a different-sized case set
does not bound the current one — the count is asserted alongside the rate.

## Mutation checks

| Mutation | Result |
|---|---|
| Remove the declining case's expectations | pairing guard fires: *"no hard case rewards declining, so the tier can be cleared by always asserting more"* — and the admission contract catches it independently |
| Drift `hard.cases` from reality | *"the hard tier has 4 cases but the baseline was recorded against 2"* |

Carried from 28-01 and still passing: tagging a rule-engine-passing case as `hard` fails the
contract; softening a hard case fails the ceiling.

## Verification

- `978 passed, 10 skipped` (was 947; 31 new tests)
- `ruff check .` clean; `mypy backend` 53 before/after
- `python3 -m agentic.evaluation` — core 13/13, exit 0 (gate usable)
- `python3 -m agentic.evaluation --tier hard` — 0/4, exit 1, by design
- Frozen v1 reproduces: `suite_agency_v1: 13/13`, all nine properties 100%
- Core floors untouched; `hard.max_pass_rate` stays 0.0 over the full tier

## A loop limitation worth its own work

The `generate_hypotheses` probe surfaced something larger than this phase: **an investigation
can only ever examine one metric.** `InvestigationPlanner._params_for` builds every tool's
parameters from `interpretation.metric_hint`, so a multi-metric question — "is growth slowing
*and* is margin deteriorating?" — cannot be answered however well the policy reasons. Extra
hypotheses are generated and then stranded at `proposed`.

That is a real product limitation, not a benchmark artefact, and it bounds what the agentic
engine can do for a user. Worth scoping separately.

## Next

28-03: per-tier reporting in the bench, re-measure against a model, republish. `autonomous:
false` — it spends money, and 28-01 left the bench averaging tiers into one row, which Task 1
must fix before anything is published.
