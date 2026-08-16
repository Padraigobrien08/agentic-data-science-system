# Agency Scoreboard — `suite_agency_v2`

**Measured:** 2026-08-08 · **Prompts:** `1.0.1` · **Model snapshot:** `gpt-5.4-mini-2026-03-17` · **Trials:** 5 per policy per tier

[`suite_agency_v2`](agency-evaluation.md) scores whether the investigation loop *reasons* well —
concludes when the evidence supports it, revises when contradicted, tests a claim before
accepting it, declines when the data cannot answer the question, and answers every part of a
question that has more than one. Every check is derived from persisted typed state, so a verdict
is reproducible and never a model judging a model.

Two tiers. **Core** was the frozen `suite_agency_v1`, 13 cases, when this was measured; it has
since gained regression cases the baseline passes, so a fresh core run reports a larger total
than the rows below. `suite_agency_v1` itself is unchanged, which is what keeps this
measurement readable. **Hard** is 5 cases admitted only if they defeat the deterministic
baseline — see [the admission rule](agency-evaluation.md#admission-rule).

## Result

| policy | tier | trials | pass rate | avoids_redundant | calibrated_confidence | challenges_before | path_adapts | preserves_contradicting | right_disposition | respects_budget | revises_under_contradiction | right_termination | mean $ | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fixture | core | 5 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 0.0000 | 0.00 |
| fixture | hard | 5 | **0%** | 100% | 0% | — | 0% | — | 0% | — | 0% | 0% | 0.0000 | 0.01 |
| gpt-5.4-mini | core | 5 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 0.0524 | 7.79 |
| gpt-5.4-mini | hard | 5 | **60%** | 84% | 0% | — | 100% | — | 67% | — | 50% | 100% | 0.0227 | 8.71 |

`—` marks a property no case in that tier asserts. Total spend: **$0.38**. Zero unstable cases in
any row, and no row truncated.

## What the model gets wrong

`gpt-5.4-mini` passes three hard cases and fails two, identically on all five trials:

| Case | Result |
|---|---|
| `implied_metric_is_selected_over_the_default` | **pass** |
| `ranking_goal_is_not_a_trend_goal` | **pass** |
| `grouping_dimension_is_inferred_from_the_question` | **pass** |
| `unanswerable_premise_is_declined` | **fail** — `supported` at confidence **0.95** |
| `two_part_goal_resolves_both_clauses` | **fail** — `insufficient_evidence`, ran only `rank_entities` |

Two distinct failures, and the second is not what we expected.

**It does not decline.** Asked whether customer complaint volume is increasing, over a dataset
holding only latency and throughput, it substitutes the nearest rising metric and reports a
confident, well-evidenced conclusion about something nobody asked. On that case its behaviour is
indistinguishable from the rule engine's.

**It misreads compound questions.** The two-part case was added expecting the model to answer the
first clause and drop the second. Instead it never got that far: asked "is revenue growth slowing
**and** is margin quality holding up?", it read the question as a *ranking* problem, ran
`rank_entities`, and concluded `insufficient_evidence`. The failure is at interpretation, before
any question of investigating both clauses arises.

Both are failures of the same kind — the model is strong at choosing *what to measure* when the
question is simple and singular, and weak at recognising when a question is not that.

## Comparison with the previous measurement

The hard tier grew from 4 cases to 5. The model passes the same three.

| | hard tier | model |
|---|---|---|
| [2026-08-07](#previous-measurements) | 4 cases | 75% (3/4) |
| **2026-08-08** | **5 cases** | **60% (3/5)** |

The drop is the tier getting harder, not the model getting worse. The core tier is unchanged at
100% for both policies, which is the control confirming nothing else moved.

## The case that could not exist before

`two_part_goal_resolves_both_clauses` was designed during phase 32 and **dropped as unwinnable**.
The planner parameterised every tool from a single `interpretation.metric_hint`, so a second
hypothesis about a second metric stayed `proposed` forever — for *any* policy, however well it
reasoned. A case built on it would have failed a perfect agent.

Phase 33 removed that limitation: experiments are parameterised from the claim they test, and
sufficiency waits for every claim rather than firing on the first one supported. The case is now
winnable — verified against a two-claim policy — and discriminating.

With it, the hard tier defeats **two** of the four model-backed decisions rather than one.
`select_experiment` remains uncovered, for the unchanged reason that
`expected_information_gain` is fixed by the planner's tool ordering.

## Cost and latency

| | mean $ / trial | p95 per investigation |
|---|---|---|
| fixture | $0.0000 | ~0.01 s |
| gpt-5.4-mini core (13 cases) | $0.0524 | 7.79 s |
| gpt-5.4-mini hard (5 cases) | $0.0227 | 8.71 s |

Per-trial cost tracks case count, so the tiers are not directly comparable. Cost is a slight
over-estimate: `ModelPrice` has no cached-input tier, so cached reads are billed at the full
input rate.

## Reproducing

```bash
python -m backend.dev.agency_bench \
  --policy fixture --policy model --model gpt-5.4-mini \
  --trials 5 --tier all --max-cost-usd 3.00 --format both --out scoreboard
```

| | |
|---|---|
| Suite | `suite_agency_v2` — 13 core + 5 hard, 9 properties |
| Prompts | `edgar.agentic.{goal_interpreter,hypothesis_generator,experiment_selector,critic}` @ `1.0.1` |
| Model | `gpt-5.4-mini` → resolved `gpt-5.4-mini-2026-03-17` |
| Pricing | $0.75 / $4.50 per 1M in/out ([source](https://developers.openai.com/api/docs/models/gpt-5.4-mini)) |
| Raw result | `data/evaluation/agency/scoreboard-2026-08-08-v3.json` |

The free offline half — the fixture policy against committed per-property floors, plus a
headroom ceiling on the hard tier — runs on every pull request. The model rows are on-demand only.

---

## Previous measurements

Retained because the core tier is frozen and these results stay reproducible.

**2026-08-07 · `suite_agency_v2`, 4 hard cases** — fixture core 100% / hard 0%; `gpt-5.4-mini`
core 100% / hard 75%. Zero unstable cases, $0.35. The run that first showed the suite could
discriminate. Raw: `data/evaluation/agency/scoreboard-2026-08-07-v2.json`.

**2026-08-07 · `suite_agency_v1`, 13 cases** — both policies 100% on all nine properties, $0.35.
That run's finding was **saturation**: the suite could not tell a keyword-matching rule engine
from a frontier model. It also caught a real defect — on prompt `1.0.0` the model scored 62%,
because the critic prompt told it to decline "with nulls" while only two of
`CritiqueProposal`'s five fields are nullable; a null `message` tripped the loop's fail-safe and
lost every converging case. Prompt `1.0.1` fixed the contract description and the same suite
scored 13/13. Raw: `data/evaluation/agency/scoreboard-2026-08-07.json`.
