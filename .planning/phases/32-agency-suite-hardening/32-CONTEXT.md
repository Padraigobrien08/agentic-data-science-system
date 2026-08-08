# Phase 32: Agency Suite Hardening - Context

**Gathered:** 2026-08-07
**Status:** Completed

<domain>
## Phase Boundary

Phase 31 measured the agency suite against a real model and found it **saturated**:
`gpt-5.4-mini` and `FixtureAgentPolicy` — a keyword-matching rule engine — both score 100% on
all nine properties over five trials, with zero unstable cases. The suite separates broken
agents from working ones. It cannot rank competent ones.

This phase gives it headroom: cases where a competent reasoner succeeds and a rule engine does
not, so the scoreboard can say something a reader could act on.

It does not change the loop, the components, the experiment registry, the nine
`AgencyProperty` definitions, or the scoring in `score_case`. Those are sound — phase 31 proved
they catch real defects, including one worth 38 points. The gap is in the *cases*.

</domain>

<decisions>
## Implementation Decisions

### What earns a case its place
- **D-01:** A hard case must **fail `FixtureAgentPolicy`**. That is the operational definition
  of "discriminating", it is free and deterministic to check, and it makes the requirement
  CI-gateable without spending a cent. A proposed case the rule engine passes does not belong
  in the hard tier.
- **D-02:** Failing for the *right reason*. A case that fails the fixture policy because of a
  crash, a malformed request, or a capability gap in the tool registry is not measuring
  reasoning. Every hard case must be traceable to a named reasoning property and a specific
  heuristic it defeats.
- **D-03:** Not overfitting to one baseline. `FixtureAgentPolicy` is the yardstick of
  convenience, not the target. Each case must independently read as "a competent analyst
  would do X here" — if the only argument for a case is that it breaks the rule engine, it is
  a trick, not a test.

### Suite identity
- **D-04:** `suite_agency_v1` is **frozen** at its published 13 cases. `docs/agent/agency-scoreboard.md`
  reports a measurement against it; silently growing the suite would invalidate a published
  result and destroy comparability.
- **D-05:** Cases gain a `tier` (`core` | `hard`). `suite_agency_v2` is the full set; the v1
  subset stays independently runnable so the published number remains reproducible.

### The free gate
- **D-06:** The PR gate gains a **headroom check** alongside the existing floors: the fixture
  policy must stay *at or below* a ceiling on the hard tier. Floors catch regression; the
  ceiling catches the suite going soft. Both run offline and free.
- **D-07:** A rise in fixture performance on the hard tier is not automatically a failure to
  suppress — it may mean the deterministic policy genuinely improved. It must be a deliberate,
  reviewed re-baseline, never a silent drift.

### Vocabulary
- **D-08:** Hard cases may use **semantically meaningful column names** (`defects_per_release`,
  `churn_rate`). This does not weaken the existing input-agnosticism property: the
  `non_financial_*` cases prove the *loop* needs no domain vocabulary; the hard cases test
  whether the *policy* can use semantics when they are present. Different claims, both kept.

### the agent's Discretion
- Exact `tier` representation, as long as the v1 subset stays independently runnable
- Exact fixture shapes and column names, as long as they are deterministic
- Which of the candidate discriminators in `<specifics>` ship, as long as each satisfies D-01
  through D-03 and the set covers more than one policy method

</decisions>

<specifics>
## Specific Ideas

`FixtureAgentPolicy`'s heuristics are narrow in ways that are legitimate to probe, because each
corresponds to a real analytical judgement:

| Heuristic | Where | Attackable because |
|---|---|---|
| `metric_hint = next((m for m in metrics if m.lower() in text), metrics[0])` | `fixture_policy.py:49` | A goal that *implies* a metric without naming it falls through to `metrics[0]`. Order the capability list so the right metric is not first. |
| Intent from an ordered keyword table, first match wins, `trend` first | `fixture_policy.py:22-30` | "which region has the weakest **growth**?" is a ranking question, but `growth` is a trend keyword and trend is checked first. |
| Direction parsed from the goal text | `fixture_policy.py:46` | "has the **decline** in churn continued?" — falling churn is an improvement. A rule engine reads `down` and loses the semantics. |
| Selection: falsification, then max `expected_information_gain` | `fixture_policy.py:96-99` | A case where the highest-gain candidate does not answer the goal punishes blind gain-maximisation. |
| One hypothesis per goal | `fixture_policy.py:61-89` | A two-part goal ("is growth slowing **and** is margin quality deteriorating?") needs two claims. |
| Critique targets the max-confidence supported claim | `fixture_policy.py:106` | Two supported claims where the load-bearing one is not the most confident. |

Cover more than one policy method — a hard tier that only defeats `interpret_goal` measures one
decision and would be gamed by a better interpreter alone.

Watch for: a case that a model passes by *luck* rather than reasoning will show up as unstable
across trials. The 31-02 stability machinery already reports that; treat an unstable hard case
as not-yet-earning its place.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### What phase 31 established
- `docs/agent/agency-scoreboard.md` — the saturation finding this phase answers
- `.planning/phases/31-agency-benchmark-under-real-models/31-VERIFICATION.md` — what was verified
- `.planning/phases/31-agency-benchmark-under-real-models/31-agency-benchmark-under-real-models-03-SUMMARY.md`
  — the prompt defect the suite did catch, and the open items

### The instrument (unchanged this phase)
- `agentic/evaluation/agency.py` — nine properties, `score_case`, `AgencyExpectations`
- `agentic/evaluation/cases.py` — the 13 frozen v1 cases and their pairing rationale
- `agentic/evaluation/fixtures.py` — deterministic fixture construction; new fixtures go here
- `docs/agent/agency-evaluation.md` — the discrimination table and its current limits

### The baseline under test
- `agentic/agent/fixture_policy.py` — the heuristics in `<specifics>`; read it closely
- `agentic/agent/components.py` — `ExperimentSelector` candidate shape, `Critic` claim shape
- `agentic/experiments/tools/general_tools.py` — the tools a case can expect to exist

### Gates and reporting
- `agentic/evaluation/baselines/fixture_floors.json` — floors to restructure per tier
- `tests/agentic/test_agency_floors.py` — the PR gate to extend with the headroom check
- `tests/agentic/test_agency_suite.py` — the existing discrimination tests
- `agentic/evaluation/scoreboard.py` — aggregation; per-tier reporting lands here
- `backend/dev/agency_bench.py` — the harness that will re-measure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AgencyExpectations` already carries everything most hard cases need — `expect_any_tool`,
  `forbid_tools`, `hypothesis_status_any`, `max_confidence`, `require_challenge`. New
  expectation fields should be a last resort, not a first move.
- The stability machinery from 31-02 already flags a case whose verdict flaps across trials,
  which is exactly the signal for "this case discriminates by luck".
- `tests/agentic/test_agency_suite.py` already runs deliberately bad policies and asserts the
  suite catches them; the hard-tier requirement is the same pattern pointed the other way.

### Established Patterns
- Cases are declarative: a goal, a fixture, and an `AgencyExpectations`. No procedural setup.
- Cases are paired — every case punishing overclaiming has a counterpart punishing hedging.
  Hard cases should preserve this discipline rather than only adding difficulty.
- Structural hints (`time_field`, `entity_id_fields`, `metric_field`) are per-case; domain
  vocabulary is not assumed by the loop.
- Floors are recorded from observed behaviour, never chosen aspirationally.

### Integration Points
- `agentic/evaluation/cases.py` — `tier` field, new cases, `SUITE_V1_CASES` subset
- `agentic/evaluation/fixtures.py` — fixtures with multiple metrics and semantic names
- `agentic/evaluation/baselines/fixture_floors.json` — per-tier structure
- `tests/agentic/test_agency_floors.py` — headroom ceiling alongside the floors
- `agentic/evaluation/scoreboard.py` + `backend/dev/agency_bench.py` — per-tier reporting

### Known Risk
- Two of the four guards written in phase 31 were **vacuous on first write** and passed with
  the bug deliberately restored. Every new case and gate in this phase must be mutation-checked
  the same way: introduce the failure it claims to catch, confirm it fails, remove it. A case
  that cannot fail reads as coverage while measuring nothing.

</code_context>

<deferred>
## Deferred Ideas

- `ModelCall` persistence for agentic policy calls — carried from 31-01, independent of this work
- Cached-input pricing tier, so reported cost stops being a slight over-estimate
- Exercising `--max-cost-usd` truncation against a real ceiling
- Multi-model comparison across providers — worth doing *after* the suite can rank, not before
- Registering agency runs in the evaluation control-plane API

</deferred>

---

*Phase: 32-agency-suite-hardening*
*Context gathered: 2026-08-07*
