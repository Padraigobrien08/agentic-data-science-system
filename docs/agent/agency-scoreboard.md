# Agency Scoreboard — `suite_agency_v2`

**Measured:** 2026-08-07 · **Prompts:** `1.0.1` · **Model snapshot:** `gpt-5.4-mini-2026-03-17` · **Trials:** 5 per policy per tier

[`suite_agency_v2`](agency-evaluation.md) scores whether the investigation loop *reasons* well —
concludes when the evidence supports it, revises when contradicted, tests a claim before
accepting it, and declines when the data cannot answer the question. Every check is derived from
persisted typed state, so a verdict is reproducible and never a model judging a model.

The suite has two tiers. **Core** is the frozen `suite_agency_v1`, 13 cases. **Hard** is 4 cases
admitted only if they defeat the deterministic baseline — see [the admission
rule](agency-evaluation.md#admission-rule).

## Result

| policy | tier | trials | pass rate | avoids_redundant | calibrated_confidence | challenges_before_concluding | path_adapts_to_goal | preserves_contradicting | reaches_right_disposition | respects_budget | revises_under_contradiction | terminates_right_reason | mean $ | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fixture | core | 5 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 0.0000 | 0.00 |
| fixture | hard | 5 | **0%** | 100% | 0% | — | 0% | — | 0% | — | 0% | 0% | 0.0000 | 0.00 |
| gpt-5.4-mini | core | 5 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 0.0522 | 13.02 |
| gpt-5.4-mini | hard | 5 | **75%** | 100% | 0% | — | 100% | — | 100% | — | 50% | 100% | 0.0174 | 14.43 |

`—` marks a property no case in that tier asserts. Total spend: **$0.35**.

## The suite now discriminates

The [previous measurement](#previous-measurement-suite_agency_v1-2026-08-07) found `suite_agency_v1`
saturated: a keyword-matching rule engine and `gpt-5.4-mini` both scored 100% on every property,
so the suite could separate broken agents from working ones but could not rank competent ones.

The hard tier closes that. On it the deterministic baseline scores **0%** and the model **75%** —
a 75-point gap where there was none. The core tier remains saturated by construction and is
retained for comparability with the published v1 result, not as a discriminator.

## What the model gets wrong

`gpt-5.4-mini` passes three hard cases and fails one, identically on all five trials:

| Case | Result |
|---|---|
| `implied_metric_is_selected_over_the_default` | **pass** — picks resolution time over the two volume metrics offered first |
| `ranking_goal_is_not_a_trend_goal` | **pass** — does not read "which region is weakest" as a question about time |
| `grouping_dimension_is_inferred_from_the_question` | **pass** — groups by plan tier, not by the first dimension available |
| `unanswerable_premise_is_declined` | **fail** — `sufficient_evidence`, `supported`, confidence **0.95** |

The pattern is specific and worth stating plainly: **the model reasons well about *what* to
analyse, and does not decline when the data cannot answer the question at all.** Asked whether
customer complaint volume is increasing, over a dataset holding only latency and throughput, it
substitutes the nearest rising metric and reports a confident, well-evidenced conclusion about
something nobody asked.

On that case its behaviour is indistinguishable from the rule engine's. The three cases it
passes reward finding the right answer; the one it fails is the tier's counterweight, where the
correct move is to decline. For an analysis agent that is the more consequential failure mode:
a wrong metric is visible to a reader, a confident answer to an unasked question is not.

## Stability

**Zero unstable cases in any row.** Every case returned the same verdict on all five trials,
for both policies. The model's 75% is therefore a stable property of its reasoning on these
cases, not a lucky sample — which matters, because a hard case whose verdict flapped would not
yet have earned its place in the tier.

## Cost and latency

| | mean $ / trial | p95 per investigation |
|---|---|---|
| fixture (either tier) | $0.0000 | ~0.004 s |
| gpt-5.4-mini core (13 cases) | $0.0522 | 13.02 s |
| gpt-5.4-mini hard (4 cases) | $0.0174 | 14.43 s |

Per-trial cost tracks case count, so the tiers are not directly comparable — per case the two
are close (~$0.004). Cost is a slight over-estimate: `ModelPrice` has no cached-input tier, so
cached reads are billed at the full input rate.

Unlike the v1 measurement, the deterministic policy no longer dominates. It is still free and
~3,000× faster, but it now scores 0% where the model scores 75%, so the $0.02 and 14 seconds
buy something the rule engine cannot do.

## What this does not measure

All four hard cases defeat `interpret_goal`, across four different judgements. Cases targeting
the other two model-backed decisions were attempted and are not fairly constructible against the
current loop — `expected_information_gain` is fixed by the planner's ordering, and a two-metric
hypothesis can never be investigated because every tool is parameterised from a single
`metric_hint`. Both are documented in [agency-evaluation.md](agency-evaluation.md#what-the-tier-does-not-cover).

The second of those is a real product limitation, not only a benchmark gap: **an investigation
can examine one metric.** A multi-part question strands its second hypothesis at `proposed`
however well the policy reasons.

## Reproducing

```bash
python -m backend.dev.agency_bench \
  --policy fixture --policy model --model gpt-5.4-mini \
  --trials 5 --tier all --max-cost-usd 3.00 --format both --out scoreboard
```

| | |
|---|---|
| Suite | `suite_agency_v2` — 13 core + 4 hard, 9 properties |
| Prompts | `edgar.agentic.{goal_interpreter,hypothesis_generator,experiment_selector,critic}` @ `1.0.1` |
| Model | `gpt-5.4-mini` → resolved `gpt-5.4-mini-2026-03-17` |
| Pricing | $0.75 / $4.50 per 1M in/out ([source](https://developers.openai.com/api/docs/models/gpt-5.4-mini), re-checked 2026-08-07) |
| Baseline | `FixtureAgentPolicy` |
| Raw result | `data/evaluation/agency/scoreboard-2026-08-07-v2.json` |

The free offline half — the fixture policy against committed per-property floors, plus a
headroom ceiling on the hard tier — runs on every pull request. The model rows are on-demand only.

---

## Previous measurement: `suite_agency_v1`, 2026-08-07

Retained because the core tier is frozen and this result stays reproducible.

| policy | trials | pass rate | all 9 properties | mean $ | p95 s |
|---|---|---|---|---|---|
| fixture | 5 | 100% | 100% | $0.0000 | 0.004 |
| gpt-5.4-mini | 5 | 100% | 100% | $0.0523 | 11.12 |

That run's finding was the saturation itself. It also caught a real defect: on prompt `1.0.0`
the model scored 62%, because the critic prompt told it to decline "with nulls" while only two
of `CritiqueProposal`'s five fields are nullable — a null `message` failed validation and tripped
the loop's fail-safe into `reason=error`, losing every case that reached a supported claim.
Prompt `1.0.1` fixed the contract description and the same suite scored 13/13. One prompt
version, +38 points.

Raw result: `data/evaluation/agency/scoreboard-2026-08-07.json`.
