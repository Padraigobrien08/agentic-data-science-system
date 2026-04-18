---
phase: 06-validation-boundaries-and-policy
plan: 03
type: execute
wave: 3
depends_on:
  - "06-02"
files_modified:
  - edgar_project/cli.py
  - edgar_project/evaluation/scripts/run_suite.py
  - edgar_project/evaluation/README.md
  - README.md
  - data/README.md
  - tests/test_evaluate_cli_guardrails.py
autonomous: true
requirements:
  - VALID-03
must_haves:
  truths:
    - "The default `evaluate` workflows remain fixture-first and do not silently opt into live or hybrid validation."
    - "Live or hybrid suites require explicit operator acknowledgement through `--allow-live` and remain non-merge-blocking by default when the acknowledgement is absent."
    - "Project docs explicitly distinguish evaluation traffic from normal user runs and describe live or hybrid evaluation as operator-invoked and fair-access-sensitive."
  artifacts:
    - path: edgar_project/cli.py
      provides: "Root CLI flag and help text for explicit live-evaluation acknowledgement"
    - path: edgar_project/evaluation/scripts/run_suite.py
      provides: "Standalone evaluation script parity for the same live-evaluation guardrail"
    - path: edgar_project/evaluation/README.md
      provides: "Evaluation docs that explain fixture-default versus operator-invoked live or hybrid policy"
    - path: tests/test_evaluate_cli_guardrails.py
      provides: "Regression coverage for default fixture behavior and `--allow-live`"
  key_links:
    - from: edgar_project/cli.py
      to: edgar_project/evaluation/runner.py
      via: "root evaluate command passes `allow_live_cases` into the runner"
      pattern: "allow_live_cases=args.allow_live"
    - from: edgar_project/evaluation/scripts/run_suite.py
      to: edgar_project/evaluation/runner.py
      via: "standalone script uses the same explicit live opt-in contract as the root CLI"
      pattern: "allow_live_cases=args.allow_live"
    - from: tests/test_evaluate_cli_guardrails.py
      to: edgar_project/cli.py
      via: "CLI regressions lock fixture-default behavior and explicit live acknowledgement"
      pattern: "--allow-live|suite_fixtures_v1.json"
---

<objective>
Put the explicit live-evaluation guardrail on the operator entrypoints and documentation.

Purpose: satisfy `VALID-03` by keeping live or hybrid evaluation intentionally operator-invoked, fair-access-sensitive, and outside default user or merge workflows.
Output: CLI `--allow-live` support, standalone script parity, updated docs, and CLI guardrail regressions.
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
@.planning/phases/06-validation-boundaries-and-policy/06-validation-boundaries-and-policy-02-PLAN.md
@edgar_project/cli.py
@edgar_project/evaluation/scripts/run_suite.py
@edgar_project/evaluation/README.md
@README.md
@data/README.md

<interfaces>
From `edgar_project/cli.py`:
```python
def _cmd_evaluate(args: argparse.Namespace) -> int: ...
def build_parser() -> argparse.ArgumentParser: ...
```

From `edgar_project/evaluation/scripts/run_suite.py`:
```python
def parse_args() -> argparse.Namespace: ...
def main() -> int: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Require explicit `--allow-live` acknowledgement on evaluation entrypoints</name>
  <files>edgar_project/cli.py
edgar_project/evaluation/scripts/run_suite.py
tests/test_evaluate_cli_guardrails.py</files>
  <read_first>.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md
.planning/phases/06-validation-boundaries-and-policy/06-RESEARCH.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
edgar_project/cli.py
edgar_project/evaluation/scripts/run_suite.py
edgar_project/evaluation/runner.py
tests/test_evaluation_runner_policy.py</read_first>
  <behavior>
    - `python3 -m edgar_project.cli evaluate` stays fixture-default.
    - Live or hybrid suites only avoid `policy_skipped` when the operator explicitly passes `--allow-live`.
    - Both CLI entrypoints use the same guardrail and help text.
  </behavior>
  <action>Update `edgar_project/cli.py` so the `evaluate` subcommand defines an exact flag `--allow-live` with help text stating live or hybrid suites are operator-invoked and non-merge-blocking by default. In `_cmd_evaluate(...)`, pass `allow_live_cases=args.allow_live` into `EvaluationRunner(...)` and keep the default suite path unchanged. Update `edgar_project/evaluation/scripts/run_suite.py` so `parse_args(...)` accepts an optional `argv` parameter for tests, defines the same `--allow-live` flag, and passes `allow_live_cases=args.allow_live` into its `EvaluationRunner(...)`. Create `tests/test_evaluate_cli_guardrails.py` first and cover: the root `evaluate` parser defaults `allow_live` to `False`, the default suite path still points at `suite_fixtures_v1.json`, the standalone script parser defaults `allow_live` to `False`, and both parsers accept `--allow-live` as `True`.</action>
  <acceptance_criteria>`edgar_project/cli.py` contains `--allow-live`.
`edgar_project/cli.py` still contains `suite_fixtures_v1.json`.
`edgar_project/cli.py` contains `allow_live_cases=args.allow_live`.
`edgar_project/evaluation/scripts/run_suite.py` contains `--allow-live`.
`edgar_project/evaluation/scripts/run_suite.py` contains `allow_live_cases=args.allow_live`.
`edgar_project/evaluation/scripts/run_suite.py` defines `parse_args(` with an optional argv parameter or equivalent testable parser path.
`tests/test_evaluate_cli_guardrails.py` asserts both parsers default `allow_live` to `False`.
`tests/test_evaluate_cli_guardrails.py` asserts both parsers accept `--allow-live`.
`python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short</automated>
  </verify>
  <done>The CLI layer now makes live or hybrid evaluation an explicit operator decision instead of an ambiguous suite detail.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Update docs to keep evaluation policy distinct from normal runs</name>
  <files>edgar_project/evaluation/README.md
README.md
data/README.md
tests/test_evaluate_cli_guardrails.py</files>
  <read_first>.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md
.planning/phases/06-validation-boundaries-and-policy/06-RESEARCH.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
README.md
data/README.md
edgar_project/evaluation/README.md
edgar_project/cli.py</read_first>
  <behavior>
    - Docs say fixture evaluation is the default regression path.
    - Docs say live or hybrid evaluation is operator-invoked, fair-access-sensitive, and not merge-blocking by default.
    - Docs keep benchmark outputs distinct from normal run outputs.
  </behavior>
  <action>Update `edgar_project/evaluation/README.md` so the `Fixture-based vs live benchmarks` section explicitly says `live` and `hybrid` require `--allow-live`, remain non-merge-blocking by default, and use invariants or freshness windows rather than exact-value expectations. Update the root `README.md` CLI reference and benchmark guidance to say `evaluate` defaults to the offline fixture suite and live or hybrid suites require `--allow-live`. Update `data/README.md` so the `evaluation/` row explicitly says evaluation outputs are operator or benchmark traffic and are not normal user-run histories. Extend `tests/test_evaluate_cli_guardrails.py` with doc-string or file-content assertions that grep these exact phrases: `operator-invoked`, `non-merge-blocking`, and `--allow-live` across the updated docs.</action>
  <acceptance_criteria>`edgar_project/evaluation/README.md` contains `--allow-live`.
`edgar_project/evaluation/README.md` contains `operator-invoked`.
`edgar_project/evaluation/README.md` contains `non-merge-blocking`.
`README.md` contains `evaluate` and `--allow-live` in the benchmark guidance.
`README.md` contains `fixture suite` or `offline fixture suite`.
`data/README.md` contains `evaluation/` and `not normal user-run` or equivalent explicit separation language.
`tests/test_evaluate_cli_guardrails.py` contains assertions for `operator-invoked`.
`tests/test_evaluate_cli_guardrails.py` contains assertions for `non-merge-blocking`.
`python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short</automated>
  </verify>
  <done>The docs now reinforce the same policy boundary as the CLI: evaluation is fixture-first by default, and live or hybrid suites are explicit operator work, not ordinary user runs or merge gates.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluate_cli_guardrails.py -q --tb=short` after each task so the CLI contract and docs stay aligned on explicit live-evaluation policy.
</verification>

<success_criteria>
Phase 06 finishes its boundary work once the evaluation entrypoints and docs make live or hybrid usage explicit, operator-only, and non-default while leaving fixture evaluation as the normal regression path.
</success_criteria>

<output>
After completion, create `.planning/phases/06-validation-boundaries-and-policy/06-validation-boundaries-and-policy-03-SUMMARY.md`
</output>
