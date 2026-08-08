---
phase: 32-agency-suite-hardening
plan: 03
status: completed
completed: 2026-08-07
requirements:
  - HARD-04
  - HARD-05
---

# Summary 32-03: Per-tier reporting, re-measurement, publication

## The result

**The suite discriminates.** On the hard tier the deterministic baseline scores 0% and
`gpt-5.4-mini` 75% — a 75-point gap where `suite_agency_v1` had none.

| policy | tier | trials | pass rate | mean $ | p95 s |
|---|---|---|---|---|---|
| fixture | core | 5 | 100% | 0.0000 | 0.004 |
| fixture | hard | 5 | **0%** | 0.0000 | 0.005 |
| gpt-5.4-mini | core | 5 | 100% | 0.0522 | 13.02 |
| gpt-5.4-mini | hard | 5 | **75%** | 0.0174 | 14.43 |

Zero unstable cases in any row — every case returned the same verdict on all five trials. Total
spend **$0.35** against a $3.00 ceiling. The frozen v1 core tier reproduced its published 100%.

## What the model gets wrong, specifically

`gpt-5.4-mini` passes three hard cases and fails one, identically every trial:

- **passes** metric selection, intent selection, dimension inference
- **fails** `unanswerable_premise_is_declined` — `sufficient_evidence`, `supported`,
  confidence **0.95** on a question the dataset cannot answer

The pattern: it reasons well about *what* to analyse, and does not decline when the data cannot
answer the question at all. Asked about complaint volume over a dataset holding only latency and
throughput, it substitutes the nearest rising metric and reports high confidence. On that case
its behaviour is indistinguishable from the rule engine's.

That is the more consequential failure mode for an analysis agent — a wrong metric is visible to
a reader, a confident answer to an unasked question is not — and it is exactly what the tier's
counterweight case was built to catch.

## What shipped

- **Per-tier reporting.** `PolicyScorecard.tier`, tier column in the markdown (omitted when no
  row is tiered), `--tier {core,hard,all}` on the bench, one row per (policy, tier). The cost
  ceiling accumulates across a policy's tiers so one ceiling covers the whole policy rather than
  one per tier.
- **The measurement**, archived at `data/evaluation/agency/scoreboard-2026-08-07-v2.json`.
- **`docs/agent/agency-scoreboard.md`** rewritten, with the phase 31 v1 result retained below
  for comparison rather than overwritten.
- **README** — agency evaluation promoted to Stable with the discriminating result; the
  saturation bullet replaced by three specific limits.

## Deviations from plan

**Two existing bench tests assumed one row per policy** and had to be made tier-aware. Not a
deviation in intent, but worth recording: the row shape is now (policy, tier), and anything
counting rows needs to know that.

**The README gained more limits than it lost.** The plan anticipated replacing the saturation
caveat with a success claim. The result supports promoting agency evaluation to Stable — it
genuinely discriminates — but the same run also produced three findings that belong in Known
limits: the tier only covers `interpret_goal`, the loop can examine only one metric, and the
model overclaims on unanswerable questions. Publishing the win without those would misrepresent
what was measured.

## Verification

- `985 passed, 10 skipped`
- `ruff check .` clean; `mypy backend` 53 before/after
- `python3 -m agentic.evaluation` — core 13/13, exit 0
- `scripts/export-openapi.py --check` — no drift
- Prices re-checked against the provider's published rates before spending; model id re-verified
- No row `truncated`; all 20 requested trials completed

## Carried forward

- **Lift the single-metric limitation** — the prerequisite for widening the hard tier beyond
  `interpret_goal`, and a real product constraint independent of the benchmark
- `ModelCall` persistence for agentic policy calls (from 31-01)
- Cached-input pricing tier — reported cost remains a slight over-estimate
- `--max-cost-usd` truncation still unproven against a real ceiling ($0.35 against $3.00)
