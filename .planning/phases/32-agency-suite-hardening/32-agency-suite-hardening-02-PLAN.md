---
phase: 32-agency-suite-hardening
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - agentic/evaluation/fixtures.py
  - agentic/evaluation/cases.py
  - agentic/evaluation/agency.py
  - agentic/evaluation/baselines/fixture_floors.json
  - tests/agentic/test_agency_tiers.py
  - docs/agent/agency-evaluation.md
autonomous: true
requirements:
  - HARD-03
must_haves:
  truths:
    - "The hard tier defeats more than one policy method, so it cannot be cleared by improving a single decision."
    - "Every hard case fails `FixtureAgentPolicy` on a named reasoning property, not on a crash or a capability gap."
    - "The hard tier preserves the suite's pairing discipline: difficulty is not added only in the overclaiming direction."
    - "Each hard case is mutation-checked — the reasoning it rewards is shown to be what makes it pass."
  artifacts:
    - path: agentic/evaluation/cases.py
      provides: "The discriminating case set, each tagged with the heuristic it defeats"
    - path: agentic/evaluation/fixtures.py
      provides: "Deterministic fixtures with multiple metrics and semantic column names"
    - path: docs/agent/agency-evaluation.md
      provides: "What the hard tier measures and why each case is there"
  key_links:
    - from: agentic/evaluation/cases.py
      to: agentic/agent/fixture_policy.py
      via: "each hard case's description names the analytical judgement it requires"
      pattern: "CaseTier.hard|description="
    - from: docs/agent/agency-evaluation.md
      to: agentic/evaluation/cases.py
      via: "the doc explains the hard tier's admission rule and lists what each case probes"
      pattern: "hard tier|discriminat"
---

<objective>
Fill out the hard tier so it measures reasoning across the policy surface, not one decision.

Purpose: 32-01 proves one case can discriminate. A tier of one is a trick; a tier that only
defeats `interpret_goal` is cleared by a better interpreter alone. This plan builds a set that
a policy has to be broadly competent to pass.
Output: fixtures, cases covering at least four distinct judgements, and the doc that explains
why each is there.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/32-agency-suite-hardening/32-CONTEXT.md
@.planning/phases/32-agency-suite-hardening/32-VALIDATION.md
@.planning/phases/32-agency-suite-hardening/32-agency-suite-hardening-01-PLAN.md
@agentic/evaluation/cases.py
@agentic/evaluation/fixtures.py
@agentic/evaluation/agency.py
@agentic/agent/fixture_policy.py
@agentic/agent/components.py
@agentic/experiments/tools/general_tools.py
@docs/agent/agency-evaluation.md

<interfaces>
Candidate discriminators, each with the heuristic it defeats (from 32-CONTEXT `<specifics>`):

| Policy method | Fixture heuristic | Case shape |
|---|---|---|
| `interpret_goal` (metric) | `metrics[0]` fallback | goal implies a metric it does not name |
| `interpret_goal` (intent) | ordered keyword table, `trend` first | "which region has the weakest **growth**?" is ranking, not trend |
| `interpret_goal` (direction) | `parse_direction` on raw text | "has the **decline** in churn continued?" — falling churn is good |
| `select_experiment` | max `expected_information_gain` | highest-gain candidate does not answer the goal |
| `generate_hypotheses` | one hypothesis per goal | two-part goal needs two claims |
| `critique` | targets max-confidence claim | load-bearing claim is not the most confident |
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fixtures for the discriminating cases</name>
  <files>agentic/evaluation/fixtures.py</files>
  <read_first>agentic/evaluation/fixtures.py
agentic/evaluation/cases.py
agentic/experiments/tools/general_tools.py</read_first>
  <behavior>
    - Deterministic: fixed formulas or a seeded RNG, never wall-clock or unseeded randomness.
    - Multiple metrics with semantic names, ordered so the goal-relevant one is not first.
    - Rich enough that the tools can actually analyse them — a case must be able to *succeed*,
      or it measures a capability gap rather than reasoning.
    - Include at least one where the honest answer is "the data does not support this", so the
      hard tier punishes overclaiming as well as under-reasoning.
  </behavior>
  <action>Add fixtures to `agentic/evaluation/fixtures.py` supporting the discriminators chosen
from the table above. Each needs enough periods for the trend and change-point tools to run
(the existing fixtures use 10-16), and where a case tests group comparison or ranking, several
entities with a genuine separation. Register each in `FIXTURES`. For every fixture, verify by
running the relevant tool directly that it produces the signal the case will assert — a case
built on a fixture whose signal is not actually present tests nothing. Add a test asserting
every registered fixture is deterministic across repeated builds, matching the guarantee the
suite's offline claim rests on.</action>
  <acceptance_criteria>`agentic/evaluation/fixtures.py` registers the new fixtures in `FIXTURES`.
Each new fixture has at least 10 rows per entity.
A determinism test over every registered fixture exists and passes.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
    <manual>For each new fixture, run the tool the case depends on and confirm the signal is present and of the expected direction/magnitude.</manual>
  </verify>
  <done>The hard cases have data that can actually distinguish good reasoning from bad.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: The discriminating case set</name>
  <files>agentic/evaluation/cases.py
agentic/evaluation/agency.py
tests/agentic/test_agency_tiers.py</files>
  <read_first>agentic/evaluation/cases.py
agentic/evaluation/agency.py
agentic/agent/fixture_policy.py
tests/agentic/test_agency_tiers.py</read_first>
  <behavior>
    - At least four hard cases, defeating at least three *different* policy methods.
    - Each fails `FixtureAgentPolicy` on a named property — the 32-01 contract enforces this.
    - Pairing is preserved: the tier includes a case where the correct behaviour is to decline,
      so a policy cannot clear the tier by being uniformly more assertive.
    - Existing `AgencyExpectations` fields are used wherever they fit; a new field is justified
      in its docstring by what no existing field could express.
  </behavior>
  <action>Add the hard cases, each with a `description` naming the analytical judgement it
requires — written so a reader can agree it is a fair test without knowing `FixtureAgentPolicy`
exists. Cover at least: metric selection under an implied metric; intent selection where a
trend keyword appears in a non-trend question; selection where the highest-information-gain
candidate does not answer the goal; and one where the evidence genuinely cannot support the
goal's premise and declining is correct. If an expectation cannot be expressed with existing
fields, add one to `AgencyExpectations` with a docstring stating what it asserts and why the
existing fields do not cover it, and score it in `score_case` against an existing
`AgencyProperty` — prefer reusing a property over inventing one. Extend
`tests/agentic/test_agency_tiers.py` with an assertion that the hard tier's failures span more
than one policy decision, so the tier cannot be cleared by fixing a single method. Mutation-check
each case: construct a policy that makes the specific right judgement and confirm the case
passes, so the case is shown to reward the reasoning it claims to.</action>
  <acceptance_criteria>`agentic/evaluation/cases.py` contains at least 4 cases with `tier=CaseTier.hard`.
At least one hard case expects a declining/insufficient outcome.
`tests/agentic/test_agency_tiers.py` asserts hard-tier failures span more than one policy decision.
Every hard case fails `FixtureAgentPolicy` (enforced by the 32-01 contract test).
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
    <manual>Read each case's description cold. If the argument for it is "it breaks the rule engine" rather than "a competent analyst would do this", cut it.</manual>
  </verify>
  <done>The hard tier measures broad competence rather than one decision.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Re-baseline and document the tier</name>
  <files>agentic/evaluation/baselines/fixture_floors.json
docs/agent/agency-evaluation.md</files>
  <read_first>agentic/evaluation/baselines/fixture_floors.json
docs/agent/agency-evaluation.md
docs/agent/agency-scoreboard.md</read_first>
  <behavior>
    - The hard-tier ceiling is re-recorded from observed fixture behaviour over the full set.
    - Core floors are untouched — this plan adds cases, it must not move the regression bar.
    - The doc explains the tier's admission rule, so a future contributor knows what makes a
      case eligible rather than guessing.
  </behavior>
  <action>Re-record `hard.max_pass_rate` in `fixture_floors.json` from the fixture policy's
observed pass rate over the complete hard tier, and update `recorded_on`. Confirm the core
section is unchanged. In `docs/agent/agency-evaluation.md`, add a section covering: the
admission rule (a hard case must fail `FixtureAgentPolicy`, on a named reasoning property, and
must stand on its own as a fair test); a table of the hard cases with the judgement each
requires; and the headroom ceiling and what a breach means in each direction. Update the
existing discrimination table with the fixture policy's measured hard-tier result, and state
plainly that the model comparison is not yet re-run — 32-03 does that.</action>
  <acceptance_criteria>`agentic/evaluation/baselines/fixture_floors.json` `hard.max_pass_rate` reflects observed behaviour.
`agentic/evaluation/baselines/fixture_floors.json` `core` section is unchanged.
`docs/agent/agency-evaluation.md` contains the hard-tier admission rule.
`docs/agent/agency-evaluation.md` lists each hard case and the judgement it requires.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short && python3 -m agentic.evaluation</automated>
  </verify>
  <done>The tier is baselined and its admission rule is written down rather than tacit.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/agentic -q --tb=short` after each task.
Confirm the v1 subset still scores 13/13 for the fixture policy.
Confirm `python3 -m agentic.evaluation` runs offline with no provider.
</verification>

<success_criteria>
The hard tier contains a set of cases that `FixtureAgentPolicy` cannot pass, spanning several
policy decisions and both failure directions, each defensible as a fair test on its own terms,
with the admission rule documented and the baseline re-recorded.
</success_criteria>

<output>
After completion, create `.planning/phases/32-agency-suite-hardening/32-agency-suite-hardening-02-SUMMARY.md`
</output>
