---
phase: 33-multi-metric-investigations
plan: 03
status: completed
completed: 2026-08-08
requirements:
  - MULTI-05
---

# Summary 33-03: The case that could not exist, and the re-measurement

## The result

| policy | tier | trials | pass rate | mean $ | p95 s |
|---|---|---|---|---|---|
| fixture | core | 5 | 100% | 0.0000 | 0.00 |
| fixture | hard | 5 | **0%** | 0.0000 | 0.01 |
| gpt-5.4-mini | core | 5 | 100% | 0.0524 | 7.79 |
| gpt-5.4-mini | hard | 5 | **60%** | 0.0227 | 8.71 |

Zero unstable cases, nothing truncated, **$0.38** against a $3.00 ceiling. The frozen core tier
reproduced 100% for both policies — the control confirming nothing else moved.

## The case is back and it discriminates

`two_part_goal_resolves_both_clauses` was designed in phase 32 and dropped as **unwinnable**: no
policy could pass it, because a second hypothesis stayed `proposed` forever. It now fails
`FixtureAgentPolicy` and passes a two-claim policy — verified before it was added.

The hard tier defeats **two** of the four model-backed decisions rather than one. That was the
bar phase 32 could not reach.

## The model fails it for an unexpected reason

The case was added expecting the model to answer the first clause and drop the second. It never
got that far: asked "is revenue growth slowing **and** is margin quality holding up?", it read
the question as a *ranking* problem, ran `rank_entities`, and concluded `insufficient_evidence`.
The failure is at interpretation, before investigating both clauses arises.

Combined with its existing failure to decline on unanswerable questions, the pattern is: strong
at choosing what to measure when a question is simple and singular, weak at recognising when a
question is not that. Written up as observed rather than as the mechanism predicted.

## Two fixes the plan did not anticipate

**`avoids_redundant_experiments` was counting the wrong thing.** It scored bare tool-name
repeats — a proxy for "did the same work twice" that was adequate only while an investigation
could see one metric. A legitimate two-metric run executes `analyze_time_series_trend` twice,
which the proxy misread as redundancy. It now counts `(tool, measured column)`, with a fallback
to tool names so investigations persisted before `executed_requests` existed still score rather
than silently passing. Flagged in the 32-02 summary, approved before implementing; `33-VALIDATION`
listed `agency.py` as out of scope.

**`unresolved` had to count as not-held.** The new case failed even against a *correct*
two-claim policy: margin came back `unresolved`, and the `mixed` branch counted only
`rejected + weakened`. Reporting "growth is slowing, margin could not be determined" as
`supported` tells the user their whole question came back favourably. `unresolved` now counts as
not-held, and the enum docstring says so.

## The case-count guard did its job

Adding the fifth hard case immediately failed
`test_the_hard_tier_keeps_its_headroom`: *"the hard tier has 5 cases but the baseline was
recorded against 4."* That assertion was added in phase 32 precisely so a ceiling could not
silently bound a different case set. Re-recorded 4 → 5.

## Verification

- `1109 passed, 10 skipped`
- `ruff` clean; `mypy backend` 53 before/after; no OpenAPI drift
- Tripwire 14/14 throughout — the published core paths never moved
- Prices re-checked against the provider before spending; model id verified
- README: single-metric limitation removed, every unrelated limit retained

## Phase 33 complete

An investigation can now examine as many metrics as it has claims. The benchmark case that
proved the limitation is the case that measures its absence.

## Carried forward

- `select_experiment` remains unprobed — `expected_information_gain` is fixed by the planner's
  tool ordering, so a case would test disagreement with that rather than reasoning
- 26 documented settings still not forwarded by compose
- `ModelCall` persistence for agentic policy calls; cached-input pricing tier
- `--max-cost-usd` truncation still unproven against a real ceiling ($0.38 against $3.00)
