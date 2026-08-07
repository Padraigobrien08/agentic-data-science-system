# Agency Evaluation (`suite_agency_v1`)

The benchmark suites in `edgar_project/evaluation/` check **outputs**: did the pipeline
produce the right artifacts with the right numbers. That is necessary, and it is unchanged.

It says nothing about the question an agentic system actually has to answer well:

> Given evidence, does the loop draw the right conclusion, revise when contradicted, and
> decline when the data cannot support a claim?

`suite_agency_v1` measures that.

```bash
python -m agentic.evaluation
```

```
suite_agency_v2: 13/13 cases passed (100%)

Per-property pass rate:
   100%  avoids_redundant_experiments
   100%  calibrated_confidence
   100%  challenges_before_concluding
   100%  path_adapts_to_goal
   ...
```

Exit code is non-zero when any case fails, so it can gate a change.

This runs the **core** tier. `suite_agency_v1` — the 13 frozen, published cases — is the core
tier today; `--tier hard` runs the cases the deterministic baseline is designed to fail, and
`--tier all` runs both. The default is core precisely so the exit code stays usable as a gate:
the hard tier is expected to fail for the deterministic policy, and a permanently red command
signals nothing when a real regression arrives.

## Two failure modes, weighted equally

The scoring treats opposite errors as equally bad:

- **Overclaiming** — asserting a trend in flat or noisy data; confirming a hypothesis the
  evidence contradicts; cherry-picking the entity that agrees with the goal.
- **Underclaiming** — concluding "insufficient evidence" on an unambiguous signal.

The second is the one most agent evals miss. **An agent that always hedges is never wrong on
adversarial cases**, so a suite made only of traps would score it perfectly. The positive
controls (`clear_rising_is_concluded`, `clear_falling_is_concluded`) exist to fail exactly that
agent, and they are load-bearing rather than filler.

## Properties

| Property | What it means |
|---|---|
| `terminates_for_the_right_reason` | Stops with the typed reason the evidence warrants |
| `reaches_the_right_disposition` | Concludes supported / refuted / insufficient in line with the data |
| `revises_under_contradiction` | A hypothesis the evidence opposes does not end up supported |
| `preserves_contradicting_evidence` | Opposing evidence is retained, not discarded for a tidy story |
| `path_adapts_to_goal` | The experiments chosen reflect what was asked |
| `avoids_redundant_experiments` | No tool is run twice for the same question |
| `respects_budget` | Stays within the resource bounds it was given |
| `calibrated_confidence` | Confidence is proportional to the strength of the evidence |
| `challenges_before_concluding` | A claim it accepted was first tested by an independent method it chose to run |

`challenges_before_concluding` exists because the adversarial behaviour degrades *quietly*
without it. `TerminationPolicy` accepts `tested or not unused`, so a loop whose critic never
fires still reaches `sufficient_evidence` at the same confidence and the same disposition — by
exhausting the candidate tools instead of testing the claim. Before this property was added,
disabling the critic entirely left the suite at 100%.

Every check is **deterministic**, read from persisted typed state — no model judging a model.
A verdict is reproducible and a regression is unambiguous. The per-property breakdown is what
makes the suite diagnostic rather than a single number: `calibrated_confidence 40%` points
somewhere specific.

## Fixtures

Seeded or formula-generated, so a case's verdict never depends on the run. A test asserts the
noisy fixture genuinely has no trend and the opposing fixture genuinely opposes — if a fixture
drifted, the case built on it would be silently invalid.

| Fixture | Designed to catch |
|---|---|
| `clear_rising` / `clear_falling` | Hedging on an unambiguous signal |
| `flat` | Manufacturing a trend from nothing |
| `noisy_no_trend` | Reading variation as direction |
| `too_short` | Claiming a trend from two points |
| `opposing_entities` | Cherry-picking the entity that agrees |
| `separated_groups` | Answering a between-group question with a trend experiment |

## Does the suite actually discriminate?

A suite that only proves the current agent passes is theatre. `tests/agentic/test_agency_suite.py`
runs deliberately bad agents and asserts the suite catches them:

| Agent | Result | Caught by |
|---|---|---|
| Baseline (deterministic policy) | 13/13 | — |
| `HedgingPolicy` — never selects an experiment | 6/13 | Both positive controls; `preserves_contradicting_evidence` and `challenges_before_concluding` 0%, `terminates_for_the_right_reason` 20%, `reaches_the_right_disposition` 33% |
| `AlwaysTrendPolicy` — reads every goal as a trend | 11/13 | `comparison_goal_uses_comparison_tools`, `clear_falling_is_concluded`; `path_adapts_to_goal` 50% |

These discrimination tests are what make the baseline 13/13 meaningful.

They also mark the limit of that meaning. The suite reliably separates a *broken* agent from a
working one, and it caught a prompt defect worth 38 points. It does **not** separate competent
agents from each other: `gpt-5.4-mini` and the deterministic baseline both score 13/13 on every
property — see [the scoreboard](agency-scoreboard.md). Raising that ceiling is open work.

## Running it against a real model

The suite takes any `AgentPolicy`, so the same cases can be pointed at a model-backed policy:

```python
from agentic.evaluation import run_agency_suite, format_report
from backend.agents.agentic_model_policy import build_agent_policy

print(format_report(run_agency_suite(policy=build_agent_policy(settings))))
```

That is the intended use: does a real model reason at least as well as the deterministic
baseline, and does upgrading it help or hurt? Pairs naturally with
[replay & diff](replay-and-diff.md), which asks the same question about persisted runs.

### The benchmark harness

One pass of a non-deterministic policy is an anecdote, not a measurement, so
`backend/dev/agency_bench.py` runs repeated trials and aggregates them with variance,
cost, and latency:

```bash
python -m backend.dev.agency_bench \
  --policy fixture --policy model --model gpt-5.4-mini \
  --trials 5 --max-cost-usd 2.00 --format both --out scoreboard
```

A case whose verdict changes across trials is listed as **unstable** rather than averaged into
a number that reads as "mostly fine". Cost and latency come from the `InvestigationEnded`
events the loop already emits, so quality and spend are measured on the same run.

The harness refuses a model row when no provider is configured, or when the model has no
configured price — the first would publish a fixture result under a model's name, the second
would leave `--max-cost-usd` summing a quantity that is always zero. `--allow-unpriced` opts
into a quality-only run.

It lives in `backend/dev` because assembling a model-backed policy needs settings, a provider,
and the prompt registry, none of which `agentic/` may import. `python -m agentic.evaluation`
stays offline, free, and deterministic.

### Results

See **[the agency scoreboard](agency-scoreboard.md)** for the current measurement.

Short version as of 2026-08-07: `gpt-5.4-mini` and the deterministic baseline both score 100%
on all nine properties over five trials, so **the suite is currently saturated and cannot rank
competent policies**. It does still catch broken ones — it found a prompt defect that cost 38
points — but hardening `AGENCY_CASES` is the open follow-up before any ranking claim.

## Scope

`suite_agency_v1` is deliberately **not** registered in
`edgar_project/evaluation/catalog.py`. That catalog's `BenchmarkInput` / `ExpectedArtifacts`
shapes are built around tickers, fixture paths, and artifact assertions; agency cases are about
reasoning over a generic frame. Forcing one into the other would distort both. The offline
default suite (`suite_fixtures_v1`) and the CLI entry points are untouched.

**Follow-up:** exposing agency runs through the evaluation control-plane API (so they persist
`EvaluationRun` rows like the other suites) is not implemented; the suite is CLI- and
library-level today.
