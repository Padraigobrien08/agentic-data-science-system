---
phase: 03-secure-defaults
plan: 03
type: execute
wave: 3
depends_on:
  - 03-01
  - 03-02
files_modified:
  - .env.example
  - docker-compose.yml
  - docs/auth-api.md
  - docs/local-stack.md
  - docs/artifact-delivery.md
  - frontend/src/actions/auth.ts
  - frontend/src/app/register/page.tsx
  - frontend/src/lib/api/types.ts
  - tests/test_secure_defaults_api.py
autonomous: true
requirements:
  - SECU-01
  - SECU-02
  - SECU-03
must_haves:
  truths:
    - "The documented local stack no longer ships a baked-in JWT secret or default-open registration."
    - "Operators have explicit instructions for bootstrap-admin creation and ops-token access."
    - "User-facing registration guidance matches the new closed-by-default backend behavior."
  artifacts:
    - path: docker-compose.yml
      provides: "Secure local-stack env contract without insecure secret fallbacks"
    - path: docs/auth-api.md
      provides: "Bootstrap-admin, registration-defaults, and ops-token usage guide"
    - path: frontend/src/actions/auth.ts
      provides: "User-facing registration-disabled guidance aligned with the new backend defaults"
  key_links:
    - from: .env.example
      to: docker-compose.yml
      via: "required env names match compose substitutions exactly"
      pattern: "EDGAR_BACKEND_JWT_SECRET|EDGAR_BACKEND_OPS_API_TOKEN|EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN"
    - from: docs/auth-api.md
      to: backend/api/routes/auth.py
      via: "bootstrap curl examples and registration posture reflect actual route contract"
      pattern: "/v1/auth/bootstrap|Registration is disabled"
    - from: frontend/src/actions/auth.ts
      to: backend/api/routes/auth.py
      via: "disabled-registration guidance maps the backend 403 detail into operator-facing copy"
      pattern: "Registration is disabled"
---

<objective>
Align docs, compose defaults, and user-facing guidance with the new secure-default backend contract, then lock the phase with a single regression command.

Purpose: finish Phase 03 by removing insecure deployment examples, documenting bootstrap and ops-token usage, and making the registration UX truthful under the new default posture.
Output: secure local-stack env examples, updated operator docs, and registration guidance that matches the hardened backend.
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
@.planning/phases/03-secure-defaults/03-VALIDATION.md
@.planning/phases/03-secure-defaults/03-secure-defaults-01-PLAN.md
@.planning/phases/03-secure-defaults/03-secure-defaults-02-PLAN.md
@.env.example
@docker-compose.yml
@docs/auth-api.md
@docs/local-stack.md
@docs/artifact-delivery.md
@frontend/src/actions/auth.ts
@frontend/src/app/register/page.tsx
@frontend/src/lib/api/types.ts
@tests/test_secure_defaults_api.py

<interfaces>
From `frontend/src/actions/auth.ts`:
```ts
export async function registerAction(
  _prev: RegisterState,
  formData: FormData,
): Promise<RegisterState>
```

From `docker-compose.yml`:
```yaml
x-backend-env:
  EDGAR_BACKEND_JWT_SECRET: ...
  EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION: ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove insecure stack examples and document the secure bootstrap contract</name>
  <files>.env.example, docker-compose.yml, docs/auth-api.md, docs/local-stack.md, docs/artifact-delivery.md</files>
  <read_first>.planning/phases/03-secure-defaults/03-CONTEXT.md
.planning/phases/03-secure-defaults/03-RESEARCH.md
.planning/phases/03-secure-defaults/03-VALIDATION.md
.env.example
docker-compose.yml
docs/auth-api.md
docs/local-stack.md
docs/artifact-delivery.md</read_first>
  <behavior>
    - `.env.example` includes the exact secure-default env vars required by the hardened backend.
    - `docker-compose.yml` no longer bakes in an insecure JWT fallback or default-open registration.
    - Docs show the explicit bootstrap-admin flow, ops-token usage for `/metrics` and `/v1/worker/health`, and admin-only raw payload/meta access.
  </behavior>
  <action>Update `.env.example` to define exact placeholder entries for `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_OPS_API_TOKEN`, `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`, `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false`, and `EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=false`. In `docker-compose.yml`, remove the baked-in dev JWT fallback and default-open registration fallback. Use exact compose substitutions `${EDGAR_BACKEND_JWT_SECRET:?set in .env}`, `${EDGAR_BACKEND_OPS_API_TOKEN:?set in .env}`, `${EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN:?set in .env}`, and `${EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION:-false}` so the documented stack fails early when required secrets are missing. Update `docs/auth-api.md` with a `POST /v1/auth/bootstrap` curl example using `X-EDGAR-Bootstrap-Token`, explain that registration is closed by default, and document that raw payload/meta expansions are admin-only. Update `docs/local-stack.md` so the quick-start section requires copying `.env.example`, setting the JWT/ops/bootstrap tokens, and using the ops bearer token for `/metrics` and `/v1/worker/health`. Update `docs/artifact-delivery.md` so artifact metadata examples no longer mention absolute `source_path` and instead describe sanitized provenance keys.</action>
  <acceptance_criteria>`.env.example` contains `EDGAR_BACKEND_OPS_API_TOKEN=`.
`.env.example` contains `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN=`.
`.env.example` contains `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false`.
`docker-compose.yml` contains `${EDGAR_BACKEND_JWT_SECRET:?set in .env}`.
`docker-compose.yml` contains `${EDGAR_BACKEND_OPS_API_TOKEN:?set in .env}`.
`docker-compose.yml` contains `${EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN:?set in .env}`.
`docs/auth-api.md` documents `/v1/auth/bootstrap`.
`docs/local-stack.md` tells operators to copy `.env.example` before `docker compose up`.
`docs/artifact-delivery.md` no longer documents absolute `source_path` metadata.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q</automated>
  </verify>
  <done>The documented stack and operator instructions are aligned with the secure-default backend contract instead of preserving insecure fallbacks.</done>
</task>

<task type="auto">
  <name>Task 2: Make registration UX truthful and lock the phase regression sweep</name>
  <files>frontend/src/actions/auth.ts, frontend/src/app/register/page.tsx, frontend/src/lib/api/types.ts, tests/test_secure_defaults_api.py</files>
  <read_first>.planning/phases/03-secure-defaults/03-CONTEXT.md
.planning/phases/03-secure-defaults/03-RESEARCH.md
frontend/src/actions/auth.ts
frontend/src/app/register/page.tsx
frontend/src/lib/api/types.ts
tests/test_secure_defaults_api.py</read_first>
  <behavior>
    - The register page tells users registration is usually disabled by default and points to the operator/bootstrap path.
    - The server action turns backend `403 Registration is disabled` into explicit operator guidance instead of a generic raw error string.
    - Frontend API types match the backend `UserRead` shape if `is_admin` is now returned.
    - A single backend regression command covers settings, bootstrap, ops auth, raw expansion gating, and sanitized artifact provenance.
  </behavior>
  <action>Update `frontend/src/app/register/page.tsx` so the copy says registration is disabled by default on secure deployments and references the bootstrap-admin path instead of implying open registration is the normal case. In `frontend/src/actions/auth.ts`, detect the exact backend detail string `Registration is disabled` and rewrite it to the user-facing message `Registration is disabled. Ask an operator to use the bootstrap admin token or explicitly enable open registration.` Keep all other backend errors unchanged. If Plan 03-01 added `is_admin` to `UserRead`, update `frontend/src/lib/api/types.ts` so `CurrentUser` includes `is_admin: boolean`. Expand `tests/test_secure_defaults_api.py` so the phase-wide backend command exercises bootstrap login, registration-disabled behavior, ops-token protection, admin-only payload/meta access, and sanitized artifact provenance expectations in one place where reasonable.</action>
  <acceptance_criteria>`frontend/src/app/register/page.tsx` says registration is disabled by default.
`frontend/src/actions/auth.ts` contains the exact user-facing string `Registration is disabled. Ask an operator to use the bootstrap admin token or explicitly enable open registration.`.
`frontend/src/lib/api/types.ts` contains `is_admin: boolean` if the backend now returns that field.
`tests/test_secure_defaults_api.py` covers bootstrap login, ops-token auth, and admin-only raw expansion behavior.
The Phase 03 quick regression command exits successfully after the plan is executed.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q</automated>
  </verify>
  <done>Phase 03 finishes with truthful operator docs and registration UX that matches the secure-default backend contract.</done>
</task>

</tasks>

<verification>
Use the same backend regression command after both tasks so docs, UX guidance, and the hardened backend contract stay aligned through one repeatable phase gate.
</verification>

<success_criteria>
Phase 03 is execution-ready when the local-stack docs no longer encode insecure defaults, bootstrap and ops-token guidance are explicit, and the registration UX no longer assumes open registration is normal.
</success_criteria>

<output>
After completion, create `.planning/phases/03-secure-defaults/03-secure-defaults-03-SUMMARY.md`
</output>
