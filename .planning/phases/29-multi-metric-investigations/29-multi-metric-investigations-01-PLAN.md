---
phase: 29-multi-metric-investigations
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - agentic/agent/components.py
  - tests/agentic/test_planner_parameterisation.py
  - tests/agentic/test_core_tier_equivalence.py
autonomous: true
requirements:
  - MULTI-01
  - MULTI-02
must_haves:
  truths:
    - "Experiments are parameterised from the metric of the hypothesis they target, not from one global interpretation hint."
    - "Candidate generation serves every open hypothesis, not only the first one that matches."
    - "A single-hypothesis investigation is byte-identical to before — same tools, same order, same ids, same conclusion — so the published scoreboard stays true."
    - "Ordering is deterministic and does not depend on set or dict iteration order."
  artifacts:
    - path: agentic/agent/components.py
      provides: "Per-hypothesis parameterisation and candidate generation in InvestigationPlanner"
    - path: tests/agentic/test_core_tier_equivalence.py
      provides: "Path-level proof that single-claim investigations did not change"
  key_links:
    - from: agentic/agent/components.py
      to: agentic/domain/hypothesis.py
      via: "the planner reads the target hypothesis's metric_refs instead of interpretation.metric_hint"
      pattern: "metric_refs|_params_for|_target_hypothesis"
    - from: tests/agentic/test_core_tier_equivalence.py
      to: docs/agent/agency-scoreboard.md
      via: "the frozen core tier's investigation paths are pinned so the published result stays reproducible"
      pattern: "SUITE_V1_CASES|observed_tools"
---

<objective>
Make the planner serve each hypothesis its own metric, without moving a single-claim
investigation.

Purpose: this is the whole mechanical change. Everything after it is semantics — what
sufficiency means with several claims, and what a mixed conclusion says. Doing it first, with
equivalence proved, means the rest of the phase builds on a known-unchanged base.
Output: per-hypothesis parameterisation, candidates across open hypotheses, and a path-level
equivalence test over the frozen core tier.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/29-multi-metric-investigations/29-CONTEXT.md
@.planning/phases/29-multi-metric-investigations/29-VALIDATION.md
@agentic/agent/components.py
@agentic/agent/loop.py
@agentic/agent/ids.py
@agentic/domain/hypothesis.py
@agentic/domain/investigation.py
@agentic/evaluation/cases.py
@tests/agentic/test_parallel_experiments.py

<interfaces>
The two methods that carry the constraint, from `agentic/agent/components.py`:
```python
def _params_for(self, tool, interpretation: GoalInterpretation, manifest) -> dict:
    metrics = manifest.metric_names()
    metric = interpretation.metric_hint or (metrics[0] if metrics else None)
    ...

def _target_hypothesis(self, state, metric: str | None) -> str | None:
    for h in state.open_hypotheses():
        if not h.metric_refs or (metric and metric in h.metric_refs):
            return h.id
    return state.hypotheses[0].id if state.hypotheses else None
```

Already per-hypothesis and needing no change:
```python
class Hypothesis(DomainModel):
    metric_refs: list[str]

# EvidenceUpdater.update
target = request.target_hypothesis_ids[0] if request.target_hypothesis_ids else None
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pin the current core-tier paths before changing anything</name>
  <files>tests/agentic/test_core_tier_equivalence.py</files>
  <read_first>agentic/evaluation/cases.py
agentic/evaluation/runner.py
docs/agent/agency-scoreboard.md</read_first>
  <behavior>
    - Every frozen core case's investigation is captured as a path, not just a verdict: the tool
      sequence, the termination reason, the disposition, and the confidence.
    - The captured expectation lives in the test as literal data, so a later change has to
      confront it rather than regenerate it.
    - Written and passing *before* the planner changes, so it is a genuine before/after.
  </behavior>
  <action>Create `tests/agentic/test_core_tier_equivalence.py`. Run every case in
`SUITE_V1_CASES` under `FixtureAgentPolicy` and record, per case, the ordered `observed_tools`,
`observed_termination`, `observed_disposition`, and `observed_confidence`. Embed the captured
values as a literal dict in the test file — not generated at runtime, or the test would compare
the new behaviour against itself and always pass. Assert each case matches. Document in the
module docstring that these paths back a published measurement
(`docs/agent/agency-scoreboard.md`), that a diff here means the scoreboard needs re-measuring
rather than the test needs updating, and that pass rate alone is insufficient — an investigation
can score the same while taking a different route.</action>
  <acceptance_criteria>`tests/agentic/test_core_tier_equivalence.py` exists.
The expected paths are literal data in the file, not computed from a live run.
The test covers all 13 frozen cases.
`python3 -m pytest tests/agentic/test_core_tier_equivalence.py -q --tb=short` passes on the unchanged planner.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic/test_core_tier_equivalence.py -q --tb=short</automated>
  </verify>
  <done>There is now a tripwire on the published result, armed before the change that could trip it.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Parameterise experiments from the target hypothesis</name>
  <files>agentic/agent/components.py
tests/agentic/test_planner_parameterisation.py</files>
  <read_first>agentic/agent/components.py
agentic/domain/hypothesis.py
agentic/experiments/tools/general_tools.py</read_first>
  <behavior>
    - A tool's parameters come from the metric of the hypothesis it targets; the interpretation
      hint is the fallback, and `metrics[0]` the fallback after that.
    - `fit_simple_regression` and `analyze_correlation` keep working — they are inherently
      multi-metric or parameterless and must not be forced through a single-metric path.
    - With one hypothesis the resolved metric is exactly what it was before.
  </behavior>
  <action>Change `_params_for` to take the target hypothesis (or its resolved metric) rather
than deriving the metric from `interpretation` alone, resolving in the order: the hypothesis's
first `metric_refs` entry, then `interpretation.metric_hint`, then `manifest.metric_names()[0]`.
Leave the per-tool parameter shapes untouched, including `fit_simple_regression`'s two-metric
form and the parameterless tools. Create `tests/agentic/test_planner_parameterisation.py`
asserting: a hypothesis with `metric_refs=["b"]` yields `value_column="b"` even when the
interpretation hint says `"a"`; a hypothesis with no `metric_refs` falls back to the hint; with
neither, `metrics[0]`; and `fit_simple_regression` still receives two distinct columns.</action>
  <acceptance_criteria>`agentic/agent/components.py` `_params_for` resolves the metric from the target hypothesis.
`tests/agentic/test_planner_parameterisation.py` exists.
`tests/agentic/test_planner_parameterisation.py` asserts the hypothesis metric wins over the interpretation hint.
`tests/agentic/test_planner_parameterisation.py` asserts `fit_simple_regression` still gets two columns.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
  </verify>
  <done>An experiment now measures the claim it was created to test.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Generate candidates across every open hypothesis</name>
  <files>agentic/agent/components.py
tests/agentic/test_planner_parameterisation.py</files>
  <read_first>agentic/agent/components.py
agentic/agent/loop.py
agentic/agent/ids.py
tests/agentic/test_parallel_experiments.py</read_first>
  <behavior>
    - Every open hypothesis contributes candidates, so a second claim is reachable at all.
    - Ordering is a pure function of hypothesis order and tool priority — never set or dict
      iteration order — so ids, batching, replay and diff stay deterministic.
    - Deduplication stays per (tool, hypothesis) rather than per tool, or the second claim
      would be starved by the first having used the same tool.
    - With one open hypothesis the candidate list is identical to before, in the same order.
  </behavior>
  <action>Split `_target_hypothesis`'s two jobs. Keep target *selection* for a given metric, and
change `candidates()` to iterate `state.open_hypotheses()` in list order, generating the intent
tools for each with that hypothesis as the target and its metric in the parameters. Track `seen`
as `(tool_name, hypothesis_id)` so the same tool can serve two different claims while still not
repeating for one. Preserve the existing falsification-candidate block ahead of the ranked ones,
and keep `expected_information_gain` computed from tool priority as it is now. Verify id
generation stays sequential and reproducible. Extend
`tests/agentic/test_planner_parameterisation.py` with: two open hypotheses over different
metrics both receive candidates; the candidate order is stable across repeated calls; one open
hypothesis produces the same list as before the change.</action>
  <acceptance_criteria>`agentic/agent/components.py` `candidates` iterates open hypotheses.
Deduplication is keyed by tool **and** hypothesis.
`tests/agentic/test_planner_parameterisation.py` asserts two hypotheses over different metrics both get candidates.
`tests/agentic/test_planner_parameterisation.py` asserts candidate ordering is stable across calls.
`python3 -m pytest tests/agentic -q --tb=short` passes.
`python3 -m pytest tests/agentic/test_core_tier_equivalence.py -q` still passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
    <manual>Re-run the 28-02 probe — two hypotheses over `revenue_growth_pct` and `margin_pct` — and confirm the second no longer ends at `proposed`.</manual>
  </verify>
  <done>A second claim can now be investigated; whether the loop stops before doing so is 29-02's problem.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/agentic -q --tb=short` after each task.
`tests/agentic/test_core_tier_equivalence.py` must pass unchanged throughout — a diff there means
the published scoreboard is now wrong and the phase must stop and decide, not adjust the test.
Confirm `python3 -m agentic.evaluation` still reports core 13/13.
</verification>

<success_criteria>
Experiments are parameterised per claim and every open hypothesis receives candidates, while a
single-hypothesis investigation follows exactly the path it followed before — proved on the
frozen core tier at the level of tools and ids, not just pass rate.
</success_criteria>

<output>
After completion, create `.planning/phases/29-multi-metric-investigations/29-multi-metric-investigations-01-SUMMARY.md`
</output>
