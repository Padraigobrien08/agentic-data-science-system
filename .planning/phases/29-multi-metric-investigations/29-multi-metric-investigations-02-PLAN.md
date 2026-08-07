---
phase: 29-multi-metric-investigations
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - agentic/agent/components.py
  - agentic/agent/budget.py
  - agentic/domain/enums.py
  - tests/agentic/test_multi_hypothesis_termination.py
  - tests/agentic/test_core_tier_equivalence.py
  - docs/agent/termination-policy.md
  - docs/agent/investigation-loop.md
autonomous: true
requirements:
  - MULTI-03
  - MULTI-04
must_haves:
  truths:
    - "Sufficiency means every hypothesis reached a terminal status, not that one did — otherwise 29-01's fix strands claims in a new place."
    - "A run with one supported and one refuted claim does not report as simply supported."
    - "The experiment budget accommodates a realistic multi-claim investigation, or the loop says so with a typed reason rather than truncating silently."
    - "Single-claim behaviour, including the frozen core tier's paths, is still unchanged."
  artifacts:
    - path: agentic/agent/components.py
      provides: "Termination across several claims and a mixed conclusion disposition"
    - path: tests/agentic/test_multi_hypothesis_termination.py
      provides: "The semantics, pinned: when a multi-claim run stops and what it concludes"
  key_links:
    - from: agentic/agent/components.py
      to: agentic/domain/investigation.py
      via: "termination consults every open hypothesis rather than the first supported one"
      pattern: "open_hypotheses|sufficient_evidence"
---

<objective>
Decide what "done" and "concluded" mean when an investigation holds several claims.

Purpose: 29-01 makes a second claim reachable. Without this plan the loop still stops the moment
the first claim is supported, so the second is stranded one step later than before — the same
bug wearing a different hat.
Output: termination across claims, a mixed disposition, a budget that fits, and the docs that
describe them.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/29-multi-metric-investigations/29-CONTEXT.md
@.planning/phases/29-multi-metric-investigations/29-VALIDATION.md
@.planning/phases/29-multi-metric-investigations/29-multi-metric-investigations-01-PLAN.md
@agentic/agent/components.py
@agentic/agent/budget.py
@agentic/domain/enums.py
@agentic/domain/conclusion.py
@docs/agent/termination-policy.md

<interfaces>
The sufficiency branch, from `TerminationPolicy.decide`:
```python
supported = [h for h in state.hypotheses
             if h.status is HypothesisStatus.supported and h.confidence >= self.SUFFICIENT_CONFIDENCE]
if supported:
    h = supported[0]
    crits = [c for c in state.critiques if c.target.id == h.id]
    unused = [t for t in intent_tools if t not in executed_tools]
    tested = any((c.suggested_action or "") in executed_tools for c in crits)
    if tested or not unused:
        return True, TerminationReason.sufficient_evidence
```

The disposition branch, from `ConclusionSynthesizer.synthesize`:
```python
if supported:
    disposition = ConclusionDisposition.supported   # one refuted claim vanishes from the headline
elif rejected and not weakened:
    disposition = ConclusionDisposition.refuted
elif weakened:
    disposition = ConclusionDisposition.inconclusive
else:
    disposition = ConclusionDisposition.insufficient_evidence
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Sufficiency across every claim</name>
  <files>agentic/agent/components.py
tests/agentic/test_multi_hypothesis_termination.py</files>
  <read_first>agentic/agent/components.py
agentic/domain/investigation.py
docs/agent/termination-policy.md</read_first>
  <behavior>
    - `sufficient_evidence` requires every hypothesis to have reached a terminal status, with the
      existing challenge requirement still applying to supported ones.
    - An investigation with one claim behaves exactly as it does today — one claim resolved *is*
      every claim resolved.
    - Budget, safety, repeated-failure and user-stop checks keep their current precedence; this
      changes only what counts as sufficiency.
    - A run that resolves one claim and exhausts its candidates for another still terminates,
      with the reason the evidence warrants rather than by hanging.
  </behavior>
  <action>Change the sufficiency branch in `TerminationPolicy.decide` so it fires only when
`state.open_hypotheses()` is empty — every hypothesis terminal — and every supported hypothesis
has been challenged or has no unused falsification tool left. Keep the check order (user stop →
safety → repeated failure → budget → sufficiency) unchanged. Confirm
`finalize_no_candidates` still resolves the case where the selector runs dry with claims
outstanding, and that such a run reports `insufficient_evidence` rather than looping. Create
`tests/agentic/test_multi_hypothesis_termination.py` covering: two claims where only the first
is supported does **not** terminate as sufficient; both resolved does; one claim behaves as
before; and a run with an unresolvable second claim still reaches a typed terminal state.</action>
  <acceptance_criteria>`agentic/agent/components.py` sufficiency consults `open_hypotheses()`.
`tests/agentic/test_multi_hypothesis_termination.py` exists.
It asserts a partially-resolved multi-claim run is not sufficient.
It asserts a single-claim run is unchanged.
It asserts an unresolvable second claim still terminates with a typed reason.
`python3 -m pytest tests/agentic -q --tb=short` passes.
`python3 -m pytest tests/agentic/test_core_tier_equivalence.py -q` still passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
  </verify>
  <done>The loop no longer declares victory with a claim still outstanding.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: A conclusion that does not round to the good news</name>
  <files>agentic/agent/components.py
agentic/domain/enums.py
tests/agentic/test_multi_hypothesis_termination.py</files>
  <read_first>agentic/agent/components.py
agentic/domain/enums.py
agentic/domain/conclusion.py
agentic/evaluation/agency.py</read_first>
  <behavior>
    - One supported and one refuted claim reports as **mixed**, not supported. Reporting it as
      supported hides a refutation the user asked about, which is the overclaiming failure the
      agency suite exists to punish.
    - Confidence for a mixed outcome reflects the split rather than the supported claims alone.
    - The statement names both sides, so the headline carries the disagreement.
    - All-supported, all-refuted and all-unresolved outcomes keep their current dispositions
      and confidences exactly.
  </behavior>
  <action>Add a `mixed` value to `ConclusionDisposition` in `agentic/domain/enums.py`. In
`ConclusionSynthesizer.synthesize`, branch to it when there is at least one supported hypothesis
**and** at least one rejected or weakened one, before the existing `if supported` branch. Build
the statement from both groups, set a confidence below the all-supported case, and carry every
group's ids in `hypothesis_ids`. Leave the single-group branches untouched. Check whether
`agentic/evaluation/agency.py`'s `disposition_in` expectations or any frontend/API consumer
enumerates dispositions, and update those that do. Extend the tests to cover: mixed is reported
for a split outcome; all-supported is unchanged; all-refuted is unchanged; the mixed statement
mentions both a supported and a refuted claim.</action>
  <acceptance_criteria>`agentic/domain/enums.py` contains a `mixed` disposition.
`agentic/agent/components.py` branches to it before the `supported` branch.
Tests assert all-supported and all-refuted dispositions and confidences are unchanged.
Tests assert a split outcome reports mixed and names both sides.
`python3 -m pytest -q` passes (including backend consumers of the enum).</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest -q --tb=short</automated>
    <manual>Grep for consumers that switch on disposition — API schemas, frontend parsing — and confirm a new value degrades gracefully rather than falling through to an unhandled branch.</manual>
  </verify>
  <done>A run that found one thing true and one thing false says so.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: A budget sized for the new shape, and the docs</name>
  <files>agentic/agent/budget.py
docs/agent/termination-policy.md
docs/agent/investigation-loop.md
tests/agentic/test_multi_hypothesis_termination.py</files>
  <read_first>agentic/agent/budget.py
docs/agent/termination-policy.md
docs/agent/investigation-loop.md
agentic/evaluation/cases.py</read_first>
  <behavior>
    - A realistic two-claim investigation completes within the default budget instead of
      truncating into `budget_exhausted`.
    - Whatever the default becomes, the frozen core tier's paths are unaffected — single-claim
      runs use the same number of experiments they always did.
    - The docs describe sufficiency-across-claims, the mixed disposition, and how experiments
      scale with claim count, so the next reader does not have to derive it.
  </behavior>
  <action>Measure how many experiments a two-claim investigation actually needs, then decide
whether `LoopBudget.max_experiments` (currently 8) is raised or left with the shortfall reported
as `budget_exhausted`. Prefer whichever keeps a two-claim run completing by default, and state
the reasoning in the field's description. Verify the change cannot alter the core tier — a
higher cap only matters to runs that would have hit it. Add a test that a two-claim
investigation completes under the default budget without `budget_exhausted`. Update
`docs/agent/termination-policy.md`: sufficiency now requires every hypothesis terminal, the
budget table reflects any new default, and the "sufficiency requires challenge" section states
that the challenge requirement applies per supported claim. Update
`docs/agent/investigation-loop.md` to describe multi-claim planning — one target per candidate,
candidates across open hypotheses — and the mixed disposition.</action>
  <acceptance_criteria>`agentic/agent/budget.py` `max_experiments` description explains the multi-claim consideration.
A test asserts a two-claim run completes without `budget_exhausted` under defaults.
`docs/agent/termination-policy.md` states sufficiency requires every hypothesis terminal.
`docs/agent/termination-policy.md` budget table matches the code.
`docs/agent/investigation-loop.md` describes multi-claim planning and the mixed disposition.
`python3 -m pytest tests/agentic -q --tb=short` passes.
`python3 -m pytest tests/agentic/test_core_tier_equivalence.py -q` still passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short && python3 -m agentic.evaluation</automated>
  </verify>
  <done>Multi-claim investigations finish, and the behaviour is written down rather than inferred.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest -q --tb=short` after each task — Task 2 touches an enum with consumers
outside `agentic/`.
`tests/agentic/test_core_tier_equivalence.py` must pass unchanged throughout.
Confirm `python3 -m agentic.evaluation` still reports core 13/13.
</verification>

<success_criteria>
A multi-claim investigation runs to completion, terminates only when every claim is resolved or
a typed bound stops it, and reports a mixed outcome as mixed — while single-claim behaviour and
the published core-tier paths are unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/29-multi-metric-investigations/29-multi-metric-investigations-02-SUMMARY.md`
</output>
