---
phase: 09-evaluation-control-plane
plan: 03
type: execute
wave: 3
depends_on:
  - "09-02"
files_modified:
  - backend/api/routes/evaluations.py
  - backend/schemas/evaluation_run.py
  - backend/schemas/evaluation_case_result.py
  - edgar_project/cli.py
  - edgar_project/evaluation/README.md
  - README.md
  - tests/test_evaluation_control_plane_api.py
  - tests/test_evaluation_control_plane_service.py
  - tests/test_evaluation_cli_compat.py
autonomous: true
requirements:
  - VALID-01
  - EVAL-01
must_haves:
  truths:
    - "Operators can reopen stored evaluation history through dedicated case-result routes instead of reparsing `results_json` blobs."
    - "The CLI keeps a compatibility path, but supported suite launches now center on `--suite-id` and the shared control-plane service rather than arbitrary manifest paths."
    - "Docs explicitly distinguish the API-backed supported workflow from raw path-based developer tooling."
  artifacts:
    - path: backend/api/routes/evaluations.py
      provides: "Stored case-review routes with project-scoped filters and detail views"
    - path: edgar_project/cli.py
      provides: "CLI compatibility path that resolves supported suite IDs and can delegate into persisted control-plane execution"
    - path: tests/test_evaluation_cli_compat.py
      provides: "CLI regressions for supported suite IDs and service delegation"
    - path: tests/test_evaluation_control_plane_api.py
      provides: "API regressions for reopening case-level evaluation history"
  key_links:
    - from: backend/api/routes/evaluations.py
      to: backend/schemas/evaluation_case_result.py
      via: "case list/detail routes return explicit stored case-result resources rather than one aggregate blob"
      pattern: "/cases|degradation_class|observation_json"
    - from: edgar_project/cli.py
      to: edgar_project/evaluation/catalog.py
      via: "the compatibility path resolves supported suite IDs instead of treating raw file paths as the normal workflow"
      pattern: "--suite-id|suite_fixtures_v1"
    - from: tests/test_evaluation_cli_compat.py
      to: edgar_project/cli.py
      via: "tests lock parser behavior and service delegation for persisted compatibility mode"
      pattern: "--project-id|EvaluationControlPlaneService|--suite"
---

<objective>
Finish the review surface, CLI compatibility path, and docs so evaluation history is reopenable and the supported workflow is clearly API-backed.

Purpose: satisfy the operator-facing review and compatibility half of Phase 09.
Output: case review routes, supported `--suite-id` CLI compatibility, docs, and regression coverage.
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
@.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
@.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
@.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
@.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-PLAN.md
@backend/api/routes/evaluations.py
@backend/schemas/evaluation_run.py
@backend/schemas/evaluation_case_result.py
@edgar_project/evaluation/catalog.py
@edgar_project/cli.py
@edgar_project/evaluation/README.md
@README.md

<interfaces>
From `backend/api/routes/evaluations.py`:
```python
@router.get("", ...)
@router.post("", ...)
@router.get("/{evaluation_run_id}", ...)
@router.post("/{evaluation_run_id}/start", ...)
```

From `edgar_project/cli.py`:
```python
def _cmd_evaluate(args: argparse.Namespace) -> int: ...
def build_parser() -> argparse.ArgumentParser: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add explicit case-review routes for stored evaluation history</name>
  <files>backend/api/routes/evaluations.py
backend/schemas/evaluation_run.py
backend/schemas/evaluation_case_result.py
tests/test_evaluation_control_plane_api.py
tests/test_evaluation_control_plane_service.py</files>
  <read_first>.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-PLAN.md
backend/api/routes/evaluations.py
backend/schemas/evaluation_run.py
backend/schemas/evaluation_case_result.py
tests/test_evaluation_control_plane_api.py
tests/test_evaluation_control_plane_service.py</read_first>
  <behavior>
    - Evaluation history reopens as a summary aggregate plus explicit per-case resources, not one opaque `results_json` blob.
    - Case review stays project-scoped and supports bounded filtering by status, input mode, and degradation class.
    - Stored policy and observation metadata are readable from case-review responses without requiring privileged raw payload expansion.
  </behavior>
  <action>Extend `backend/schemas/evaluation_case_result.py` with explicit list/detail response models if needed, and extend `backend/schemas/evaluation_run.py` so evaluation detail returns `case_count`, status counts, or other summary fields without forcing clients to parse `results_json`. Add `GET /v1/evaluations/{evaluation_run_id}/cases` and `GET /v1/evaluations/{evaluation_run_id}/cases/{case_id}` to `backend/api/routes/evaluations.py`. The case-list route must support query parameters `status`, `input_mode`, and `degradation_class`, must require ownership through the parent evaluation run, and must return stored `policy_json` and `observation_json` fields for each case record. Extend `tests/test_evaluation_control_plane_api.py` so it covers listing stored cases, filtering by `policy_skipped` and `fixture`, reopening one case by `case_id`, and returning `404` for non-owned evaluation history. Extend `tests/test_evaluation_control_plane_service.py` if needed so API expectations match the stored row shape.</action>
  <acceptance_criteria>`backend/api/routes/evaluations.py` contains `@router.get("/{evaluation_run_id}/cases"`.
`backend/api/routes/evaluations.py` contains `@router.get("/{evaluation_run_id}/cases/{case_id}"`.
`backend/api/routes/evaluations.py` contains `degradation_class`.
`backend/api/routes/evaluations.py` contains `input_mode`.
`backend/schemas/evaluation_case_result.py` contains a read model for stored case results.
`backend/schemas/evaluation_run.py` contains `case_count`.
`tests/test_evaluation_control_plane_api.py` contains `/cases`.
`tests/test_evaluation_control_plane_api.py` contains `policy_skipped`.
`tests/test_evaluation_control_plane_api.py` contains `fixture`.
`tests/test_evaluation_control_plane_api.py` asserts non-owned evaluation history returns `404`.
`python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py -q --tb=short</automated>
  </verify>
  <done>Operators can now reopen evaluation history through dedicated case-level resources instead of reparsing aggregate result blobs.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add supported `--suite-id` CLI compatibility and document the API-backed workflow</name>
  <files>edgar_project/cli.py
edgar_project/evaluation/README.md
README.md
tests/test_evaluation_cli_compat.py</files>
  <read_first>.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
edgar_project/evaluation/catalog.py
edgar_project/cli.py
edgar_project/evaluation/README.md
README.md
backend/services/evaluation_control_plane_service.py</read_first>
  <behavior>
    - The supported CLI path resolves curated suite IDs instead of requiring a raw manifest path.
    - API-backed persisted evaluation remains the primary workflow; raw file-path execution stays an explicit compatibility escape hatch for developer use only.
    - Docs make it clear that supported evaluation runs are API-backed and project-scoped, while `--suite` remains a lower-level dev tool.
  </behavior>
  <action>Update `edgar_project/cli.py` so `evaluate` accepts `--suite-id` with default `suite_fixtures_v1`, keeps `--suite` only as an explicit developer fallback, and adds `--project-id` as the switch that enables persisted control-plane execution. When `--project-id` is present, the command must resolve the suite through `edgar_project.evaluation.catalog`, instantiate `EvaluationControlPlaneService`, create or start the persisted evaluation run through the same service path as the API, and print the resulting `evaluation_run_id` plus terminal status. When `--project-id` is absent, the command may retain the legacy local JSON-output behavior, but `--suite-id` must still resolve through the catalog rather than forcing a file path. Add `tests/test_evaluation_cli_compat.py` to cover parser defaults for `--suite-id`, unknown suite-id rejection, `--suite` fallback retention, and service delegation when `--project-id` is supplied. Update `edgar_project/evaluation/README.md` and `README.md` so they explicitly say the supported workflow is API-backed and project-scoped, the CLI is a compatibility path, and `--suite` is a developer fallback rather than the primary control-plane contract.</action>
  <acceptance_criteria>`edgar_project/cli.py` contains `--suite-id`.
`edgar_project/cli.py` contains `suite_fixtures_v1`.
`edgar_project/cli.py` contains `--project-id`.
`edgar_project/cli.py` still contains `--suite`.
`edgar_project/cli.py` contains `EvaluationControlPlaneService`.
`tests/test_evaluation_cli_compat.py` exists.
`tests/test_evaluation_cli_compat.py` contains `--suite-id`.
`tests/test_evaluation_cli_compat.py` contains `--project-id`.
`tests/test_evaluation_cli_compat.py` contains `suite_fixtures_v1`.
`edgar_project/evaluation/README.md` contains `API-backed`.
`edgar_project/evaluation/README.md` contains `compatibility path`.
`README.md` contains `--suite-id`.
`README.md` contains `developer fallback`.
`python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py -q --tb=short</automated>
  </verify>
  <done>The CLI and docs now reinforce the supported API-backed workflow while keeping a narrower dev-only fallback for raw suite paths.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py -q --tb=short` after each task so case review and CLI compatibility stay aligned with the persisted control-plane contract.
</verification>

<success_criteria>
Phase 09 is fully planned once evaluation history is reopenable through case resources, the CLI resolves supported suite IDs through the same control-plane contract, and the docs no longer present raw manifest paths as the primary workflow.
</success_criteria>

<output>
After completion, create `.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md`
</output>
