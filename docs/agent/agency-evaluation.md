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
suite_agency_v1: 10/10 cases passed (100%)

Per-property pass rate:
   100%  avoids_redundant_experiments
   100%  calibrated_confidence
   100%  path_adapts_to_goal
   ...
```

Exit code is non-zero when any case fails, so it can gate a change.

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
| Baseline (deterministic policy) | 10/10 | — |
| `HedgingPolicy` — never selects an experiment | 5/10 | Both positive controls; `calibrated_confidence` 60%, `preserves_contradicting_evidence` 0% |
| `AlwaysTrendPolicy` — reads every goal as a trend | 8/10 | `comparison_goal_uses_comparison_tools` |

These discrimination tests are what make the baseline 10/10 meaningful.

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

## Scope

`suite_agency_v1` is deliberately **not** registered in
`edgar_project/evaluation/catalog.py`. That catalog's `BenchmarkInput` / `ExpectedArtifacts`
shapes are built around tickers, fixture paths, and artifact assertions; agency cases are about
reasoning over a generic frame. Forcing one into the other would distort both. The offline
default suite (`suite_fixtures_v1`) and the CLI entry points are untouched.

**Follow-up:** exposing agency runs through the evaluation control-plane API (so they persist
`EvaluationRun` rows like the other suites) is not implemented; the suite is CLI- and
library-level today.
