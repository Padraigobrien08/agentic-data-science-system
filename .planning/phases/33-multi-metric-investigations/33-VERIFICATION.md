---
phase: 33-multi-metric-investigations
verified: 2026-08-08T21:00:00Z
status: passed
---

# Phase 33 Verification

## Goal

Lift the single-metric limitation: an investigation could examine exactly one metric, stranding
every additional claim at `proposed` however well the agent reasoned.

## Verified Truths

1. Experiments are parameterised from the metric of the hypothesis they target.
2. Every open hypothesis receives candidates; the same tool serves two claims on two metrics,
   and does not repeat for one metric.
3. Sufficiency requires that no hypothesis is still `proposed`, and the challenge requirement
   applies per supported claim.
4. A split outcome reports `mixed`, naming both sides, with confidence averaged across all
   claims. `unresolved` counts as not-held.
5. A two-claim investigation completes under the default budget and is resumable — resuming
   reproduces the same tools and statuses as an uninterrupted run.
6. Candidate ordering is a pure function of state, stable across calls.
7. `fit_simple_regression` and the parameterless tools still work.
8. **The published core-tier paths never moved** — tool sequence, termination, disposition and
   confidence identical for all 13 frozen cases, throughout every change.
9. No database migration was required.

## Result

The 32-02 probe, before and after:

```
BEFORE:  [(['revenue_growth_pct'], 'supported'), (['margin_pct'], 'proposed')]
AFTER :  [(['revenue_growth_pct'], 'supported'), (['margin_pct'], 'weakened')]
```

Re-measured: hard tier 5 cases, fixture 0%, `gpt-5.4-mini` 60%, zero unstable, $0.38. Core 100%
for both policies.

## The plan was wrong twice, and the tripwire caught the second

**"No migration is required"** was half true. The domain model was multi-metric, but the planner
learns what has run from `executed_tools` — a flat set derived from results that record a tool
name only. No `(tool, hypothesis)` key was derivable from state. Resolved by retaining
`executed_requests`, after ruling out the reproducibility manifest (hash only) and evidence
(no tool, nothing for failures).

**"Sufficiency requires every hypothesis terminal"** broke five frozen cases.
`Hypothesis.is_terminal()` means no outgoing transitions and only `rejected` qualifies, so the
condition amounted to requiring every claim be rejected. Corrected to "nothing still
`proposed`". The tripwire failed loudly on a change that left the pass rate at 13/13 while
altering the route — exactly what it was armed for.

## Evidence

- `agentic/domain/investigation.py` — `executed_requests`
- `agentic/agent/components.py` — `_metric_for`, `_executed_pairs`, per-hypothesis candidates,
  sufficiency across claims, the `mixed` branch
- `agentic/domain/enums.py` — `ConclusionDisposition.mixed`
- `agentic/agent/budget.py` — documented scaling, default unchanged
- `agentic/evaluation/agency.py` — `(tool, metric)` redundancy units
- `agentic/evaluation/cases.py`, `fixtures.py` — the two-part hard case
- `tests/agentic/test_core_tier_equivalence.py`, `test_planner_parameterisation.py`,
  `test_multi_hypothesis_termination.py`
- `docs/agent/{termination-policy,investigation-loop,agency-evaluation,agency-scoreboard}.md`
- `data/evaluation/agency/scoreboard-2026-08-08-v3.json`

## Validation

- `python3 -m pytest -q` — 1109 passed, 10 skipped
- `python3 -m ruff check .` — clean
- `python3 -m mypy backend` — 53 before and after
- `python3 -m agentic.evaluation` — core 13/13, exit 0
- `python3 scripts/export-openapi.py --check` — no drift
- Tripwire 14/14 at every step

## Mutation Checks

| Mutation | Guard |
|---|---|
| Reorder a tool's intent priority | core-tier tripwire |
| Ignore the hypothesis metric | 5 of 11 planner tests |
| Dedup on tool alone | 4 of 11 planner tests |
| Restore "first supported claim wins" | stranding tests |
| Route a split outcome back to `supported` | 4 of 12 termination tests |
| Add a fifth hard case without re-recording | hard-tier case-count guard |

## Carried Forward

- `select_experiment` still unprobed by the hard tier
- 26 documented settings not forwarded by compose, several security controls
- `ModelCall` persistence for agentic policy calls; cached-input pricing tier
- `--max-cost-usd` truncation unproven against a real ceiling
