---
phase: 06-validation-boundaries-and-policy
plan: 02
type: execute
wave: 2
depends_on:
  - "06-01"
files_modified:
  - edgar_project/evaluation/runner.py
  - edgar_project/evaluation/summary_report.py
  - examples/evaluation_results.example.json
  - examples/evaluation_summary.example.json
  - tests/test_evaluation_runner_policy.py
autonomous: true
requirements:
  - VALID-02
must_haves:
  truths:
    - "Runner output distinguishes product regressions, policy skips, stale-source cases, and upstream SEC degradation without collapsing all routing into `status` or `message`."
    - "Suite summaries and human-readable reports expose degradation context that an operator can inspect directly."
    - "Documented example JSON files match the real structured result shape that Phase 06 introduces."
  artifacts:
    - path: edgar_project/evaluation/runner.py
      provides: "Deterministic degradation classification and policy-aware result enrichment"
    - path: edgar_project/evaluation/summary_report.py
      provides: "Console and markdown reporting that surfaces degradation routing context"
    - path: examples/evaluation_results.example.json
      provides: "Static example of per-case result fields including degradation, policy, and observation"
    - path: tests/test_evaluation_runner_policy.py
      provides: "Regression coverage for degradation classification and summary/report output"
  key_links:
    - from: edgar_project/evaluation/runner.py
      to: edgar_project/evaluation/summary_report.py
      via: "summary output consumes runner-populated degradation fields and counts"
      pattern: "degradation_class|degradation_counts"
    - from: tests/test_evaluation_runner_policy.py
      to: edgar_project/evaluation/runner.py
      via: "tests lock the mapping from runner outcomes to explicit degradation classes"
      pattern: "policy_skipped|product_regression|stale_source|upstream_sec_degraded"
    - from: examples/evaluation_results.example.json
      to: edgar_project/evaluation/schemas.py
      via: "example output demonstrates the current structured result contract"
      pattern: "degradation_class|policy|observation"
---

<objective>
Make evaluation results and summaries surface explicit degradation routing and policy context.

Purpose: satisfy `VALID-02` on the current inspectable output surfaces before later phases add a full evaluation control plane.
Output: a policy-aware runner, degradation-aware summaries and reports, static example JSON that matches the new shape, and regression tests.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md
@.planning/phases/06-validation-boundaries-and-policy/06-RESEARCH.md
@.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
@.planning/phases/06-validation-boundaries-and-policy/06-validation-boundaries-and-policy-01-PLAN.md
@edgar_project/evaluation/schemas.py
@edgar_project/evaluation/runner.py
@edgar_project/evaluation/summary_report.py
@examples/evaluation_results.example.json
@examples/evaluation_summary.example.json

<interfaces>
From `edgar_project/evaluation/runner.py`:
```python
class EvaluationRunner:
    def __init__(
        self,
        suite: BenchmarkSuite,
        rubric: Rubric | None = None,
        *,
        update_regression_goldens: bool = False,
    ) -> None: ...
```

From `edgar_project/evaluation/summary_report.py`:
```python
def format_benchmark_cli_summary(summary: EvaluationSummary, results: list[EvaluationResult], *, results_json_path: str, summary_json_path: str | None = None) -> str: ...
def format_console_report(summary: EvaluationSummary, results: list[EvaluationResult]) -> str: ...
def render_markdown_report(summary: EvaluationSummary, results: list[EvaluationResult]) -> str: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add deterministic degradation classification to runner results</name>
  <files>edgar_project/evaluation/runner.py
tests/test_evaluation_runner_policy.py</files>
  <read_first>.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md
.planning/phases/06-validation-boundaries-and-policy/06-RESEARCH.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
edgar_project/evaluation/schemas.py
edgar_project/evaluation/runner.py
edgar_project/evaluation/summary_report.py
edgar_project/evaluation/benchmarks/suite_smoke.json</read_first>
  <behavior>
    - Lifecycle status and degradation routing are computed separately.
    - Omitted live opt-in becomes `policy_skipped`, not a generic skipped note.
    - Fixture or mocked failures map to `product_regression`.
    - Freshness-window breaches and upstream SEC failures have reserved deterministic mappings for later live execution.
  </behavior>
  <action>Refactor `edgar_project/evaluation/runner.py` to add `allow_live_cases: bool = False` to `EvaluationRunner.__init__` and `from_case_file(...)`. Add a pure helper such as `_classify_degradation_class(...)` that returns `ValidationDegradationClass.policy_skipped` when `case.input.mode` is `live` or `hybrid` and `allow_live_cases` is false, returns `ValidationDegradationClass.product_regression` when deterministic checks fail on `fixture` or `orchestration_mocked` cases, returns `ValidationDegradationClass.stale_source` when `source_age_seconds > freshness_window_seconds`, returns `ValidationDegradationClass.upstream_sec_degraded` when a live or hybrid path reports upstream error codes such as `sec_rate_limited`, `sec_access_denied`, `sec_unavailable`, or `upstream_unavailable`, and otherwise returns `ValidationDegradationClass.none`. Populate `result.degradation_class`, `result.policy`, and `result.observation` in every case path. In the current live or hybrid branch, when `allow_live_cases` is false, keep `status = EvaluationStatus.skipped` but set `degradation_class = policy_skipped` and use the exact message `policy skipped: live/hybrid validation requires explicit --allow-live opt-in and remains non-merge-blocking by default.` When `allow_live_cases` is true, keep the current not-implemented skip semantics but set `degradation_class = none` rather than `policy_skipped`. Create `tests/test_evaluation_runner_policy.py` first and cover: fixture failure -> `product_regression`, no live opt-in -> `policy_skipped`, synthetic stale observation -> `stale_source`, and synthetic upstream error code -> `upstream_sec_degraded`.</action>
  <acceptance_criteria>`edgar_project/evaluation/runner.py` contains `allow_live_cases: bool = False`.
`edgar_project/evaluation/runner.py` contains `policy skipped: live/hybrid validation requires explicit --allow-live opt-in`.
`edgar_project/evaluation/runner.py` contains `ValidationDegradationClass.product_regression`.
`edgar_project/evaluation/runner.py` contains `ValidationDegradationClass.stale_source`.
`edgar_project/evaluation/runner.py` contains `ValidationDegradationClass.upstream_sec_degraded`.
`edgar_project/evaluation/runner.py` assigns `result.degradation_class`.
`tests/test_evaluation_runner_policy.py` contains `policy_skipped`.
`tests/test_evaluation_runner_policy.py` contains `product_regression`.
`tests/test_evaluation_runner_policy.py` contains `stale_source`.
`tests/test_evaluation_runner_policy.py` contains `upstream_sec_degraded`.
`python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short</automated>
  </verify>
  <done>The runner now produces explicit degradation routing for operators instead of leaving all interpretation to free-form status messages.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Surface degradation routing in summaries, reports, and example result shapes</name>
  <files>edgar_project/evaluation/summary_report.py
examples/evaluation_results.example.json
examples/evaluation_summary.example.json
tests/test_evaluation_runner_policy.py</files>
  <read_first>.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md
.planning/phases/06-validation-boundaries-and-policy/06-RESEARCH.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
edgar_project/evaluation/schemas.py
edgar_project/evaluation/summary_report.py
examples/evaluation_results.example.json
examples/evaluation_summary.example.json
tests/test_evaluation_runner_policy.py</read_first>
  <behavior>
    - Suite summaries expose degradation counts, not only pass/fail counts.
    - Human-readable console or markdown output surfaces degradation class for non-passing or skipped cases.
    - Static example JSON files match the new structured output shape so docs stay trustworthy.
  </behavior>
  <action>Update `edgar_project/evaluation/summary_report.py` so `summary_json_blob(...)` emits a `degradation_counts` object derived from result `degradation_class` values. Extend `format_benchmark_cli_summary(...)` to print a line `degradation:` followed by the non-zero degradation counts when any exist. Update `format_console_report(...)` and `render_markdown_report(...)` so each non-passing or skipped case includes its `degradation_class` alongside `status`, and the markdown table adds a dedicated `degradation` column. Update `examples/evaluation_results.example.json` so at least one case shows `degradation_class`, `policy`, and `observation`, with the live example case using `policy_skipped`. Update `examples/evaluation_summary.example.json` to include `degradation_counts` and at least one non-zero `policy_skipped` count. Extend `tests/test_evaluation_runner_policy.py` so it renders the summary/report helpers against synthetic results and asserts the output contains `policy_skipped`, `product_regression`, and `degradation_counts`.</action>
  <acceptance_criteria>`edgar_project/evaluation/summary_report.py` contains `degradation_counts`.
`edgar_project/evaluation/summary_report.py` contains `degradation` in the markdown table header or CLI output.
`examples/evaluation_results.example.json` contains `"degradation_class":`.
`examples/evaluation_results.example.json` contains `"policy":`.
`examples/evaluation_results.example.json` contains `"observation":`.
`examples/evaluation_summary.example.json` contains `"degradation_counts":`.
`examples/evaluation_summary.example.json` contains `"policy_skipped":`.
`tests/test_evaluation_runner_policy.py` contains `degradation_counts`.
`tests/test_evaluation_runner_policy.py` asserts rendered output includes `policy_skipped`.
`python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short</automated>
  </verify>
  <done>Operators can now inspect degradation routing directly in the current result files and human-readable summaries, and the static examples match the real contract.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluation_runner_policy.py -q --tb=short` after each task so runner classification and report output stay in sync.
</verification>

<success_criteria>
Phase 06 gives operators actionable validation outcomes once result files and summaries show explicit degradation classes and policy context rather than only generic skipped or failed messages.
</success_criteria>

<output>
After completion, create `.planning/phases/06-validation-boundaries-and-policy/06-validation-boundaries-and-policy-02-SUMMARY.md`
</output>
