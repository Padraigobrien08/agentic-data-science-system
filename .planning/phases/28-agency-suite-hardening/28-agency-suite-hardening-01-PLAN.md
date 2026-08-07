---
phase: 28-agency-suite-hardening
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - agentic/evaluation/cases.py
  - agentic/evaluation/fixtures.py
  - agentic/evaluation/runner.py
  - agentic/evaluation/__init__.py
  - agentic/evaluation/baselines/fixture_floors.json
  - tests/agentic/test_agency_floors.py
  - tests/agentic/test_agency_tiers.py
autonomous: true
requirements:
  - HARD-01
  - HARD-02
must_haves:
  truths:
    - "`suite_agency_v1` is frozen at its published 13 cases and stays independently runnable, so the committed scoreboard remains reproducible."
    - "Cases carry a tier; the hard tier is defined by a property the CI can check for free: `FixtureAgentPolicy` must fail it."
    - "The PR gate checks headroom as well as regression — the fixture policy must stay at or below a ceiling on the hard tier."
    - "One proof-of-concept hard case exists and is mutation-checked, so the contract is demonstrated rather than asserted."
  artifacts:
    - path: agentic/evaluation/cases.py
      provides: "`tier` field, frozen `SUITE_V1_CASES`, and the first discriminating case"
    - path: tests/agentic/test_agency_tiers.py
      provides: "The discrimination contract: every hard case must defeat the rule engine"
    - path: agentic/evaluation/baselines/fixture_floors.json
      provides: "Per-tier baseline — floors on core, a headroom ceiling on hard"
  key_links:
    - from: tests/agentic/test_agency_tiers.py
      to: agentic/evaluation/cases.py
      via: "every case tagged hard is asserted to fail FixtureAgentPolicy"
      pattern: "tier|CaseTier|hard|FixtureAgentPolicy"
    - from: tests/agentic/test_agency_floors.py
      to: agentic/evaluation/baselines/fixture_floors.json
      via: "core floors and the hard-tier ceiling are both read from the committed baseline"
      pattern: "core|hard|ceiling"
---

<objective>
Establish the mechanism that makes hardening verifiable, and prove it with one case.

Purpose: "add harder cases" is not a specification — a case is only worth having if it
separates a competent reasoner from a rule engine, and that has to be checkable for free on
every PR. This plan builds that check before the cases arrive, so 28-02 has a bar to clear.
Output: tiering, a frozen v1 subset, the discrimination contract, a per-tier baseline, and one
demonstrated hard case.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/28-agency-suite-hardening/28-CONTEXT.md
@.planning/phases/28-agency-suite-hardening/28-VALIDATION.md
@docs/agent/agency-scoreboard.md
@agentic/evaluation/cases.py
@agentic/evaluation/agency.py
@agentic/evaluation/fixtures.py
@agentic/evaluation/runner.py
@agentic/agent/fixture_policy.py
@agentic/evaluation/baselines/fixture_floors.json
@tests/agentic/test_agency_floors.py
@tests/agentic/test_agency_suite.py

<interfaces>
From `agentic/evaluation/cases.py`:
```python
class AgencyCase(DomainModel):
    case_id: str
    description: str
    goal: str
    fixture_id: str
    expectations: AgencyExpectations
    time_field: str | None = "period"
    entity_id_fields: list[str] = ["entity"]
    metric_field: str = "value"
    max_experiments: int | None = None

AGENCY_CASES: tuple[AgencyCase, ...] = (...)  # 13 cases, published as suite_agency_v1
```

From `agentic/agent/fixture_policy.py` — the heuristic this plan's case defeats:
```python
metric_hint = next((m for m in metrics if m.lower() in text), metrics[0] if metrics else None)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Tier the cases and freeze suite_agency_v1</name>
  <files>agentic/evaluation/cases.py
agentic/evaluation/runner.py
agentic/evaluation/__init__.py</files>
  <read_first>agentic/evaluation/cases.py
agentic/evaluation/runner.py
docs/agent/agency-scoreboard.md</read_first>
  <behavior>
    - Every existing case is `core` and unchanged; the published v1 result stays reproducible.
    - `SUITE_V1_CASES` is exactly the 13 published cases and can be run on its own.
    - `AGENCY_CASES` becomes the full set under `suite_agency_v2`; the runner can be pointed at
      either, or at one tier.
    - Default `run_agency_suite()` behaviour is explicit about which suite it reports, so a
      number is never ambiguous about what produced it.
  </behavior>
  <action>Add `CaseTier(str, Enum)` with `core` and `hard` to `agentic/evaluation/cases.py`, and
a `tier: CaseTier = CaseTier.core` field on `AgencyCase`. Leave all 13 existing cases untouched
— they take the default. Define `SUITE_V1_ID = "suite_agency_v1"` and
`SUITE_V1_CASES: tuple[AgencyCase, ...]` as exactly those 13, plus `SUITE_ID = "suite_agency_v2"`
for the full set. Add `cases_for_tier(tier)` returning the subset. In
`agentic/evaluation/runner.py` add a `tier: CaseTier | None = None` filter to
`run_agency_suite` that narrows `cases` before running, leaving every other default intact.
Export the new names from `agentic/evaluation/__init__.py`. Add a test asserting
`len(SUITE_V1_CASES) == 13` and that every id in it matches the ids named in
`docs/agent/agency-scoreboard.md`'s reproduction section, so the frozen subset cannot drift
from the published artifact.</action>
  <acceptance_criteria>`agentic/evaluation/cases.py` contains `class CaseTier`.
`agentic/evaluation/cases.py` contains `SUITE_V1_CASES`.
`agentic/evaluation/cases.py` contains `SUITE_V1_ID`.
`agentic/evaluation/cases.py` contains `def cases_for_tier`.
`agentic/evaluation/runner.py` contains `tier`.
`agentic/evaluation/__init__.py` contains `CaseTier`.
`python3 -m pytest tests/agentic -q --tb=short` passes.
`python3 -m agentic.evaluation` exits 0.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short && python3 -m agentic.evaluation</automated>
  </verify>
  <done>The published suite is frozen and the shape for a harder tier exists.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: The discrimination contract, proved with one case</name>
  <files>agentic/evaluation/fixtures.py
agentic/evaluation/cases.py
tests/agentic/test_agency_tiers.py</files>
  <read_first>agentic/agent/fixture_policy.py
agentic/evaluation/fixtures.py
agentic/evaluation/agency.py
agentic/experiments/tools/general_tools.py</read_first>
  <behavior>
    - A hard case fails `FixtureAgentPolicy` — that is what makes it discriminating, and it is
      checkable offline and free.
    - It fails for a *reasoning* reason: a named property, on a specific heuristic, not a crash
      or a missing capability.
    - The contract is enforced for every hard case, so 28-02 cannot add a case that quietly
      fails to discriminate.
  </behavior>
  <action>Add a fixture to `agentic/evaluation/fixtures.py` carrying **several** metrics with
semantic names where the one the goal implies is deliberately **not first** in column order —
for example a support dataset with `tickets_opened`, `tickets_closed`, and `median_resolution_hours`,
over a `week` time field. Add one `tier=CaseTier.hard` case whose goal implies a metric without
naming it (e.g. "are we getting slower at resolving customer issues?"), so
`FixtureAgentPolicy`'s `metrics[0]` fallback selects the wrong metric while a reasoner selects
`median_resolution_hours`. Express the expectation through existing `AgencyExpectations` fields
— `expect_any_tool` / `forbid_tools` / `hypothesis_status_any` — and add a new field only if
none fit. Create `tests/agentic/test_agency_tiers.py` asserting: every `hard` case fails
`FixtureAgentPolicy`, with the failing case ids and their failed properties in the message;
every hard case's failures name at least one `AgencyProperty` (not an empty outcome list, which
would mean nothing was asserted); and the hard tier is non-empty. Mutation-check the case:
confirm it passes when the policy is given the right metric hint, so the failure is attributable
to metric selection rather than to the fixture being unanalysable.</action>
  <acceptance_criteria>`agentic/evaluation/fixtures.py` contains the new multi-metric fixture.
`agentic/evaluation/cases.py` contains `CaseTier.hard`.
`tests/agentic/test_agency_tiers.py` exists.
`tests/agentic/test_agency_tiers.py` contains `FixtureAgentPolicy`.
`tests/agentic/test_agency_tiers.py` asserts the hard tier is non-empty.
`tests/agentic/test_agency_tiers.py` asserts every hard case fails the fixture policy.
`python3 -m pytest tests/agentic/test_agency_tiers.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic/test_agency_tiers.py -q --tb=short</automated>
    <manual>Confirm the case fails on metric selection, not on a crash, a malformed request, or a tool capability gap — read the failed property detail, not just the verdict.</manual>
  </verify>
  <done>"Discriminating" is now a property the build checks, not a claim in a document.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Per-tier baseline with a headroom ceiling</name>
  <files>agentic/evaluation/baselines/fixture_floors.json
tests/agentic/test_agency_floors.py</files>
  <read_first>agentic/evaluation/baselines/fixture_floors.json
tests/agentic/test_agency_floors.py
agentic/evaluation/agency.py</read_first>
  <behavior>
    - Core-tier floors are unchanged in meaning: the fixture policy must not regress.
    - The hard tier gets a **ceiling**: the fixture policy must stay at or below it. Floors
      catch the agent getting worse; the ceiling catches the suite getting easier.
    - A breach of the ceiling fails with a message that names both readings — the deterministic
      policy improved, or the cases went soft — because the fix differs.
    - Both checks stay offline and free, so they gate every PR.
  </behavior>
  <action>Restructure `fixture_floors.json` into per-tier sections: `core` keeping the existing
per-property floors and `pass_rate`, and `hard` carrying `max_pass_rate` recorded from the
observed fixture behaviour on the hard tier. Keep `recorded_on` and extend `note` to explain the
ceiling's purpose. Update `tests/agentic/test_agency_floors.py` so the existing floor tests read
the `core` section and run against `tier=CaseTier.core`, and add a headroom test asserting the
fixture policy's hard-tier pass rate is at or below `max_pass_rate`, with an assertion message
stating both possible causes and that a re-baseline must be deliberate. Keep the existing
coverage tests — every `AgencyProperty` floored, every floor exercised — and scope them to the
core tier so they remain meaningful.</action>
  <acceptance_criteria>`agentic/evaluation/baselines/fixture_floors.json` contains `"core"`.
`agentic/evaluation/baselines/fixture_floors.json` contains `"hard"`.
`agentic/evaluation/baselines/fixture_floors.json` contains `max_pass_rate`.
`tests/agentic/test_agency_floors.py` contains `max_pass_rate`.
`tests/agentic/test_agency_floors.py` asserts a hard-tier ceiling.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
    <manual>Mutation-check the ceiling: make the hard case trivially passable, confirm the headroom test fails, then revert.</manual>
  </verify>
  <done>The free gate now protects headroom as well as behaviour, so the suite cannot silently go soft.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/agentic -q --tb=short` after each task.
Confirm `python3 -m agentic.evaluation` still runs offline and reports which suite it measured.
Confirm the v1 subset still scores 13/13 for the fixture policy, so the published scoreboard
stays reproducible.
</verification>

<success_criteria>
The suite has a tier whose defining property — a rule engine cannot pass it — is enforced by a
free offline test, the published v1 result remains reproducible, and the PR gate now fails both
when the agent regresses and when the cases go soft.
</success_criteria>

<output>
After completion, create `.planning/phases/28-agency-suite-hardening/28-agency-suite-hardening-01-SUMMARY.md`
</output>
