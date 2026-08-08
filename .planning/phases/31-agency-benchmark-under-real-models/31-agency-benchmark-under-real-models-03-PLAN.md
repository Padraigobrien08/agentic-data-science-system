---
phase: 31-agency-benchmark-under-real-models
plan: 03
type: execute
wave: 3
depends_on: [01, 02]
files_modified:
  - agentic/evaluation/baselines/fixture_floors.json
  - tests/agentic/test_agency_floors.py
  - docs/agent/agency-scoreboard.md
  - docs/agent/agency-evaluation.md
  - .github/workflows/agency-bench.yml
  - README.md
autonomous: false
requirements:
  - AGCY-04
  - AGCY-05
must_haves:
  truths:
    - "A committed scoreboard reports each measured policy's agency score, stability, cost, and latency."
    - "The README no longer claims the measurement has not been run."
    - "A prompt or policy change that degrades a per-property score below its committed floor fails CI."
    - "The floor gate rides the existing free offline suite; the model suite never runs per-PR."
  artifacts:
    - path: docs/agent/agency-scoreboard.md
      provides: "The published measurement: policies scored on suite_agency_v1 with cost and variance"
    - path: agentic/evaluation/baselines/fixture_floors.json
      provides: "Committed per-property regression floors for the deterministic baseline"
    - path: tests/agentic/test_agency_floors.py
      provides: "The CI gate that makes a prompt regression a build failure"
    - path: .github/workflows/agency-bench.yml
      provides: "On-demand model benchmark, never triggered by a pull request"
  key_links:
    - from: tests/agentic/test_agency_floors.py
      to: agentic/evaluation/baselines/fixture_floors.json
      via: "the offline suite's per-property scores are asserted against committed floors"
      pattern: "fixture_floors|property_scores"
    - from: README.md
      to: docs/agent/agency-scoreboard.md
      via: "the status section links the measurement instead of disclaiming its absence"
      pattern: "agency-scoreboard"
---

<objective>
Publish the measurement and make it defended by CI.

Purpose: this is the deliverable the phase exists for. It converts the project's strongest asset —
a deterministic reasoning benchmark — from internal machinery into the headline claim, and stops
the result from silently rotting.
Output: committed floors, a gate test, the scoreboard document, an on-demand workflow, and an
honest README.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/31-agency-benchmark-under-real-models/31-CONTEXT.md
@.planning/phases/31-agency-benchmark-under-real-models/31-VALIDATION.md
@.planning/phases/31-agency-benchmark-under-real-models/31-agency-benchmark-under-real-models-02-PLAN.md
@agentic/evaluation/agency.py
@agentic/evaluation/scoreboard.py
@backend/dev/agency_bench.py
@docs/agent/agency-evaluation.md
@docs/observability.md
@README.md
@.github/workflows/ci.yml

<interfaces>
From `agentic/evaluation/agency.py`:
```python
class AgencyProperty(str, Enum):
    terminates_for_the_right_reason
    reaches_the_right_disposition
    revises_under_contradiction
    preserves_contradicting_evidence
    path_adapts_to_goal
    avoids_redundant_experiments
    respects_budget
    calibrated_confidence
```

From `README.md` (the claim this plan retires):
```
- The loop's reasoning is verified against a **deterministic fixture policy**, not a live
  model. `suite_agency_v1` accepts any `AgentPolicy` precisely so a real model can be held
  to the same bar — that measurement has not been run.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Commit per-property floors and the gate that enforces them</name>
  <files>agentic/evaluation/baselines/fixture_floors.json
tests/agentic/test_agency_floors.py</files>
  <read_first>agentic/evaluation/agency.py
agentic/evaluation/runner.py
tests/agentic/test_agency_suite.py</read_first>
  <behavior>
    - The offline fixture suite's per-property scores are asserted against committed floors on
      every PR, at no cost and with no network.
    - A failure names the property, the floor, and the observed score, so the regression is
      diagnosable from the CI log alone.
    - Floors are recorded from the actual current baseline, not aspirational round numbers.
  </behavior>
  <action>Run `python3 -m agentic.evaluation` and record the real observed
`AgencyReport.property_scores()` for the fixture policy. Create
`agentic/evaluation/baselines/fixture_floors.json` mapping each of the eight `AgencyProperty`
values to a floor at or just below the observed score, plus a `pass_rate` floor and a
`recorded_on` date and short `note` explaining that these are regression floors rather than
targets. Create `tests/agentic/test_agency_floors.py` which loads the JSON, runs
`run_agency_suite()`, and asserts every property score and the overall pass rate meet their floor,
with an assertion message naming property, floor, and observed value. Add a second test asserting
the floors file covers every member of `AgencyProperty`, so a new property cannot be added without
a floor. Ensure the file is packaged alongside the module (no reliance on the current working
directory) by resolving it relative to `__file__`.</action>
  <acceptance_criteria>`agentic/evaluation/baselines/fixture_floors.json` exists.
`agentic/evaluation/baselines/fixture_floors.json` contains `calibrated_confidence`.
`agentic/evaluation/baselines/fixture_floors.json` contains `recorded_on`.
`tests/agentic/test_agency_floors.py` exists.
`tests/agentic/test_agency_floors.py` contains `property_scores`.
`tests/agentic/test_agency_floors.py` asserts coverage of every `AgencyProperty` member.
`python3 -m pytest tests/agentic/test_agency_floors.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic/test_agency_floors.py -q --tb=short</automated>
  </verify>
  <done>A prompt edit that quietly degrades calibration now breaks the build instead of shipping.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Run the benchmark and write the scoreboard</name>
  <files>docs/agent/agency-scoreboard.md
docs/agent/agency-evaluation.md</files>
  <read_first>backend/dev/agency_bench.py
agentic/evaluation/scoreboard.py
agentic/evaluation/cases.py
docs/agent/agency-evaluation.md
docs/observability.md</read_first>
  <behavior>
    - The scoreboard reports, per policy: overall pass rate, all eight property scores, verdict
      stability across trials, total and mean cost, and p95 latency.
    - The fixture policy appears as the baseline row and is described accurately as a tuned rule
      engine, not a strawman.
    - Results are reported as measured. A model scoring below the deterministic baseline is
      published as-is with a short note on which properties it lost.
    - The document states the trial count and the exact prompt version each row used, so a future
      re-run is comparable.
  </behavior>
  <action>Run `python3 -m backend.dev.agency_bench` with `--policy fixture` and `--policy model`
for each model to be measured, `--trials 5`, a sensible `--max-cost-usd`, and `--format both`.
Create `docs/agent/agency-scoreboard.md` containing: a short statement of what the suite measures
and why it is deterministic (no model judging a model); the generated table; a per-property
commentary section calling out where models diverge from the baseline, with particular attention
to `calibrated_confidence` and `avoids_redundant_experiments`; an explicit stability section
listing any case whose verdict was not unanimous; a cost-versus-quality observation; and a
reproduction section giving the exact command, trial count, and prompt versions used. If the suite
turns out to be saturated — every policy near 100% — say so plainly and record it as the signal to
harden `AGENCY_CASES`. Update `docs/agent/agency-evaluation.md` to document the bench harness and
link the scoreboard.</action>
  <acceptance_criteria>`docs/agent/agency-scoreboard.md` exists.
`docs/agent/agency-scoreboard.md` contains `suite_agency_v1`.
`docs/agent/agency-scoreboard.md` contains `calibrated_confidence`.
`docs/agent/agency-scoreboard.md` contains a reproduction command referencing `backend.dev.agency_bench`.
`docs/agent/agency-scoreboard.md` records the trial count and prompt versions.
`docs/agent/agency-evaluation.md` contains `agency-scoreboard`.</acceptance_criteria>
  <verify>
    <manual>Confirm every table row states its trial count, and that any non-unanimous case appears in the stability section rather than only in the averaged score.</manual>
  </verify>
  <done>The measurement the suite was built for exists, in the repository, with its method stated.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: On-demand model workflow and an honest README</name>
  <files>.github/workflows/agency-bench.yml
README.md</files>
  <read_first>.github/workflows/ci.yml
README.md
docs/agent/agency-scoreboard.md</read_first>
  <behavior>
    - The model benchmark is triggerable by hand and never by a pull request, because it costs
      money and depends on a provider.
    - The offline floor gate needs no new workflow — it rides the existing backend pytest job.
    - The README's Status section reports the result and links the scoreboard instead of
      disclaiming that the measurement is missing.
    - Remaining honest limitations stay; only the one this phase closed is removed.
  </behavior>
  <action>Create `.github/workflows/agency-bench.yml` with a `workflow_dispatch` trigger only —
no `pull_request`, no `push` — taking inputs for model id, trial count, and cost ceiling. It
installs `requirements-dev.lock`, reads the provider key from repository secrets, runs
`python -m backend.dev.agency_bench`, and uploads the JSON and markdown as artifacts. Do not add
the model suite to `ci.yml`. In `README.md`, replace the "that measurement has not been run"
bullet with a short statement of what was measured, the headline result, and a link to
`docs/agent/agency-scoreboard.md`; move the agency benchmark into the Stable list if the result
supports it. Leave the other stated limits — MCP rate limiting and handshake auth, no CD, no
backup/restore runbook, single-host Compose — exactly as they are.</action>
  <acceptance_criteria>`.github/workflows/agency-bench.yml` exists.
`.github/workflows/agency-bench.yml` contains `workflow_dispatch`.
`.github/workflows/agency-bench.yml` does not contain `pull_request`.
`.github/workflows/ci.yml` does not reference `agency_bench`.
`README.md` contains `docs/agent/agency-scoreboard.md`.
`README.md` no longer contains `that measurement has not been run`.
`README.md` still contains the MCP rate limiting limitation.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
    <manual>Confirm the README's remaining limitations are unchanged and that no per-PR job can trigger a paid model run.</manual>
  </verify>
  <done>The result is published, reproducible on demand, and cannot be quietly regressed.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/agentic tests/test_agency_bench.py -q --tb=short`.
Confirm `python3 -m agentic.evaluation` still runs offline and meets the committed floors.
Review `docs/agent/agency-scoreboard.md` against the actual bench output before merging.
</verification>

<success_criteria>
The repository publishes a reproducible measurement of how well real models reason inside the
investigation loop, scored on eight deterministic properties with stated variance and cost; a
per-property regression floor is enforced by the free offline suite on every PR; and the README's
claims match what has actually been measured.
</success_criteria>

<output>
After completion, create `.planning/phases/31-agency-benchmark-under-real-models/31-agency-benchmark-under-real-models-03-SUMMARY.md`
</output>
