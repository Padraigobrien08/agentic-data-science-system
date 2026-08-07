# Agency Scoreboard — `suite_agency_v1`

**Measured:** 2026-08-07 · **Prompts:** `1.0.1` · **Model snapshot:** `gpt-5.4-mini-2026-03-17` · **Trials:** 5 per policy

[`suite_agency_v1`](agency-evaluation.md) scores whether the investigation loop *reasons* well —
concludes when the evidence supports it, revises when contradicted, declines when it cannot,
and tests a claim before accepting it. Every check is derived from persisted typed state, so a
verdict is reproducible and never a model judging a model.

The suite takes any `AgentPolicy`. This page is what happened when it was pointed at a real one.

## Result

| policy | trials | pass rate | avoids_redundant_experiments | calibrated_confidence | challenges_before_concluding | path_adapts_to_goal | preserves_contradicting_evidence | reaches_the_right_disposition | respects_budget | revises_under_contradiction | terminates_for_the_right_reason | mean $ | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fixture | 5 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 0.0000 | 0.00 |
| gpt-5.4-mini | 5 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 0.0523 | 11.12 |

Zero unstable cases for either policy: every one of the 13 cases returned the same verdict on
all 5 trials. Total spend for the model row: **$0.26**.

`fixture` is `FixtureAgentPolicy`, a deterministic rule engine — keyword-matched intent,
falsification-first selection, challenge-the-strongest-claim critique. It is a tuned baseline,
not a strawman.

## The headline is that this suite is saturated

**`suite_agency_v1` cannot currently tell a keyword-matching rule engine apart from a frontier
model.** Both score 100% on all nine properties with no variance across five trials.

This is the result, and it is more useful than a favourable number would have been. Read
honestly, it says:

- Nothing about `gpt-5.4-mini`'s reasoning beyond "it clears this bar."
- Something about the suite: the cases discriminate against *broken* agents (see
  [the discrimination table](agency-evaluation.md#does-the-suite-actually-discriminate)) but
  not between *competent* ones. The ceiling is too low to rank.

Hardening `AGENCY_CASES` is the follow-up. Until then, no ranking claim should be made from
this page.

## What the run did establish

**The suite detects real defects.** The first live measurement, on prompt `1.0.0`, scored 62%
(8/13) with `terminates_for_the_right_reason` at 0%. That was not a reasoning failure: the
critic prompt told the model to decline with *"`should_challenge: false` with nulls"*, but only
two of `CritiqueProposal`'s five fields are nullable. The model declined correctly, sent
`"message": null`, failed validation, and tripped the loop's fail-safe into `reason=error` —
losing every case that reached a supported claim. Prompt `1.0.1` names the nullable fields;
the same suite then scored 13/13.

One prompt version, +38 points. The suite caught a systematic fault that a spot check would
have missed, and versioned prompts made the before/after comparable. `1.0.0` remains on disk
as the artifact that produced the 62%.

**Determinism at temperature 0 is not free but was observed here.** A model policy can return
different decisions on identical input, which is why trials and stability tracking exist. Over
5 trials × 13 cases, `gpt-5.4-mini` never changed a verdict. That is a property of this suite's
cases — mostly unambiguous fixtures — and should not be assumed to hold on harder ones.

## Cost and latency

On this suite the deterministic policy **dominates**: identical score, no spend, and roughly
2,800× faster.

| | mean $ / trial | p95 per investigation |
|---|---|---|
| fixture | $0.0000 | 0.004 s |
| gpt-5.4-mini | $0.0523 | 11.12 s |

The honest reading is not "the model is not worth it" — it is that *this suite's cases are
inside the deterministic policy's competence*, so they cannot show what a model buys. The
question a hardened suite should answer is where the rule engine starts failing and whether the
model's $0.05 and 11 seconds close that gap.

`p95 s` is the 95th percentile across **investigations** (one per case), not across trials.

## Reproducing

```bash
python -m backend.dev.agency_bench \
  --policy fixture --policy model --model gpt-5.4-mini \
  --trials 5 --max-cost-usd 2.00 --format both --out scoreboard
```

Requires a configured provider and priced models. The harness refuses a model row when either
is missing, rather than reporting a fixture result under a model's name or a $0.00 cost column
that would leave `--max-cost-usd` unable to fire.

| | |
|---|---|
| Suite | `suite_agency_v1`, 13 cases, 9 properties |
| Prompts | `edgar.agentic.{goal_interpreter,hypothesis_generator,experiment_selector,critic}` @ `1.0.1` |
| Model | `gpt-5.4-mini` → resolved `gpt-5.4-mini-2026-03-17` |
| Pricing | $0.75 / $4.50 per 1M in/out ([source](https://developers.openai.com/api/docs/models/gpt-5.4-mini), checked 2026-08-07) |
| Baseline | `FixtureAgentPolicy` |

Cost is a slight over-estimate: `ModelPrice` has no cached-input tier, so cached reads are
billed at the full input rate.

The free offline half of this measurement — the fixture policy against committed per-property
floors in `agentic/evaluation/baselines/fixture_floors.json` — runs on every pull request. The
model rows above are on-demand only.
