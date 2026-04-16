---
phase: 03-secure-defaults
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/008_user_admin_bootstrap.py
  - backend/models/user.py
  - backend/schemas/user.py
  - backend/schemas/auth.py
  - backend/services/user_service.py
  - backend/config/settings.py
  - backend/api/routes/auth.py
  - tests/conftest.py
  - tests/api_auth.py
  - tests/test_auth_api.py
  - tests/test_secure_defaults_settings.py
autonomous: true
requirements:
  - SECU-01
  - SECU-02
must_haves:
  truths:
    - "Startup fails when the built-in JWT secret is active unless the explicit insecure-dev override is enabled."
    - "Self-service registration is disabled by default instead of default-open."
    - "Operators can create the first admin user through an explicit bootstrap route rather than relying on open registration."
  artifacts:
    - path: backend/config/settings.py
      provides: "Fail-fast security-default settings contract for JWT secret, onboarding posture, and bootstrap token"
    - path: backend/api/routes/auth.py
      provides: "Closed-by-default registration and explicit bootstrap-admin route"
    - path: tests/test_secure_defaults_settings.py
      provides: "Executable regression coverage for startup validation and default registration posture"
  key_links:
    - from: backend/config/settings.py
      to: backend/api/routes/auth.py
      via: "bootstrap token and allow_open_registration settings drive route behavior directly"
      pattern: "bootstrap_admin_token|allow_open_registration"
    - from: backend/models/user.py
      to: backend/schemas/user.py
      via: "new admin capability is persisted and returned through auth routes"
      pattern: "is_admin"
    - from: tests/test_auth_api.py
      to: backend/api/routes/auth.py
      via: "registration-disabled and bootstrap-admin regressions lock the new onboarding contract"
      pattern: "bootstrap|Registration is disabled"
---

<objective>
Enforce secure startup configuration and replace default-open registration with an explicit bootstrap-admin path.

Purpose: satisfy SECU-01 and SECU-02 before later plans build privileged payload and ops-surface protections on top of the new security posture.
Output: a settings contract that rejects the built-in JWT secret, default-closed registration, and a bootstrap-admin route backed by persisted `is_admin`.
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
@.planning/phases/03-secure-defaults/03-CONTEXT.md
@.planning/phases/03-secure-defaults/03-RESEARCH.md
@backend/config/settings.py
@backend/models/user.py
@backend/schemas/user.py
@backend/schemas/auth.py
@backend/services/user_service.py
@backend/api/routes/auth.py
@tests/conftest.py
@tests/api_auth.py
@tests/test_auth_api.py

<interfaces>
From `backend/config/settings.py`:
```python
class Settings(BaseSettings):
    jwt_secret: SecretStr
    allow_open_registration: bool
```

From `backend/api/routes/auth.py`:
```python
@router.post("/register", response_model=UserRead, status_code=201)
def register(body: AuthRegisterBody, db: DbSession) -> User
```

From `backend/services/user_service.py`:
```python
def create_with_password(
    self,
    *,
    email: str,
    hashed_password: str,
    display_name: str | None,
) -> User
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add secure settings validation and persisted admin capability</name>
  <files>alembic/versions/008_user_admin_bootstrap.py, backend/models/user.py, backend/schemas/user.py, backend/services/user_service.py, backend/config/settings.py, tests/conftest.py, tests/test_secure_defaults_settings.py</files>
  <read_first>.planning/phases/03-secure-defaults/03-CONTEXT.md
.planning/phases/03-secure-defaults/03-RESEARCH.md
backend/config/settings.py
backend/models/user.py
backend/schemas/user.py
backend/services/user_service.py
tests/conftest.py
tests/test_auth_api.py</read_first>
  <behavior>
    - `allow_open_registration` defaults to `False` instead of `True`.
    - The literal built-in JWT secret string is rejected unless `allow_insecure_dev_jwt` is explicitly enabled.
    - When registration is closed, a non-empty bootstrap token is required so the app still has an explicit first-user path.
    - Users persist `is_admin`, and `UserRead` exposes that field.
  </behavior>
  <action>Add a settings constant for the existing built-in JWT secret value and introduce exact fields `allow_insecure_dev_jwt: bool = False` and `bootstrap_admin_token: SecretStr | None = None` in `backend/config/settings.py`. Change `allow_open_registration` default to `False`. In `_production_sanity()`, keep the existing minimum-length check, then add an equality check that raises a `ValueError` mentioning `EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true` whenever `jwt_secret` still equals the built-in dev secret and `allow_insecure_dev_jwt` is false. In the same validator, require a non-empty `bootstrap_admin_token` whenever `allow_open_registration` is false. Add Alembic revision `alembic/versions/008_user_admin_bootstrap.py` that adds `users.is_admin BOOLEAN NOT NULL DEFAULT false`, then update `backend/models/user.py`, `backend/schemas/user.py`, and `backend/services/user_service.py` so `User` persists `is_admin`, `UserRead` returns `is_admin`, and `create_with_password()` accepts an `is_admin: bool = False` argument. Update `tests/conftest.py` so the default test environment sets `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=true` and `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN=pytest-bootstrap-token`, preserving broad legacy helpers while new secure-default tests exercise the stricter config explicitly. Create `tests/test_secure_defaults_settings.py` first with direct `Settings(...)` cases for: built-in secret rejected by default, built-in secret allowed only with `allow_insecure_dev_jwt=True`, default `allow_open_registration is False`, and closed registration without a bootstrap token raising a clear error.</action>
  <acceptance_criteria>`backend/config/settings.py` defines `allow_insecure_dev_jwt`.
`backend/config/settings.py` defines `bootstrap_admin_token`.
`backend/config/settings.py` sets `allow_open_registration` default to `False`.
`backend/config/settings.py` contains a validator branch that rejects the built-in JWT secret by exact value unless `allow_insecure_dev_jwt` is true.
`alembic/versions/008_user_admin_bootstrap.py` exists and adds `users.is_admin`.
`backend/models/user.py`, `backend/schemas/user.py`, and `backend/services/user_service.py` all contain `is_admin`.
`tests/test_secure_defaults_settings.py` asserts the built-in secret rejection path and the closed-registration bootstrap-token requirement.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_secure_defaults_settings.py -q</automated>
  </verify>
  <done>The app has a fail-fast secure-default settings contract and persisted admin capability without breaking the broad legacy test environment.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace default-open onboarding with explicit bootstrap-admin flow</name>
  <files>backend/schemas/auth.py, backend/api/routes/auth.py, tests/api_auth.py, tests/test_auth_api.py</files>
  <read_first>.planning/phases/03-secure-defaults/03-CONTEXT.md
.planning/phases/03-secure-defaults/03-RESEARCH.md
backend/schemas/auth.py
backend/api/routes/auth.py
backend/services/user_service.py
tests/api_auth.py
tests/test_auth_api.py</read_first>
  <behavior>
    - `POST /v1/auth/register` returns `403` under the secure default.
    - `POST /v1/auth/bootstrap` creates exactly the first admin user when the bootstrap token matches and no admin exists yet.
    - `GET /v1/auth/me` includes `is_admin`.
    - A second bootstrap attempt fails instead of creating another implicit operator account.
  </behavior>
  <action>Add `AuthBootstrapBody` to `backend/schemas/auth.py` with the same email/password/display-name fields as registration. In `backend/api/routes/auth.py`, leave `/login` and `/me` in place, keep `/register` public, but make it return `HTTP 403` with the exact detail `Registration is disabled` whenever `allow_open_registration` is false. Add a new public `POST /v1/auth/bootstrap` route that reads `X-EDGAR-Bootstrap-Token`, compares it to `settings.bootstrap_admin_token`, returns `401` on missing or mismatched token, returns `503` with a clear detail if bootstrap is not configured, returns `409` with the exact detail `Bootstrap already completed` if any `User.is_admin` already exists, and otherwise creates the first admin user with `is_admin=True`. Reuse `UserService.create_with_password(...)` for persistence and keep login semantics unchanged. Update `tests/api_auth.py` with a `bootstrap_admin_and_headers()` helper that calls `/v1/auth/bootstrap`, logs in, and creates a project. Extend `tests/test_auth_api.py` with concrete cases that clear the settings cache and exercise the secure-default route behavior: registration-disabled returns `403`, bootstrap succeeds and `/v1/auth/me` returns `"is_admin": true`, and a second bootstrap attempt returns `409` with `Bootstrap already completed`.</action>
  <acceptance_criteria>`backend/schemas/auth.py` defines `AuthBootstrapBody`.
`backend/api/routes/auth.py` defines `@router.post("/bootstrap"`.
`backend/api/routes/auth.py` returns `Registration is disabled` when `allow_open_registration` is false.
`backend/api/routes/auth.py` returns `Bootstrap already completed` when an admin already exists.
`tests/api_auth.py` defines `bootstrap_admin_and_headers`.
`tests/test_auth_api.py` asserts bootstrap success, registration-disabled `403`, and second-bootstrap `409`.
`GET /v1/auth/me` returns `is_admin` in the response JSON.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py -q</automated>
  </verify>
  <done>Onboarding is no longer default-open: operators must bootstrap the first admin explicitly, and the route closes once that admin exists.</done>
</task>

</tasks>

<verification>
Run the settings-only test after Task 1, then rerun the combined settings + auth tests after Task 2 so both startup validation and bootstrap flow stay green together.
</verification>

<success_criteria>
Phase 03 is ready to layer further protections when the app rejects the built-in JWT secret by default, self-service registration is closed by default, and the first admin can only be created through an explicit bootstrap path.
</success_criteria>

<output>
After completion, create `.planning/phases/03-secure-defaults/03-secure-defaults-01-SUMMARY.md`
</output>
