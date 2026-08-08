---
phase: 33-multi-metric-investigations
plan: 02
status: completed
completed: 2026-08-08
requirements:
  - MULTI-03
  - MULTI-04
---

# Summary 33-02: Termination and conclusion across claims

## The limitation is lifted

The probe from 28-02 that motivated this whole phase:

```
BEFORE:  [(['revenue_growth_pct'], 'supported'), (['margin_pct'], 'proposed')]
AFTER :  [(['revenue_growth_pct'], 'supported'), (['margin_pct'], 'weakened')]
```

Three experiments across two metrics. The second claim is investigated and reaches a verdict
instead of being stranded, and the conclusion reports `mixed` at confidence 0.70 naming both
sides — where before it reported `supported` at 0.95 and the refuted clause vanished.

## What shipped

- **Sufficiency across claims** — `TerminationPolicy.decide` no longer fires on the first
  supported hypothesis, and the challenge requirement applies per supported claim.
- **`ConclusionDisposition.mixed`**, branched before `supported` in `ConclusionSynthesizer`.
- **Budget documented, default unchanged** at 8.
- **`tests/agentic/test_multi_hypothesis_termination.py`** — 12 tests, including resume.
- `docs/agent/termination-policy.md` and `docs/agent/investigation-loop.md`.

## Deviation: the tripwire caught my first attempt

Task 1 specified sufficiency should require every hypothesis "terminal". Implemented literally
as `if state.open_hypotheses(): return False`, that broke **five** frozen core cases — each ran
one extra experiment before stopping.

`Hypothesis.is_terminal()` is `not ALLOWED_HYPOTHESIS_TRANSITIONS[status]`, and only `rejected`
has no outgoing transitions. A `supported` claim can still be weakened, so it is never terminal;
requiring terminality would mean requiring every claim to be **rejected**. Sufficiency could
never fire on its own terms, and runs fell through to the "no unused tools" path instead.

Corrected to **no hypothesis still `proposed`** — a claim past `proposed` has had evidence
brought to bear on it, one still at `proposed` has had nothing run against it. Single-claim
behaviour is then bit-identical, because the supported claim was already past `proposed` when
sufficiency used to fire.

This is exactly what the tripwire was armed for. It failed loudly on a change that left the pass
rate at 13/13 while altering the route.

## Budget: default left at 8

Measured against the deterministic policy:

| Claims | Experiments | Outcome |
|---|---|---|
| 1 | 2 | `sufficient_evidence` |
| 2 | 3 | `sufficient_evidence` |
| 3 | 7 | `sufficient_evidence` |
| 4 | 8 | `budget_exhausted` |

Two and three clauses complete comfortably. Four stops with a typed reason rather than silently
truncating, which is an honest outcome, and raising the cap would raise worst-case cost and
latency for every run to serve an unusual case. The reasoning is now in the field's description
and the docs.

## The enum was safe to extend

Checked before changing it, as promised. `dispositionTone` in
`frontend/src/lib/investigation-view.ts` has a `default:` branch that titleizes unknown values
with neutral styling; the DB column is a plain `String(64)`; `backend/schemas/investigation.py`
types it as `str`. `mixed` degrades gracefully with no frontend or backend change, and
`export-openapi.py --check` reports no drift.

## Mutation checks

| Mutation | Result |
|---|---|
| Restore "first supported claim wins" | *"the second claim was never investigated"*, *"terminated with 1 claim(s) never investigated"* |
| Route a split outcome back to `supported` | 4 of 12 fail |

## Verification

- `1103 passed, 10 skipped` (was 1091; 12 new)
- `ruff` clean; `mypy backend` 53 before/after; no OpenAPI drift
- Tripwire 14/14 — the published scoreboard still stands
- Multi-claim resume reproduces the same tools and statuses as an uninterrupted run

## Next

33-03: add back the two-part case 32-02 had to drop as unwinnable, re-baseline, re-measure,
publish. `autonomous: false` — it spends money.
