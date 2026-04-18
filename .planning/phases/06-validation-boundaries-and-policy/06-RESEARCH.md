# Phase 06: Validation Boundaries and Policy - Research

**Researched:** 2026-04-18
**Domain:** Evaluation policy boundaries, degradation taxonomy, and explicit live-validation guardrails
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Validation runs must stay explicitly separate from normal user work at the policy layer instead of being treated as ordinary analyses with light labeling.
- **D-02:** Validation retention and namespace handling must remain evaluation-scoped even before later phases add richer control-plane or child-run linkage.
- **D-03:** Validation outcomes must distinguish at least `product_regression`, `upstream_sec_degraded`, `stale_source`, and `policy_skipped`.
- **D-04:** The degradation taxonomy must help operators decide whether follow-up belongs to upstream monitoring or product debugging.
- **D-05:** Fixture and `orchestration_mocked` evaluation remain the default validation paths.
- **D-06:** `live` and `hybrid` evaluation stay explicit operator-invoked workflows, non-merge-blocking by default, and outside ordinary end-user paths.
- **D-07:** `live` and `hybrid` verdicts should use invariants and freshness windows instead of exact output equality.
- **D-08:** Stale SEC data must degrade a validation result instead of being classified as a product regression.

### the agent's Discretion
- Exact field and enum names for policy, observation, and degradation metadata
- Exact CLI flag names and default runner behavior, as long as live or hybrid use stays explicit
- Exact JSON/result shape used by current benchmark outputs, as long as operators can inspect degradation and policy context cleanly
- Exact backwards-compat strategy for existing fixture and orchestration benchmark manifests

### Deferred Ideas (OUT OF SCOPE)
- Dedicated evaluation dashboard or API control plane
- Child `AnalysisRun` linkage for live or hybrid cases
- Scheduled live canaries and alerting
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VALID-02 | Operator can inspect case-level validation outcomes with explicit degradation classes that distinguish SEC freshness or availability issues from product regressions | Extend evaluation result contracts with explicit degradation classes, structured observation metadata, and degradation-aware summary/report output. |
| VALID-03 | Live SEC validation enforces explicit fair-access controls and does not become a default merge-blocking or user-run path | Require manifest-level live policy metadata plus explicit CLI opt-in; keep fixture evaluation as the default suite and treat live or hybrid without opt-in as policy-skipped, not failed. |
</phase_requirements>

## Summary

Phase 06 should not try to build the full supported evaluation product surface yet. The repo already has the right foundation for a policy-first slice: `edgar_project/evaluation/schemas.py` defines `fixture`, `live`, `hybrid`, and `orchestration_mocked`; `edgar_project/evaluation/runner.py` already emits per-case JSON results; `edgar_project/evaluation/summary_report.py` already creates the console and markdown summaries operators inspect today; and the root CLI already keeps evaluation separate from normal analysis runs by defaulting `evaluate` to the offline fixture suite.

The missing piece is that the current evaluation path is too stringly and too coarse. A live or hybrid case today is only "skipped" with a free-form message. There is no typed degradation taxonomy, no explicit policy or freshness metadata on the case result, and no guardrail at the CLI layer to make live use feel intentionally operator-invoked. That means the product can describe future live validation in prose, but it cannot yet express the exact reason a case is safe to ignore, safe to rerun later, or evidence of a product regression.

The lowest-risk implementation path is therefore three additive slices: first, extend the evaluation contracts with typed policy, observation, and degradation fields while preserving backward compatibility for existing manifests; second, make the runner and summary/report output actually populate and expose those fields; third, put the explicit guardrail on the operator entrypoints and docs so live or hybrid suites are acknowledged as opt-in, fair-access-sensitive, and non-default.

**Primary recommendation:** Keep this phase inside the current evaluation package and CLI surfaces. Do not add a new evaluation API or child-run execution path yet. Instead, define the policy and degradation contract in `edgar_project/evaluation/schemas.py`, emit it through `runner.py` and `summary_report.py`, and enforce the live guardrail at the `evaluate` entrypoints.

Repo note: `AGENTS.md` was applied. No repository-local `.claude/skills/` or `.agents/skills/` directory exists under the project root.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python + Pydantic models in `edgar_project/evaluation/schemas.py` | existing repo stack | Typed validation policy, observation, and degradation metadata | The repo already models benchmark manifests and results with Pydantic; no new schema layer is needed. |
| Existing `EvaluationRunner` in `edgar_project/evaluation/runner.py` | in-repo seam | Case-level classification and operator-facing metadata population | This is already the place where per-case `status`, `message`, and `metadata` are produced. |
| Existing summary/report layer in `edgar_project/evaluation/summary_report.py` | in-repo seam | Console, markdown, and JSON summaries that operators inspect today | This is the current human-facing evaluation surface and should surface the new taxonomy. |
| Existing CLIs in `edgar_project/cli.py` and `edgar_project/evaluation/scripts/run_suite.py` | in-repo seam | Explicit operator invocation for live or hybrid suites | The product already keeps fixture evaluation as the default here; guardrails should stay at this boundary. |
| `pytest 8.4.2` via `pytest.ini` | local env | Schema, runner, and CLI guardrail regressions | Existing backend and evaluation work already uses pytest; no new framework or runner is required. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Existing benchmark JSON manifests under `edgar_project/evaluation/benchmarks/` | in-repo seam | Encode live or hybrid policy metadata and freshness windows | Use `suite_smoke.json` as the policy scaffold; keep the default fixture suite unchanged. |
| Static example outputs under `examples/` | in-repo docs seam | Show the new degradation and policy fields in documented result shapes | Update only once the real result contract is stable. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extend evaluation schemas and summaries in place | Add a new backend-only evaluation policy service first | Premature for Phase 06 because there is still no supported control plane using it. |
| Explicit CLI opt-in for live or hybrid suites | Rely on docs only | Too easy to drift into accidental or ambiguous live usage. |
| Separate `status` and `degradation_class` | Encode all routing detail in the free-form `message` string | Keeps results hard to inspect or summarize programmatically and defeats the requirement for explicit taxonomy. |
| Typed JSON policy metadata inside current result files | Immediate DB migration for `EvaluationRun` case-result storage | Better deferred to Phase 09, where first-class persisted evaluation records become the supported workflow. |

## Architecture Patterns

### Pattern 1: Separate Lifecycle Status from Degradation Class

**What:** Keep `EvaluationStatus` as the lifecycle field (`passed`, `failed`, `skipped`, `error`), but add a separate typed degradation class such as `none`, `product_regression`, `upstream_sec_degraded`, `stale_source`, and `policy_skipped`.

**When to use:** Every case result emitted by the runner, whether it comes from fixtures, mocked orchestration, or later live or hybrid execution.

**Why:** The repo currently only has `status` plus a text `message`. That is enough for basic regression output but not enough to route follow-up. The operator needs to know whether "skipped" means the policy refused to run, the source is stale, or the product failed.

**Recommended contract:**
- `status` answers "what happened in the runner lifecycle?"
- `degradation_class` answers "why should an operator care, and who owns the follow-up?"
- `message` remains the short human-readable explanation
- `observation` carries freshness-window and observation timestamps when relevant

### Pattern 2: Put Live Guardrails in the Manifest and CLI, Not Only in Docs

**What:** Add a typed policy block on `BenchmarkInput` for live or hybrid cases and an explicit `--allow-live` acknowledgement on the CLI entrypoints.

**When to use:** `live` and `hybrid` cases only.

**Why:** Guardrails should be visible where work is defined and where work is launched. Putting them only in docs would still allow accidental or ambiguous use.

**Recommended manifest fields:**
- `requires_explicit_live_opt_in: true`
- `fair_access_policy: "sec_fair_access_operator_invoked"`
- `allow_merge_blocking: false`
- `normal_user_visible: false`
- `freshness_window_seconds: 300`

**Recommended entrypoint behavior:**
- `python3 -m edgar_project.cli evaluate` continues to default to the fixture suite
- suites containing live or hybrid cases require `--allow-live` to avoid `policy_skipped`
- omission of `--allow-live` is not a failure; it remains non-merge-blocking by default

### Pattern 3: Keep Phase 06 on Current JSON Result Surfaces

**What:** Populate the new policy and degradation fields in `*_results.json`, `*_summary.json`, console output, markdown output, and example JSON files.

**When to use:** Phase 06 specifically, before the control plane exists.

**Why:** This phase is about policy truth, not about a new supported operator UI or API. The current evaluation output files are the existing inspectable seam, so the taxonomy should become explicit there first.

**Recommended result additions:**
- Per case: `degradation_class`, `policy`, `observation`
- Suite summary: `degradation_counts`
- Failure briefs: keep short `reason_short`, but also include degradation class in the raw summary data

### Pattern 4: Preserve Backward Compatibility for Fixture and Mocked Suites

**What:** Keep existing fixture and `orchestration_mocked` manifests valid without requiring new policy blocks.

**When to use:** Existing suite manifests and current offline docs.

**Why:** Fixture-based regression is the default evaluation path today. Phase 06 should harden live policy without breaking that baseline.

**Recommended compatibility rules:**
- `fixture` and `orchestration_mocked` cases validate without a `policy` block
- only `live` and `hybrid` require explicit live policy metadata
- existing result files without `degradation_class` still parse under defaults where possible

## Implementation Slices

### Slice A: Schema and Manifest Contract

Focus files:
- `edgar_project/evaluation/schemas.py`
- `edgar_project/evaluation/benchmarks/suite_smoke.json`
- `tests/test_evaluation_policy_contract.py`

Deliver:
- typed policy and observation models
- typed degradation enum
- validators that require explicit live policy metadata on `live` or `hybrid`
- backward-compatible fixture and mocked manifest parsing

### Slice B: Runner and Summary Surface

Focus files:
- `edgar_project/evaluation/runner.py`
- `edgar_project/evaluation/summary_report.py`
- `examples/evaluation_results.example.json`
- `examples/evaluation_summary.example.json`
- `tests/test_evaluation_runner_policy.py`

Deliver:
- explicit degradation-class assignment separate from lifecycle status
- runner-level policy-skip behavior
- summary counts or output sections that expose degradation routing context
- example JSON shapes that match the new result contract

### Slice C: Operator Guardrails and Docs

Focus files:
- `edgar_project/cli.py`
- `edgar_project/evaluation/scripts/run_suite.py`
- `edgar_project/evaluation/README.md`
- `README.md`
- `data/README.md`
- `tests/test_evaluate_cli_guardrails.py`

Deliver:
- explicit `--allow-live` acknowledgement
- unchanged fixture-default `evaluate` behavior
- docs that clearly state live or hybrid evaluation is operator-invoked and non-default
- CLI regressions for default and opt-in paths

## Validation Architecture

Phase 06 needs Wave 0 tests because the repo currently has almost no direct evaluation policy coverage.

**Recommended quick command:**
```bash
python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluate_cli_guardrails.py -q --tb=short
```

**Recommended full command:**
```bash
python3 -m pytest tests/ -q --tb=short
```

**Required new tests:**
- `tests/test_evaluation_policy_contract.py`
  - live or hybrid manifests require explicit policy metadata
  - fixture and mocked manifests remain backward compatible
  - result schemas keep `status` and `degradation_class` separate
- `tests/test_evaluation_runner_policy.py`
  - policy-skipped, product-regression, stale-source, and upstream-degraded classification helpers behave deterministically
  - suite summaries expose degradation counts
  - markdown or console summaries include degradation routing context
- `tests/test_evaluate_cli_guardrails.py`
  - `evaluate` defaults to the fixture suite
  - `--allow-live` is required to opt into live or hybrid suites
  - omission of `--allow-live` yields policy-skipped results instead of merge-blocking failures

**Wave 0 note:** All three test files are missing today, so the plan set must seed them as it goes.

## Pitfalls and Boundaries

- Do not turn Phase 06 into full live execution support. That belongs later when runs are linked to canonical `AnalysisRun` records.
- Do not add a new evaluation API or UI here. The supported control plane is Phase 09.
- Do not flatten all non-pass results into `failed` or a free-form text `message`; that would undo the requirement this phase exists to provide.
- Do not change the default `evaluate` suite away from fixtures; that would blur policy boundaries immediately.
- Do not make live acknowledgment flags imply merge blocking or ordinary user visibility.

## Recommended Plan Shape

Phase 06 should be planned as **3 sequential plans**:

1. **Schema contract** — define policy, observation, and degradation fields plus live-manifest validation
2. **Runner/result surfacing** — emit explicit degradation and observation context through result files and summaries
3. **CLI/docs guardrails** — keep live use explicit and non-default at the operator entrypoints and in docs

This sequence keeps the implementation incremental and testable. Each plan builds on the prior one, and no plan needs to widen scope into the later control-plane or child-run phases.

## Sources

### Primary
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md`
- `.planning/research/SUMMARY.md`
- `.planning/research/FEATURES.md`
- `.planning/research/PITFALLS.md`
- `edgar_project/evaluation/README.md`
- `edgar_project/evaluation/schemas.py`
- `edgar_project/evaluation/runner.py`
- `edgar_project/evaluation/summary_report.py`
- `edgar_project/evaluation/benchmarks/suite_smoke.json`
- `edgar_project/cli.py`
- `edgar_project/evaluation/scripts/run_suite.py`
- `README.md`
- `data/README.md`
- `examples/evaluation_results.example.json`
- `examples/evaluation_summary.example.json`

### Secondary
- `.planning/phases/03-secure-defaults/03-CONTEXT.md`
- `.planning/phases/05-storage-and-ops/05-CONTEXT.md`
- `backend/models/evaluation_run.py`
- `backend/auth/resource_access.py`
- `backend/services/artifact_service.py`

---
*Research completed: 2026-04-18*
*Ready for planning: yes*
