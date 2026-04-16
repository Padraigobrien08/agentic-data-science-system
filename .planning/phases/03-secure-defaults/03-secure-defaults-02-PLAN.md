---
phase: 03-secure-defaults
plan: 02
type: execute
wave: 2
depends_on:
  - 03-01
files_modified:
  - backend/config/settings.py
  - backend/api/auth_deps.py
  - backend/api/routes/metrics.py
  - backend/api/routes/health.py
  - backend/api/routes/runs.py
  - backend/api/routes/artifacts.py
  - backend/services/artifact_service.py
  - tests/conftest.py
  - tests/test_backend_health.py
  - tests/test_secure_defaults_api.py
  - tests/test_artifact_storage.py
  - tests/test_run_isolation_execution_service.py
autonomous: true
requirements:
  - SECU-03
must_haves:
  truths:
    - "`/metrics` and `/v1/worker/health` reject requests without the dedicated ops token."
    - "Raw payload or meta expansions on owner routes require an admin user instead of any resource owner."
    - "Artifact provenance no longer persists absolute filesystem `source_path` values."
  artifacts:
    - path: backend/api/auth_deps.py
      provides: "Dedicated ops-token dependency plus admin-only raw expansion helper"
    - path: backend/services/artifact_service.py
      provides: "Sanitized artifact provenance persistence"
    - path: tests/test_secure_defaults_api.py
      provides: "Ops-token and admin-only raw access regressions"
  key_links:
    - from: backend/api/routes/metrics.py
      to: backend/api/auth_deps.py
      via: "ops-only dependency protects public infra route without reusing user bearer auth"
      pattern: "require_ops_token|get_ops_token"
    - from: backend/api/routes/runs.py
      to: backend/api/auth_deps.py
      via: "summary-first owner routes require admin capability before honoring include_payloads"
      pattern: "include_payloads|require_admin_debug_access"
    - from: backend/services/artifact_service.py
      to: tests/test_run_isolation_execution_service.py
      via: "sanitized provenance replaces absolute source_path in persisted artifact metadata"
      pattern: "source_filename|source_workspace_relative_path"
---

<objective>
Protect operational endpoints and tighten raw payload / artifact provenance exposure without changing the existing summary-first route shapes.

Purpose: satisfy SECU-03 by adding a dedicated ops credential, admin-only raw expansions on owner routes, and sanitized persisted artifact provenance.
Output: ops-token-protected `/metrics` and `/v1/worker/health`, admin-gated payload/meta flags, and artifact metadata without absolute filesystem paths.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-secure-defaults/03-CONTEXT.md
@.planning/phases/03-secure-defaults/03-RESEARCH.md
@.planning/phases/03-secure-defaults/03-secure-defaults-01-PLAN.md
@backend/config/settings.py
@backend/api/auth_deps.py
@backend/api/routes/metrics.py
@backend/api/routes/health.py
@backend/api/routes/runs.py
@backend/api/routes/artifacts.py
@backend/services/artifact_service.py
@tests/conftest.py
@tests/test_backend_health.py
@tests/test_artifact_storage.py
@tests/test_run_isolation_execution_service.py

<interfaces>
From `backend/api/routes/metrics.py`:
```python
@router.get("/metrics")
def prometheus_metrics(db: DbSession) -> Response
```

From `backend/api/routes/health.py`:
```python
@router.get("/worker/health", response_model=WorkerHealthResponse)
def worker_health(db: DbSession) -> WorkerHealthResponse
```

From `backend/api/routes/runs.py`:
```python
@router.get("/{run_id}")
def get_run(..., include_payloads: bool = Query(False), ...)

@router.get("/{run_id}/model-calls")
def list_run_model_calls(..., include_payloads: bool = Query(False))
```

From `backend/api/routes/artifacts.py`:
```python
@router.get("/{artifact_id}")
def get_artifact(..., include_meta: bool = Query(False))
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Protect ops-only routes with a dedicated bearer token</name>
  <files>backend/config/settings.py, backend/api/auth_deps.py, backend/api/routes/metrics.py, backend/api/routes/health.py, tests/conftest.py, tests/test_backend_health.py, tests/test_secure_defaults_api.py</files>
  <read_first>.planning/phases/03-secure-defaults/03-CONTEXT.md
.planning/phases/03-secure-defaults/03-RESEARCH.md
backend/config/settings.py
backend/api/auth_deps.py
backend/api/routes/metrics.py
backend/api/routes/health.py
tests/conftest.py
tests/test_backend_health.py</read_first>
  <behavior>
    - The app requires a non-empty ops API token in normal settings.
    - `GET /metrics` returns `401` without a valid ops token and `200` with it.
    - `GET /v1/worker/health` returns `401` without a valid ops token and `200` with it.
    - `GET /health` and `GET /v1/ready` remain public.
  </behavior>
  <action>Add `ops_api_token: SecretStr | None = None` to `backend/config/settings.py` and extend startup validation so a non-empty token is required alongside the secure-default app configuration. In `tests/conftest.py`, set `EDGAR_BACKEND_OPS_API_TOKEN=pytest-ops-token` before backend settings are first imported. In `backend/api/auth_deps.py`, add a dedicated bearer parser for ops routes plus `get_ops_token()` / `require_ops_token()` that validates `Authorization: Bearer <token>` against `settings.ops_api_token`, returning `401` with `WWW-Authenticate: Bearer` on missing or mismatched credentials. Apply that dependency to `backend/api/routes/metrics.py` and `backend/api/routes/health.py::worker_health`, but leave `/health` and `/ready` untouched. Add focused regressions in `tests/test_backend_health.py` and `tests/test_secure_defaults_api.py` so they prove `/metrics` and `/v1/worker/health` reject unauthenticated requests, accept the exact pytest ops token header, and do not change the public behavior of `/health` or `/ready`.</action>
  <acceptance_criteria>`backend/config/settings.py` defines `ops_api_token`.
`backend/config/settings.py` validates that `ops_api_token` is non-empty under the secure-default settings contract.
`tests/conftest.py` sets `EDGAR_BACKEND_OPS_API_TOKEN`.
`backend/api/auth_deps.py` defines `get_ops_token` or `require_ops_token`.
`backend/api/routes/metrics.py` depends on the ops-token dependency.
`backend/api/routes/health.py` protects `worker_health` with the ops-token dependency while leaving `health` and `readiness` public.
`tests/test_backend_health.py` asserts `401` without ops auth and `200` with `Authorization: Bearer pytest-ops-token` for both `/metrics` and `/v1/worker/health`.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_backend_health.py tests/test_secure_defaults_api.py -q</automated>
  </verify>
  <done>Operational telemetry routes are no longer public and require a dedicated ops credential distinct from normal user auth.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Gate raw expansions to admins and sanitize persisted artifact provenance</name>
  <files>backend/api/auth_deps.py, backend/api/routes/runs.py, backend/api/routes/artifacts.py, backend/services/artifact_service.py, tests/test_secure_defaults_api.py, tests/test_artifact_storage.py, tests/test_run_isolation_execution_service.py</files>
  <read_first>.planning/phases/03-secure-defaults/03-CONTEXT.md
.planning/phases/03-secure-defaults/03-RESEARCH.md
backend/api/auth_deps.py
backend/api/routes/runs.py
backend/api/routes/artifacts.py
backend/services/artifact_service.py
tests/test_artifact_storage.py
tests/test_run_isolation_execution_service.py
tests/test_sprint3_transparency_api.py</read_first>
  <behavior>
    - Non-admin owners get `403` when they request `include_payloads=true` or `include_meta=true`.
    - Admin users can still retrieve the raw payload/meta views through the existing query flags.
    - `ArtifactService.ingest_pipeline_file()` no longer stores `meta_json["source_path"]`.
    - Run-scoped artifact provenance still remains useful through sanitized keys such as basename and workspace-relative path.
  </behavior>
  <action>Add `require_admin_debug_access(user, *, feature: str)` to `backend/api/auth_deps.py` so routes can reject non-admin raw expansions with `HTTP 403`. In `backend/api/routes/runs.py`, before honoring `include_payloads=true` on run detail, run steps, or model-call listing, require `user.is_admin`. In `backend/api/routes/artifacts.py`, before honoring `include_meta=true`, require `user.is_admin`. Keep the default summary responses unchanged. In `backend/services/artifact_service.py::ingest_pipeline_file()`, replace the absolute-path metadata merge with exact keys `source_filename` and, when the source file is under the run workspace root, `source_workspace_relative_path` relative to that run workspace (for example `artifacts/report.md`); do not persist `source_path`. Update `tests/test_secure_defaults_api.py` first so it proves a non-admin owner gets `403` on `include_payloads=true` and `include_meta=true`, while an admin user can request the same expansions successfully. Update `tests/test_artifact_storage.py` and `tests/test_run_isolation_execution_service.py` so they assert `source_path` is absent and the sanitized keys are present instead.</action>
  <acceptance_criteria>`backend/api/auth_deps.py` defines `require_admin_debug_access`.
`backend/api/routes/runs.py` checks admin capability before returning raw payload fields when `include_payloads` is true.
`backend/api/routes/artifacts.py` checks admin capability before returning `meta_json` when `include_meta` is true.
`backend/services/artifact_service.py` no longer writes `source_path` into artifact metadata.
`backend/services/artifact_service.py` writes `source_filename`.
`tests/test_secure_defaults_api.py` asserts non-admin `403` and admin `200` for raw expansion flags.
`tests/test_artifact_storage.py` and `tests/test_run_isolation_execution_service.py` assert `source_path` is absent from persisted artifact metadata.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_secure_defaults_api.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q</automated>
  </verify>
  <done>Raw payloads and artifact meta expansions are privileged rather than owner-default, and persisted artifact provenance no longer leaks absolute filesystem paths.</done>
</task>

</tasks>

<verification>
Run the ops-route tests after Task 1, then rerun the combined ops/auth/artifact regressions after Task 2 so endpoint protection and sanitized persistence stay aligned.
</verification>

<success_criteria>
Phase 03 moves past its largest exposure seams when ops endpoints require a dedicated credential, raw payload/meta expansions require admin privilege, and artifact metadata no longer persists absolute filesystem paths.
</success_criteria>

<output>
After completion, create `.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md`
</output>
