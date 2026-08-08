---
phase: 32-agency-suite-hardening
plan: 01
status: completed
completed: 2026-08-07
requirements:
  - HARD-01
  - HARD-02
---

# Summary 32-01: Tiering and the discrimination contract

## What shipped

- **`CaseTier`** (`core` | `hard`) on `AgencyCase`, defaulted to `core` so the 13 published
  cases are unchanged byte-for-byte.
- **`SUITE_V1_CASE_IDS` / `SUITE_V1_CASES`** — the freeze, pinned by id. `SUITE_V1_ID` stays
  `suite_agency_v1`; the full set is `suite_agency_v2`.
- **`cases_for_tier()`** and a `tier=` filter on `run_agency_suite`.
- **`support_desk_slowing` fixture** — three metrics where the goal-relevant one
  (`median_resolution_hours`, rising) is deliberately last and the flat volume metrics come
  first.
- **First hard case**, `implied_metric_is_selected_over_the_default`.
- **`tests/agentic/test_agency_tiers.py`** — the admission rule, enforced per-case.
- **Per-tier baseline** — `core` floors, `hard.max_pass_rate` ceiling — and the headroom test.

## The first hard case

Goal: *"are we getting slower at resolving customer issues?"*

It defeats two `FixtureAgentPolicy` heuristics at once, verified before the case was written:

- **Intent.** No keyword in the goal matches the intent table, so the rule engine falls through
  to `general` → `profile_dataset` / `summarize_distribution`. It never reaches
  `analyze_time_series_trend`.
- **Metric.** No metric name appears in the goal text, so `metrics[0]` selects
  `tickets_opened` — flat — producing a defensible-looking "no trend" on the wrong column.

Observed: `FixtureAgentPolicy` fails on `terminates_for_the_right_reason`,
`reaches_the_right_disposition`, and `path_adapts_to_goal`. A policy that reads the goal as a
trend on `median_resolution_hours` passes. The case is therefore winnable and fails for a
reasoning reason, not a capability gap.

## Mutation checks

Both new gates were shown to fail for the right reason:

| Mutation | Result |
|---|---|
| Tag a case the rule engine passes as `hard` | contract fails: *"is tagged hard but FixtureAgentPolicy passes it, so it does not discriminate"* |
| Soften the hard case's expectations | ceiling fails: *"now passes 100% of the hard tier, above the committed ceiling of 0%"* — and the contract catches it independently |

## Deviations from plan

**The freeze is pinned by id, not read from the scoreboard doc.** Task 1 said to assert the v1
ids match "the ids named in `docs/agent/agency-scoreboard.md`'s reproduction section". That
section names the suite and case *count*, not the ids, so there was nothing to match against.
Pinning an explicit id tuple in `cases.py` is the stronger freeze anyway — deriving the subset
from `tier == core` would let a future core case silently join it and change what "the v1
result" means. A second test asserts every pinned id still resolves, so a rename cannot shrink
the frozen suite silently.

**`python -m agentic.evaluation` now takes `--tier`, defaulting to `core`.** Not in the plan,
and needed. Adding a tier the baseline is *designed* to fail made the default invocation exit
1 permanently — and that command's exit code is documented as a gate. A permanently red gate
says nothing when a real regression arrives. The default runs core and prints a footer naming
the hard cases it skipped and why; `--tier hard` and `--tier all` are available.

**`test_the_deterministic_baseline_passes_the_suite` was scoped to core.** It asserted a clean
sweep across every case, which is now the opposite of what the hard tier is for.

**Two hardcoded `"suite_agency_v1"` strings** had to move to the constant —
`tests/test_agency_bench.py` and the `suite_id` in `fixture_floors.json`.

## Verification

- `947 passed, 10 skipped` (was 937; 10 new tests)
- `ruff check .` clean; `mypy backend` 53 before/after
- `python3 -m agentic.evaluation` — core, 13/13, exit 0
- `python3 -m agentic.evaluation --tier hard` — 0/1, exit 1, as designed
- Frozen v1 reproduces the published result: `suite_agency_v1: 13/13`, all nine properties 100%

## Note for 32-03

`backend/dev/agency_bench.py` currently measures all tiers into one row, so its fixture number
reads 93% rather than 100%/0% split. That is exactly the averaging problem 32-03 Task 1 fixes
with `--tier`; the scoreboard must not be published from a mixed row.

## Next

32-02: fixtures and the rest of the hard cases, covering at least three more policy decisions
and including one where declining is correct.
