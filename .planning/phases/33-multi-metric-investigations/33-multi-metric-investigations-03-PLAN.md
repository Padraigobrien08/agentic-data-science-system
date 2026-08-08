---
phase: 33-multi-metric-investigations
plan: 03
type: execute
wave: 3
depends_on: [01, 02]
files_modified:
  - agentic/evaluation/fixtures.py
  - agentic/evaluation/cases.py
  - agentic/evaluation/agency.py
  - agentic/evaluation/baselines/fixture_floors.json
  - tests/agentic/test_agency_tiers.py
  - docs/agent/agency-evaluation.md
  - docs/agent/agency-scoreboard.md
  - README.md
  - data/evaluation/agency/
autonomous: false
requirements:
  - MULTI-05
must_haves:
  truths:
    - "The two-part case that 32-02 had to drop as unwinnable is now winnable, and is in the hard tier."
    - "The hard tier defeats a second policy method, closing the gap phase 32 documented."
    - "The frozen core tier still reproduces its published result, or the divergence is diagnosed before anything is published."
    - "The scoreboard reports what was measured, including if the model does no better on multi-claim questions."
  artifacts:
    - path: agentic/evaluation/cases.py
      provides: "The multi-claim hard case, admitted under the existing contract"
    - path: docs/agent/agency-scoreboard.md
      provides: "The re-measurement, with prior results retained for comparison"
  key_links:
    - from: agentic/evaluation/cases.py
      to: agentic/agent/components.py
      via: "the case is winnable only because planning now serves each hypothesis its own metric"
      pattern: "CaseTier.hard|metric_refs"
---

<objective>
Close the loop: add the benchmark case that proved the limitation, now that the limitation is
gone, and re-measure.

Purpose: 32-02 dropped a `generate_hypotheses` case because no policy could pass it. That was
the evidence for this phase. Putting it back — and having it discriminate — is what shows the
phase actually changed something a user would feel.
Output: a winnable multi-claim hard case, a re-measurement, and honest publication.

**Not autonomous.** Task 3 spends money, and Task 4 requires judgement about a result that does
not exist yet.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/33-multi-metric-investigations/33-CONTEXT.md
@.planning/phases/33-multi-metric-investigations/33-VALIDATION.md
@.planning/phases/32-agency-suite-hardening/32-agency-suite-hardening-02-SUMMARY.md
@agentic/evaluation/cases.py
@agentic/evaluation/fixtures.py
@agentic/evaluation/agency.py
@tests/agentic/test_agency_tiers.py
@docs/agent/agency-evaluation.md
@docs/agent/agency-scoreboard.md
@backend/dev/agency_bench.py

<interfaces>
The probe from 32-02 that established the limitation — the second claim never leaves `proposed`:
```
hypotheses: [(['revenue_growth_pct'], 'supported'), (['margin_pct'], 'proposed')]
```

The hard tier's admission rule, enforced by `tests/agentic/test_agency_tiers.py`: a case must
fail `FixtureAgentPolicy` on a named `AgencyProperty`, and must stand on its own as a fair test.

Current published result — `suite_agency_v2`, prompts `1.0.1`, `gpt-5.4-mini-2026-03-17`,
5 trials: fixture core 100% / hard 0%, model core 100% / hard 75%, zero unstable cases, $0.35.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: The multi-claim fixture and case</name>
  <files>agentic/evaluation/fixtures.py
agentic/evaluation/cases.py
agentic/evaluation/agency.py</files>
  <read_first>agentic/evaluation/fixtures.py
agentic/evaluation/cases.py
agentic/evaluation/agency.py
.planning/phases/32-agency-suite-hardening/32-agency-suite-hardening-02-SUMMARY.md</read_first>
  <behavior>
    - Two metrics where the honest answers differ — one clause holds, the other does not — so a
      policy that investigates only the first reaches a confidently wrong overall answer.
    - The case is winnable: a policy that raises both claims resolves both. Verify this before
      adding it, exactly as the 32-02 cases were verified.
    - It fails `FixtureAgentPolicy`, satisfying the existing admission contract without the
      contract needing to change.
  </behavior>
  <action>Add a fixture with two semantically named metrics whose trajectories diverge — for
example `revenue_growth_pct` clearly slowing and `margin_pct` clearly stable — with the
deteriorating one ordered first so the single-claim fallback lands on it and produces a
plausible partial answer. Add a `tier=CaseTier.hard` case with a two-clause goal. Express the
expectation with existing `AgencyExpectations` fields if they suffice: `hypothesis_status_any`
including a refuted status is only reachable if the second claim was raised *and* investigated.
Add a new field only if nothing fits, and score it against an existing `AgencyProperty`. Before
committing the case, probe it against `FixtureAgentPolicy` and against a policy that raises both
claims, and confirm it fails the first and passes the second.</action>
  <acceptance_criteria>A two-metric divergent fixture is registered in `FIXTURES`.
`agentic/evaluation/cases.py` contains a `tier=CaseTier.hard` multi-clause case.
The case fails `FixtureAgentPolicy` (enforced by the existing contract test).
A probe confirms a two-claim policy passes it.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
    <manual>Confirm the case fails on a reasoning property, not because the second claim is still unreachable — read the failure detail and the hypothesis statuses.</manual>
  </verify>
  <done>The case that proved the limitation now measures its absence.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Re-baseline the tier and record what it now covers</name>
  <files>agentic/evaluation/baselines/fixture_floors.json
tests/agentic/test_agency_tiers.py
docs/agent/agency-evaluation.md</files>
  <read_first>agentic/evaluation/baselines/fixture_floors.json
tests/agentic/test_agency_tiers.py
docs/agent/agency-evaluation.md</read_first>
  <behavior>
    - `hard.cases` and `hard.max_pass_rate` reflect the enlarged tier.
    - Core floors are untouched — this plan adds a hard case and must not move the regression bar.
    - The doc's "what the tier does not cover" section is corrected: `generate_hypotheses` is now
      covered, and the reason it previously could not be is recorded as resolved rather than
      quietly deleted.
  </behavior>
  <action>Re-record the hard section of `fixture_floors.json` from observed behaviour over the
enlarged tier and update `recorded_on`. Confirm the core section is unchanged. Update the case
table and the "what the tier does not cover" section in `docs/agent/agency-evaluation.md`: the
`generate_hypotheses` exclusion is lifted and should say so, with a pointer to why it was
impossible before, while the `select_experiment` exclusion stands and its reasoning is unchanged.
If the tier now defeats two policy methods, say so — that was the bar phase 32 could not
reach.</action>
  <acceptance_criteria>`agentic/evaluation/baselines/fixture_floors.json` hard section reflects the new case count.
The core section is byte-identical to before.
`docs/agent/agency-evaluation.md` records `generate_hypotheses` as now covered and why it was not before.
`docs/agent/agency-evaluation.md` retains the `select_experiment` exclusion and its reasoning.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short && python3 -m agentic.evaluation</automated>
  </verify>
  <done>The tier's coverage claim matches what it actually covers.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Re-measure (paid)</name>
  <files>data/evaluation/agency/</files>
  <read_first>backend/dev/agency_bench.py
docs/agent/agency-scoreboard.md</read_first>
  <behavior>
    - Same conditions as the phase 32 run wherever unchanged — 5 trials, same model, same
      pricing source — so the comparison means something.
    - The frozen core tier is re-run as a control and must reproduce its published 100% for both
      policies. A divergence blocks publication until diagnosed.
    - Prices are re-checked against the provider before spending; a stale rate makes the cost
      column wrong and the ceiling bind in the wrong place.
    - Raw output is archived before anything is written up.
  </behavior>
  <action>Re-verify the model id resolves and that the configured prices still match the
provider's published rates. Run the bench with `--policy fixture --policy model --model
<model> --trials 5 --tier all` under a ceiling scaled from the phase 32 observed cost ($0.35 for
17 cases). Archive the JSON under `data/evaluation/agency/` with the run date. Check the core
tier reproduces 100% for both policies and that no row is `truncated`; if either fails, stop and
diagnose rather than publish. Note observed cost and p95, and note specifically whether the
model passes the new multi-claim case — that is the phase's headline.</action>
  <acceptance_criteria>A dated JSON result is archived under `data/evaluation/agency/`.
The core tier reproduces 100% for both policies, or the divergence is diagnosed and recorded.
No row is `truncated`.
Observed cost is at or under the stated ceiling.</acceptance_criteria>
  <verify>
    <manual>Confirm all requested trials completed and the core tier matches the published result before writing anything up.</manual>
  </verify>
  <done>The widened suite has been measured under conditions comparable to the previous run.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 4: Publish, whatever it says</name>
  <files>docs/agent/agency-scoreboard.md
README.md</files>
  <read_first>docs/agent/agency-scoreboard.md
docs/agent/agency-evaluation.md
README.md</read_first>
  <behavior>
    - Reported as measured. The model passing the new case, failing it, or flapping on it are all
      publishable and each says something different about multi-part reasoning.
    - Prior measurements are retained for comparison, not overwritten — the same discipline the
      v1 result got when v2 replaced it.
    - The README's single-metric limitation is removed only if it is actually gone, and the
      "widening the hard tier" in-progress item is updated to match.
    - Unstable cases are named; a flapping new case has not earned its place.
  </behavior>
  <action>Update `docs/agent/agency-scoreboard.md` with the new measurement, retaining the
phase 32 result below it as that one retained v1. Say explicitly whether the model handles a
multi-part question, since that is what this phase set out to make measurable. In `README.md`,
remove the single-metric bullet from Known limits — it is the constraint this phase lifted —
and update the "widening the agency hard tier" in-progress item to whatever is now true. Leave
every unrelated stated limit exactly as it is, including MCP rate limiting, no CD, and the
model's overclaiming on unanswerable questions unless the new run changed it.</action>
  <acceptance_criteria>`docs/agent/agency-scoreboard.md` reports the new per-tier result.
`docs/agent/agency-scoreboard.md` retains the phase 32 measurement for comparison.
`docs/agent/agency-scoreboard.md` states whether the model handles multi-part questions.
`README.md` no longer claims an investigation can examine only one metric.
`README.md` still contains the MCP rate limiting limitation.
`README.md` still contains the CD pipeline limitation.</acceptance_criteria>
  <verify>
    <manual>Read the scoreboard cold. If it reads as advocacy rather than measurement, rewrite it. Confirm no claim is made that the numbers do not support.</manual>
  </verify>
  <done>The project can say, with evidence, whether its agent handles a question with two parts.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest -q --tb=short`.
`tests/agentic/test_core_tier_equivalence.py` must still pass — the published core paths are
unchanged by this phase.
Review the scoreboard against the archived JSON before merging.
</verification>

<success_criteria>
The benchmark case that was impossible before this phase is in the hard tier, discriminating,
and the scoreboard reports what a real model does with a two-part question — with the core tier
still reproducing its published result.
</success_criteria>

<output>
After completion, create `.planning/phases/33-multi-metric-investigations/33-multi-metric-investigations-03-SUMMARY.md`
</output>
