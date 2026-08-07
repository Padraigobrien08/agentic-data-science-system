---
phase: 28-agency-suite-hardening
plan: 03
type: execute
wave: 3
depends_on: [01, 02]
files_modified:
  - agentic/evaluation/scoreboard.py
  - backend/dev/agency_bench.py
  - tests/agentic/test_scoreboard.py
  - tests/test_agency_bench.py
  - docs/agent/agency-scoreboard.md
  - data/evaluation/agency/
  - README.md
autonomous: false
requirements:
  - HARD-04
  - HARD-05
must_haves:
  truths:
    - "The scoreboard reports the hard tier separately, so a saturated tier can never hide inside an aggregate."
    - "The published v1 result stays reproducible and is not silently replaced."
    - "The re-measurement is reported as observed, including if the hard tier also fails to discriminate."
    - "The README's claim matches what has actually been measured."
  artifacts:
    - path: agentic/evaluation/scoreboard.py
      provides: "Per-tier aggregation so core and hard are never averaged together"
    - path: docs/agent/agency-scoreboard.md
      provides: "The re-measurement, with the v1 result preserved for comparison"
  key_links:
    - from: backend/dev/agency_bench.py
      to: agentic/evaluation/scoreboard.py
      via: "the bench measures each tier and reports them as separate rows"
      pattern: "tier|CaseTier|per_tier"
---

<objective>
Re-measure against the hardened suite and publish what it says.

Purpose: this is the question phase 27 could not answer — does a real model reason better than
a rule engine? The hard tier exists to make that answerable.
Output: per-tier reporting, a paid re-measurement, an updated scoreboard, and a README that
matches it.

**Not autonomous.** Task 2 spends money, and Task 3 requires judgement about a result that does
not exist yet.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/28-agency-suite-hardening/28-CONTEXT.md
@.planning/phases/28-agency-suite-hardening/28-VALIDATION.md
@.planning/phases/28-agency-suite-hardening/28-agency-suite-hardening-02-PLAN.md
@agentic/evaluation/scoreboard.py
@backend/dev/agency_bench.py
@docs/agent/agency-scoreboard.md
@docs/agent/agency-evaluation.md
@README.md
@.planning/phases/27-agency-benchmark-under-real-models/27-agency-benchmark-under-real-models-03-SUMMARY.md

<interfaces>
From `agentic/evaluation/scoreboard.py`:
```python
class PolicyScorecard(DomainModel):
    label: str
    trials: int
    mean_pass_rate: float
    property_means: dict[str, float]
    unstable_cases: list[CaseStability]
    total_cost_usd: float
    mean_cost_usd: float
    p95_latency_seconds: float
    truncated: bool

def aggregate_trials(label, reports, metrics=(), *, truncated=False) -> PolicyScorecard: ...
```

The phase 27 measurement this one is compared against — `suite_agency_v1`, prompts `1.0.1`,
`gpt-5.4-mini-2026-03-17`, 5 trials: both policies 100% on all nine properties, zero unstable
cases, $0.26.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Per-tier reporting</name>
  <files>agentic/evaluation/scoreboard.py
backend/dev/agency_bench.py
tests/agentic/test_scoreboard.py
tests/test_agency_bench.py</files>
  <read_first>agentic/evaluation/scoreboard.py
backend/dev/agency_bench.py
agentic/evaluation/runner.py</read_first>
  <behavior>
    - Core and hard results are reported separately and never averaged into one number — an
      aggregate would let a saturated core mask a discriminating hard tier, and vice versa.
    - The markdown table makes the tier of every row unambiguous.
    - `--tier` selects what to measure; omitting it measures both.
    - Existing single-tier behaviour and every existing test remain valid.
  </behavior>
  <action>Extend `agentic/evaluation/scoreboard.py` so a `PolicyScorecard` carries the tier it
describes, and `Scoreboard.to_markdown()` renders tier as a column or as separate tables —
whichever reads better with nine property columns. Add `--tier {core,hard,all}` to
`backend/dev/agency_bench.py`, defaulting to `all`, producing one row per (policy, tier). Keep
the existing guards — provider configured, model priced, cost ceiling, post-first-trial
unpriced detection — applying per policy, not per row, so a two-tier run does not double-charge
the ceiling check. Extend the tests: aggregation keeps tiers separate; the markdown names the
tier of each row; `--tier core` measures only the frozen v1 cases.</action>
  <acceptance_criteria>`agentic/evaluation/scoreboard.py` carries tier on the scorecard.
`backend/dev/agency_bench.py` contains `--tier`.
`tests/agentic/test_scoreboard.py` asserts tiers are not averaged together.
`tests/test_agency_bench.py` asserts `--tier core` measures only the v1 cases.
`python3 -m pytest tests/agentic tests/test_agency_bench.py -q --tb=short` passes.
`python3 -m backend.dev.agency_bench --policy fixture --trials 2 --tier all --format md` exits 0.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic tests/test_agency_bench.py -q --tb=short</automated>
  </verify>
  <done>A tier's result can no longer be hidden inside an average.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Re-measure (paid)</name>
  <files>data/evaluation/agency/</files>
  <read_first>backend/dev/agency_bench.py
docs/agent/agency-scoreboard.md
.planning/phases/27-agency-benchmark-under-real-models/27-agency-benchmark-under-real-models-03-SUMMARY.md</read_first>
  <behavior>
    - Same conditions as the phase 27 run wherever they are unchanged — 5 trials, same model,
      same pricing source — so the comparison is meaningful.
    - The frozen v1 tier is re-run alongside, and must reproduce the published 100%/100%. A
      divergence means something moved that should not have, and blocks publication until
      explained.
    - Spend is bounded by an explicit ceiling.
    - Raw output is archived before anything is written up.
  </behavior>
  <action>Confirm prices are current against the provider's published rates before spending —
model pricing changes independently of this repo, and a stale rate makes the cost column wrong
and the ceiling bind in the wrong place. Verify the model id still resolves. Run the bench with
`--policy fixture --policy model --model <model> --trials 5 --tier all` under a ceiling sized
from the phase 27 observed cost (that run was $0.26 for 13 cases; scale by the new case count
and add headroom). Archive the JSON under `data/evaluation/agency/` with the run date. Check
the v1 tier reproduces 13/13 for both policies; if it does not, stop and diagnose rather than
publish. Note the observed cost and p95 for the writeup.</action>
  <acceptance_criteria>A dated JSON result is archived under `data/evaluation/agency/`.
The v1 tier reproduces the published result for both policies, or the divergence is diagnosed and recorded.
Observed cost is at or under the stated ceiling.</acceptance_criteria>
  <verify>
    <manual>Confirm the run completed all requested trials (no `truncated` row) and that the v1 tier matches the published scoreboard before writing anything up.</manual>
  </verify>
  <done>The hardened suite has been measured under conditions comparable to the phase 27 run.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Publish, whatever it says</name>
  <files>docs/agent/agency-scoreboard.md
README.md</files>
  <read_first>docs/agent/agency-scoreboard.md
docs/agent/agency-evaluation.md
README.md</read_first>
  <behavior>
    - The result is reported as measured. Three outcomes are all publishable and each says
      something different:
      - **The hard tier discriminates** — the suite can now rank, and the phase succeeded.
      - **Both policies pass the hard tier** — the cases were not hard enough; report it and
        say what would be tried next.
      - **Both policies fail the hard tier** — the cases may be unfair or the tooling
        insufficient; that is a finding about the suite, not the models.
    - The phase 27 v1 measurement is preserved for comparison, not overwritten.
    - Unstable cases are reported explicitly; a hard case that flaps has not earned its place.
    - The README's claim matches the scoreboard, and every unrelated stated limit stays.
  </behavior>
  <action>Rewrite `docs/agent/agency-scoreboard.md` with the new measurement: per-tier table,
the v1 result retained as the comparison row with its date, per-property commentary on where
policies diverge on the hard tier, an explicit stability section, cost and latency, and a
reproduction block with the exact command, trial count, prompt versions, model snapshot, and
pricing source. If any hard case was unstable across trials, say so and mark it as not yet
counting toward the discrimination claim. Update the README's Status section so the agency
bullet reflects the measured outcome — promoting agency evaluation to Stable only if the hard
tier actually discriminates — and move or remove the "hardening `AGENCY_CASES`" in-progress item
accordingly. Leave every other stated limit untouched.</action>
  <acceptance_criteria>`docs/agent/agency-scoreboard.md` reports per-tier results.
`docs/agent/agency-scoreboard.md` retains the dated phase 27 v1 measurement for comparison.
`docs/agent/agency-scoreboard.md` contains a stability section.
`docs/agent/agency-scoreboard.md` contains a reproduction command with trial count and prompt versions.
`README.md` links the scoreboard and its agency claim matches the measured outcome.
`README.md` still contains the MCP rate limiting limitation.
`README.md` still contains the CD pipeline limitation.</acceptance_criteria>
  <verify>
    <manual>Read the scoreboard as someone who has not seen this work. If it reads as advocacy rather than measurement, rewrite it. Confirm no ranking claim is made that the numbers do not support.</manual>
  </verify>
  <done>The project publishes a measurement of reasoning quality that can distinguish between competent policies — or an honest account of why it still cannot.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/agentic tests/test_agency_bench.py -q --tb=short`.
Confirm `python3 -m agentic.evaluation` still runs offline and meets the committed floors.
Review the scoreboard against the archived JSON before merging.
</verification>

<success_criteria>
The scoreboard reports core and hard tiers separately from a real measurement, the frozen v1
result stays reproducible and comparable, and the README states what was actually found —
including, if that is what happened, that the hardened suite still does not discriminate.
</success_criteria>

<output>
After completion, create `.planning/phases/28-agency-suite-hardening/28-agency-suite-hardening-03-SUMMARY.md`
</output>
