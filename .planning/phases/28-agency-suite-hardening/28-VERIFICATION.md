---
phase: 28-agency-suite-hardening
verified: 2026-08-07T16:10:00Z
status: passed
---

# Phase 28 Verification

## Goal

Give `suite_agency_v1` headroom, so the agency benchmark can rank competent policies rather than
only separate broken ones from working ones.

## Verified Truths

1. `suite_agency_v1` is frozen at 13 cases, pinned by id, and still reproduces its published
   100% for the deterministic baseline.
2. Every case tagged `hard` fails `FixtureAgentPolicy` on a named `AgencyProperty` — enforced
   per-case by a free offline test.
3. The hard tier's failures span five properties, so it cannot be cleared by one narrow fix.
4. The tier includes a case where declining is correct, preserving the suite's pairing
   discipline.
5. The PR gate fails both when the baseline regresses on core (floors) and when it starts
   passing hard cases (ceiling), and a ceiling breach names both possible causes.
6. `python3 -m agentic.evaluation` runs offline, free, and deterministic, and its exit code is
   still usable as a gate.
7. Core and hard are never averaged into one number, in aggregation or in the published table.
8. Every registered fixture is deterministic across repeated builds.
9. The README's unrelated stated limits are unchanged.

## Result

The suite discriminates. Hard tier: `FixtureAgentPolicy` **0%**, `gpt-5.4-mini` **75%**, stable
across five trials, zero unstable cases, $0.35 total.

The model fails exactly one hard case — `unanswerable_premise_is_declined` — reaching
`sufficient_evidence` / `supported` / confidence 0.95 on a question the data cannot answer. It
reasons well about what to analyse and does not decline when it should.

## Evidence

- `agentic/evaluation/cases.py` — `CaseTier`, frozen `SUITE_V1_CASES`, four hard cases
- `agentic/evaluation/fixtures.py` — four new deterministic fixtures
- `agentic/evaluation/scoreboard.py` — per-tier aggregation
- `backend/dev/agency_bench.py` — `--tier`, shared cost ceiling across a policy's tiers
- `agentic/evaluation/baselines/fixture_floors.json` — core floors, hard ceiling and case count
- `tests/agentic/test_agency_tiers.py` — the admission rule
- `tests/agentic/test_agency_floors.py` — floors and headroom
- `docs/agent/agency-scoreboard.md` — the measurement, with v1 retained
- `data/evaluation/agency/scoreboard-2026-08-07-v2.json` — raw output

## Validation

- `python3 -m pytest -q` — 985 passed, 10 skipped
- `python3 -m ruff check .` — clean
- `python3 -m mypy backend` — 53 before and after; none in files this phase touched
- `python3 -m agentic.evaluation` — core 13/13, exit 0
- `python3 -m agentic.evaluation --tier hard` — 0/4, exit 1, by design
- `python3 scripts/export-openapi.py --check` — no drift

## Mutation Checks

Every new gate was shown to fail for the right reason, per `28-VALIDATION.md`:

| Mutation | Guard that fired |
|---|---|
| Tag a rule-engine-passing case as `hard` | admission contract |
| Soften a hard case's expectations | headroom ceiling, and the contract independently |
| Remove the declining case's expectations | pairing guard |
| Drift the recorded hard case count | baseline count assertion |

## Rejected On Evidence

Two planned case types were attempted and dropped rather than forced:

- **`select_experiment`** — `expected_information_gain` is `0.85 - 0.1 * position` in the intent
  tool list, so such a case would test disagreement with the planner's ordering, not reasoning.
- **`generate_hypotheses`** — structurally unwinnable: the planner parameterises every tool from
  one `metric_hint`, so a second hypothesis over a second metric stays `proposed` for any
  policy, including a perfect one.

## Carried Forward

- Lift the single-metric limitation — prerequisite for widening the hard tier, and a real
  product constraint in its own right
- `ModelCall` persistence for agentic policy calls (from 27-01)
- Cached-input pricing tier
- `--max-cost-usd` truncation unproven against a real ceiling
