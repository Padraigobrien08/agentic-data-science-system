---
phase: 06-validation-boundaries-and-policy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - edgar_project/evaluation/schemas.py
  - edgar_project/evaluation/benchmarks/suite_smoke.json
  - tests/test_evaluation_policy_contract.py
autonomous: true
requirements:
  - VALID-02
  - VALID-03
must_haves:
  truths:
    - "Validation cases can represent policy intent, freshness windows, and degradation routing with typed fields instead of only free-form notes."
    - "`live` and `hybrid` manifests require explicit operator-only live policy metadata, while fixture and `orchestration_mocked` manifests remain backward compatible."
    - "Per-case result models can record a degradation class separately from lifecycle status so later phases do not need to overload `message` strings."
  artifacts:
    - path: edgar_project/evaluation/schemas.py
      provides: "Typed validation policy, observation, and degradation contract for benchmark manifests and results"
    - path: edgar_project/evaluation/benchmarks/suite_smoke.json
      provides: "Concrete live-manifest example using the explicit policy and freshness contract"
    - path: tests/test_evaluation_policy_contract.py
      provides: "Regression coverage for policy-required live manifests and backward-compatible fixture parsing"
  key_links:
    - from: edgar_project/evaluation/schemas.py
      to: edgar_project/evaluation/benchmarks/suite_smoke.json
      via: "smoke manifest validates against the new live-policy and freshness fields"
      pattern: "requires_explicit_live_opt_in|freshness_window_seconds"
    - from: tests/test_evaluation_policy_contract.py
      to: edgar_project/evaluation/schemas.py
      via: "schema regression tests lock live-policy validation and result-field defaults"
      pattern: "ValidationDegradationClass|BenchmarkSuite"
---

<objective>
Define the typed policy, freshness, and degradation contract for validation cases and results.

Purpose: establish the Phase 06 source-of-truth contract before runner, summary, and CLI changes rely on it.
Output: enriched evaluation schemas, a policy-aware `suite_smoke.json` scaffold, and schema regressions.
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
@edgar_project/evaluation/README.md
@edgar_project/evaluation/schemas.py
@edgar_project/evaluation/benchmarks/suite_smoke.json
@edgar_project/evaluation/runner.py

<interfaces>
From `edgar_project/evaluation/schemas.py`:
```python
class InputMode(str, Enum):
    fixture = "fixture"
    live = "live"
    hybrid = "hybrid"
    orchestration_mocked = "orchestration_mocked"

class BenchmarkInput(BaseModel):
    mode: InputMode = InputMode.live
    tickers: list[str]
    goal: str
    refresh: bool

class EvaluationResult(BaseModel):
    case_id: str
    status: EvaluationStatus = EvaluationStatus.pending
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend evaluation schemas with typed live-policy and degradation contracts</name>
  <files>edgar_project/evaluation/schemas.py
tests/test_evaluation_policy_contract.py</files>
  <read_first>.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md
.planning/phases/06-validation-boundaries-and-policy/06-RESEARCH.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
edgar_project/evaluation/README.md
edgar_project/evaluation/schemas.py
edgar_project/evaluation/runner.py</read_first>
  <behavior>
    - `live` and `hybrid` cases encode explicit operator-invoked policy instead of relying on comments or notes.
    - Case results can represent lifecycle status and degradation routing separately.
    - Existing fixture and `orchestration_mocked` manifests remain valid without a new policy block.
  </behavior>
  <action>Update `edgar_project/evaluation/schemas.py` to add the exact enum `ValidationDegradationClass` with values `none`, `product_regression`, `upstream_sec_degraded`, `stale_source`, and `policy_skipped`. Add `ValidationPolicy` with the exact fields `requires_explicit_live_opt_in: bool = False`, `fair_access_policy: str | None = None`, `allow_merge_blocking: bool = False`, `normal_user_visible: bool = False`, and `freshness_window_seconds: int | None = Field(default=None, ge=0)`. Add `ValidationObservation` with `observed_at`, `source_observed_at`, `source_age_seconds`, and `freshness_window_seconds`. Add `policy: ValidationPolicy | None = None` to `BenchmarkInput`, and add `degradation_class: ValidationDegradationClass = ValidationDegradationClass.none`, `policy: ValidationPolicy | None = None`, and `observation: ValidationObservation | None = None` to `EvaluationResult`. Add validators so `live` and `hybrid` require a non-null `policy`, `requires_explicit_live_opt_in is True`, non-empty `fair_access_policy`, and `allow_merge_blocking is False`, while `fixture` and `orchestration_mocked` do not require those fields. Create `tests/test_evaluation_policy_contract.py` first with schema-level tests that prove fixture manifests still validate without `policy`, live manifests fail without a `policy` block, live manifests fail when `allow_merge_blocking` is true, and `EvaluationResult` defaults `degradation_class` to `none` independently of `status`.</action>
  <acceptance_criteria>`edgar_project/evaluation/schemas.py` contains `class ValidationDegradationClass`.
`edgar_project/evaluation/schemas.py` contains `policy_skipped = "policy_skipped"`.
`edgar_project/evaluation/schemas.py` contains `class ValidationPolicy`.
`edgar_project/evaluation/schemas.py` contains `requires_explicit_live_opt_in: bool = False`.
`edgar_project/evaluation/schemas.py` contains `fair_access_policy: str | None = None`.
`edgar_project/evaluation/schemas.py` contains `allow_merge_blocking: bool = False`.
`edgar_project/evaluation/schemas.py` contains `degradation_class: ValidationDegradationClass`.
`tests/test_evaluation_policy_contract.py` contains `ValidationDegradationClass.policy_skipped`.
`tests/test_evaluation_policy_contract.py` contains an assertion that live manifests without `policy` raise a validation error.
`python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short</automated>
  </verify>
  <done>The evaluation schema layer now expresses explicit live-policy intent and typed degradation routing without breaking the default fixture or mocked suites.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Update the smoke live suite scaffold to use the explicit policy contract</name>
  <files>edgar_project/evaluation/benchmarks/suite_smoke.json
tests/test_evaluation_policy_contract.py</files>
  <read_first>.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md
.planning/phases/06-validation-boundaries-and-policy/06-RESEARCH.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
edgar_project/evaluation/benchmarks/suite_smoke.json
edgar_project/evaluation/schemas.py
edgar_project/evaluation/README.md</read_first>
  <behavior>
    - The live smoke manifest demonstrates the explicit operator-only policy expected for `live` cases.
    - The live scaffold encodes a freshness window instead of implying exact snapshot assertions.
    - The suite remains a scaffold and does not become the default fixture benchmark suite.
  </behavior>
  <action>Update `edgar_project/evaluation/benchmarks/suite_smoke.json` so the existing `smoke_aapl_msft` live case includes an exact `policy` block under `input` with `requires_explicit_live_opt_in: true`, `fair_access_policy: "sec_fair_access_operator_invoked"`, `allow_merge_blocking: false`, `normal_user_visible: false`, and `freshness_window_seconds: 300`. Keep the case `mode` as `live`, preserve the current goal and artifact expectations, and update the `notes` string so it explicitly says this is a policy scaffold for live validation rather than the default regression suite. Extend `tests/test_evaluation_policy_contract.py` with a manifest regression that loads `suite_smoke.json` through `BenchmarkSuite.model_validate_json(...)`, asserts the live case keeps `mode == InputMode.live`, and asserts the exact policy values above are present after parsing.</action>
  <acceptance_criteria>`edgar_project/evaluation/benchmarks/suite_smoke.json` contains `"requires_explicit_live_opt_in": true`.
`edgar_project/evaluation/benchmarks/suite_smoke.json` contains `"fair_access_policy": "sec_fair_access_operator_invoked"`.
`edgar_project/evaluation/benchmarks/suite_smoke.json` contains `"allow_merge_blocking": false`.
`edgar_project/evaluation/benchmarks/suite_smoke.json` contains `"normal_user_visible": false`.
`edgar_project/evaluation/benchmarks/suite_smoke.json` contains `"freshness_window_seconds": 300`.
`edgar_project/evaluation/benchmarks/suite_smoke.json` still contains `"mode": "live"`.
`tests/test_evaluation_policy_contract.py` contains `suite_smoke.json`.
`tests/test_evaluation_policy_contract.py` asserts the parsed live case policy includes `sec_fair_access_operator_invoked`.
`python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short</automated>
  </verify>
  <done>The live smoke suite now shows the exact operator-only live policy and freshness contract the rest of the phase builds on.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluation_policy_contract.py -q --tb=short` after each task so the schema contract stays backward compatible while locking the new live-policy rules.
</verification>

<success_criteria>
Phase 06 has a real policy source of truth once evaluation manifests can encode explicit live guardrails and per-case results can express degradation routing independently from raw runner status strings.
</success_criteria>

<output>
After completion, create `.planning/phases/06-validation-boundaries-and-policy/06-validation-boundaries-and-policy-01-SUMMARY.md`
</output>
