---
phase: 27-agency-benchmark-under-real-models
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - agentic/evaluation/runner.py
  - agentic/evaluation/scoreboard.py
  - agentic/evaluation/__init__.py
  - backend/dev/agency_bench.py
  - tests/agentic/test_domain_boundary.py
  - tests/agentic/test_scoreboard.py
  - tests/test_agency_bench.py
autonomous: true
requirements:
  - AGCY-03
must_haves:
  truths:
    - "The agency suite can be run repeatedly against a model-backed policy and aggregated into a variance-aware scorecard."
    - "A case whose verdict changes across trials is reported as unstable rather than averaged into silence."
    - "Cost and latency per trial come from the existing observer events, not from a parallel measurement path."
    - "`agentic/` imports nothing from `backend/` anywhere, and reaches `edgar_project`/`src` only from the two EDGAR bridge modules — enforced by an AST test that sees function-local imports."
    - "`python -m agentic.evaluation` with no arguments still runs offline, free, and deterministic."
  artifacts:
    - path: agentic/evaluation/scoreboard.py
      provides: "Pure multi-trial aggregation: per-property means, stability, cost and latency"
    - path: backend/dev/agency_bench.py
      provides: "The only place a model-backed agency suite run is assembled"
    - path: tests/agentic/test_domain_boundary.py
      provides: "AST-based guard that the agentic domain stays dependency-free"
  key_links:
    - from: backend/dev/agency_bench.py
      to: agentic/evaluation/scoreboard.py
      via: "the bench runs N suites with a model policy and aggregates them through the pure scoreboard"
      pattern: "aggregate_trials|PolicyScorecard|run_agency_suite"
    - from: agentic/evaluation/runner.py
      to: agentic/agent/loop.py
      via: "an injected observer reaches the loop so InvestigationEnded cost and timing are capturable"
      pattern: "observer=|InvestigationLoop("
---

<objective>
Make the suite runnable against a real model in a way that produces a defensible number rather
than an anecdote, and lock the domain boundary that this work is most likely to break.

Purpose: a single pass of a non-deterministic policy is not a measurement. Trials and variance are
what make the 27-03 scoreboard publishable.
Output: observer passthrough, a pure aggregation module, a backend-side bench harness, and a
purity test.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/27-agency-benchmark-under-real-models/27-CONTEXT.md
@.planning/phases/27-agency-benchmark-under-real-models/27-VALIDATION.md
@.planning/phases/27-agency-benchmark-under-real-models/27-agency-benchmark-under-real-models-01-PLAN.md
@agentic/evaluation/runner.py
@agentic/evaluation/agency.py
@agentic/evaluation/cases.py
@agentic/agent/observer.py
@agentic/agent/budget.py
@agentic/agent/loop.py
@backend/agents/agentic_model_policy.py
@backend/dev/llm_context_compare.py
@backend/config/settings.py

<interfaces>
From `agentic/agent/observer.py`:
```python
class InvestigationEnded:
    investigation_id: str
    status: InvestigationStatus
    termination_reason: TerminationReason | None
    iterations: int
    elapsed_seconds: float
    cost_usd: float
    model_calls: int
    partial: bool
```

From `agentic/evaluation/agency.py`:
```python
class AgencyReport(DomainModel):
    suite_id: str
    total: int
    passed: int
    results: list[AgencyCaseResult]
    def property_scores(self) -> dict[str, float]: ...
```

From `agentic/evaluation/runner.py` (current signature to extend):
```python
def run_agency_suite(*, policy=None, cases=AGENCY_CASES, suite_id=SUITE_ID) -> AgencyReport: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Lock the domain boundary before anything else touches it</name>
  <files>tests/agentic/test_domain_boundary.py</files>
  <read_first>agentic/agent/loop.py
agentic/evaluation/runner.py
.planning/phases/27-agency-benchmark-under-real-models/27-CONTEXT.md</read_first>
  <behavior>
    - No module under `agentic/` may import `backend`, at module level or inside a function.
      This is absolute: the investigation domain knows nothing about persistence or the API.
    - `edgar_project` and `src` may be imported **only** from the two EDGAR bridge modules
      `agentic/adapters/edgar.py` and `agentic/experiments/tools/edgar_tools.py`. A third file
      reaching for EDGAR computation means the adapter seam is leaking and must fail.
    - The check is structural (AST), so it cannot be defeated by a deferred or local import.
  </behavior>
  <action>Create `tests/agentic/test_domain_boundary.py`. Walk every `*.py` under `agentic/`,
parse each with `ast.parse`, and visit all `ast.Import` and `ast.ImportFrom` nodes via `ast.walk`
— nodes nested inside functions and methods must be included, because every existing
`edgar_project`/`src` import is function-local and a line-anchored grep misses all of them.
Assert that no file imports a module whose root is `backend`. Assert that imports rooted at
`edgar_project` or `src` appear only in the allowlist
`{"agentic/adapters/edgar.py", "agentic/experiments/tools/edgar_tools.py"}`, and add a second
assertion that both allowlisted files still exist, so the allowlist cannot rot into a no-op after
a rename. On failure, report the offending file, line number, and module name. Document in the
module docstring that the `backend` rule is what lets the domain be reused outside this
repository, while the EDGAR allowance is the adapter pattern working as intended — the
domain-specific plug-in reaching domain-specific computation, lazily, so the generic path never
pays for it. Baseline as of 2026-08-07: `backend` 0 imports; `edgar_project` 3 and `src` 3, all
within the two allowlisted files.</action>
  <acceptance_criteria>`tests/agentic/test_domain_boundary.py` exists.
`tests/agentic/test_domain_boundary.py` contains `ast.parse`.
`tests/agentic/test_domain_boundary.py` contains `edgar_project`.
`python3 -m pytest tests/agentic/test_domain_boundary.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic/test_domain_boundary.py -q --tb=short</automated>
  </verify>
  <done>The boundary that makes the domain portable is now enforced rather than merely observed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Observer passthrough and pure multi-trial aggregation</name>
  <files>agentic/evaluation/runner.py
agentic/evaluation/scoreboard.py
agentic/evaluation/__init__.py
tests/agentic/test_scoreboard.py</files>
  <read_first>agentic/evaluation/runner.py
agentic/evaluation/agency.py
agentic/agent/observer.py
agentic/evaluation/__init__.py</read_first>
  <behavior>
    - `run_case` and `run_agency_suite` accept an optional observer and forward it to the loop; the
      default stays `NULL_OBSERVER` so existing callers are unaffected.
    - Aggregation over N reports yields per-property means, overall pass rate, and an explicit list
      of cases whose pass/fail verdict was not unanimous across trials.
    - Cost and latency are read from captured `InvestigationEnded` events.
    - The module is pure: no I/O, no clock, no backend import, so it is unit-testable from
      synthetic reports.
  </behavior>
  <action>In `agentic/evaluation/runner.py` add `observer: AgentObserver | None = None` to both
`run_case` and `run_agency_suite`, defaulting to `NULL_OBSERVER`, and pass it into the
`InvestigationLoop(...)` construction. Keep every existing default behaviour identical. Create
`agentic/evaluation/scoreboard.py` containing: a `RunMetrics` model (`cost_usd`,
`elapsed_seconds`, `model_calls`, `investigation_id`); a `MetricsObserver` implementing the
`AgentObserver` surface that records `InvestigationEnded` events into a list and ignores the rest;
a `CaseStability` model (`case_id`, `passed_trials`, `total_trials`, with a `stable` property that
is true only when the verdict was unanimous); a `PolicyScorecard` model carrying `label`, `trials`,
`mean_pass_rate`, `property_means: dict[str, float]`, `unstable_cases: list[CaseStability]`,
`total_cost_usd`, `mean_cost_usd`, and `p95_latency_seconds`; and
`aggregate_trials(label: str, reports: Sequence[AgencyReport], metrics: Sequence[RunMetrics]) -> PolicyScorecard`.
Compute p95 by nearest-rank on the sorted elapsed times so a small trial count behaves sensibly.
Add `Scoreboard` holding many `PolicyScorecard` rows with `to_markdown()` and a
`model_dump(mode="json")`-friendly shape. Export the new names from
`agentic/evaluation/__init__.py`. Create `tests/agentic/test_scoreboard.py` driving aggregation
from synthetic `AgencyReport`s: unanimous cases are absent from `unstable_cases`, a case passing
in 2 of 3 trials is present, property means average correctly across reports, and p95 is exact on
a known list.</action>
  <acceptance_criteria>`agentic/evaluation/scoreboard.py` exists.
`agentic/evaluation/scoreboard.py` contains `class PolicyScorecard`.
`agentic/evaluation/scoreboard.py` contains `class CaseStability`.
`agentic/evaluation/scoreboard.py` contains `def aggregate_trials`.
`agentic/evaluation/scoreboard.py` contains `class MetricsObserver`.
`agentic/evaluation/runner.py` contains `observer`.
`agentic/evaluation/__init__.py` contains `aggregate_trials`.
`tests/agentic/test_scoreboard.py` exists.
`python3 -m pytest tests/agentic -q --tb=short` passes.
`python3 -m agentic.evaluation` exits 0.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short && python3 -m agentic.evaluation</automated>
  </verify>
  <done>Many suite runs can now be reduced to one honest scorecard that shows its own uncertainty.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: The model-backed bench harness</name>
  <files>backend/dev/agency_bench.py
tests/test_agency_bench.py</files>
  <read_first>backend/dev/llm_context_compare.py
backend/agents/agentic_model_policy.py
backend/config/settings.py
agentic/evaluation/scoreboard.py
agentic/evaluation/runner.py</read_first>
  <behavior>
    - This is the only place a model-backed agency run is assembled; `agentic/` never learns of it.
    - `--policy fixture` needs no provider and is the baseline row every report includes.
    - A suite-level cost ceiling stops the run before it overspends, on top of the per-run
      `LoopBudget.max_cost_usd`.
    - Output is both machine-readable JSON and a markdown table.
  </behavior>
  <action>Create `backend/dev/agency_bench.py` following the shape of
`backend/dev/llm_context_compare.py`. Provide `main(argv: list[str] | None = None) -> int` with
argparse flags `--policy {fixture,model}` (repeatable so one invocation can produce a baseline row
plus model rows), `--model <id>`, `--trials N` (default 3), `--max-cost-usd` (suite ceiling),
`--budget-cost-usd` (per-run `LoopBudget.max_cost_usd`), `--out <path>`, and
`--format {json,md,both}`. For each requested policy build the label and the `AgentPolicy` —
`FixtureAgentPolicy()` for `fixture`, and for `model` a `build_agent_policy` call against a
`Settings` copy whose `agent_completion_model` is the `--model` value. Run `run_agency_suite` once
per trial with a fresh `MetricsObserver`, accumulate reports and metrics, abort the remaining
trials and mark the scorecard truncated if the accumulated cost crosses `--max-cost-usd`, then
call `aggregate_trials`. Emit a `Scoreboard` over all rows. Add `backend/dev/__main__`-style
`if __name__ == "__main__": raise SystemExit(main())`. Create `tests/test_agency_bench.py` that
runs the harness with `--policy fixture --trials 2` and a stub policy factory, asserting a
scorecard is produced with two trials, a JSON payload is written to `--out`, no network call is
attempted, and the cost ceiling truncates when set below the accrued cost.</action>
  <acceptance_criteria>`backend/dev/agency_bench.py` exists.
`backend/dev/agency_bench.py` contains `--trials`.
`backend/dev/agency_bench.py` contains `--max-cost-usd`.
`backend/dev/agency_bench.py` contains `aggregate_trials`.
`backend/dev/agency_bench.py` contains `build_agent_policy`.
`tests/test_agency_bench.py` exists.
`python3 -m pytest tests/test_agency_bench.py -q --tb=short` passes.
`python3 -m backend.dev.agency_bench --policy fixture --trials 2 --format md` exits 0.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_agency_bench.py -q --tb=short && python3 -m backend.dev.agency_bench --policy fixture --trials 2 --format md</automated>
  </verify>
  <done>The suite can be pointed at a real model, repeatedly, under a cost ceiling, from one command.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/agentic tests/test_agency_bench.py -q --tb=short` after each task.
Confirm `python3 -m agentic.evaluation` still needs no provider and no network.
</verification>

<success_criteria>
`suite_agency_v1` can be run against a model-backed policy over multiple trials under a cost
ceiling, producing a scorecard that reports per-property quality, verdict stability, spend, and
latency — while the offline fixture path and the domain boundary are both provably unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/27-agency-benchmark-under-real-models/27-agency-benchmark-under-real-models-02-SUMMARY.md`
</output>
