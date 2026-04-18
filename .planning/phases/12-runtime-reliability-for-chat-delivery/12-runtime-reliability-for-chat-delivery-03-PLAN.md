---
phase: 12-runtime-reliability-for-chat-delivery
plan: 03
type: execute
wave: 3
depends_on:
  - "12-02"
files_modified:
  - backend/api/routes/auth.py
  - backend/schemas/auth.py
  - frontend/src/lib/api/types.ts
  - frontend/src/lib/api/runs.ts
  - frontend/src/actions/auth.ts
  - frontend/src/app/login/page.tsx
  - frontend/src/app/register/page.tsx
  - frontend/src/components/auth/register-form.tsx
  - frontend/src/components/auth/auth-entry-guidance.tsx
  - frontend/src/components/auth/auth-entry-guidance.test.tsx
  - tests/test_auth_api.py
  - tests/test_secure_defaults_api.py
autonomous: true
requirements:
  - RUN-03
must_haves:
  truths:
    - "First-run local auth/onboarding surfaces no longer advertise a dead-end register path when secure-default registration is closed."
    - "The frontend can distinguish open registration, bootstrap-required, and sign-in-only states through a coarse public capability contract."
    - "Onboarding cleanup stays narrowly tied to first-run chat delivery and does not broaden into a general auth redesign."
  artifacts:
    - path: backend/api/routes/auth.py
      provides: "Public auth-capability contract for login/register surfaces"
    - path: frontend/src/components/auth/auth-entry-guidance.tsx
      provides: "Reusable environment-aware onboarding guidance for secure-default deployments"
    - path: tests/test_auth_api.py
      provides: "API regression coverage for auth capability states"
    - path: frontend/src/components/auth/auth-entry-guidance.test.tsx
      provides: "Frontend regression coverage for open-registration, bootstrap-required, and sign-in-only guidance"
  key_links:
    - from: backend/api/routes/auth.py
      to: frontend/src/app/login/page.tsx
      via: "login and register pages read one coarse capability surface instead of hardcoding registration assumptions"
      pattern: "capabilities|bootstrap_required|bootstrap_completed"
    - from: frontend/src/actions/auth.ts
      to: frontend/src/components/auth/register-form.tsx
      via: "register-form errors use the capability-aware messaging instead of a generic dead-end disabled-registration string"
      pattern: "Registration is disabled|bootstrap|required"
    - from: tests/test_secure_defaults_api.py
      to: backend/api/routes/auth.py
      via: "tests lock secure-default registration and bootstrap states to the new capability contract"
      pattern: "/v1/auth/register|/v1/auth/bootstrap|/v1/auth/capabilities"
---

<objective>
Replace the dead-end first-run auth story with environment-aware onboarding guidance that matches the secure-default local stack.

Purpose: complete the Phase 12 scope expansion by removing the auth blockers discovered during live chat testing without widening into a full account-management project.
Output: a public auth-capability contract, adaptive login/register surfaces, and backend/frontend regression coverage.
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
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-02-PLAN.md
@backend/api/routes/auth.py
@backend/schemas/auth.py
@backend/config/settings.py
@frontend/src/actions/auth.ts
@frontend/src/app/login/page.tsx
@frontend/src/app/register/page.tsx
@frontend/src/components/auth/register-form.tsx
@tests/test_auth_api.py
@tests/test_secure_defaults_api.py

<interfaces>
From `backend/api/routes/auth.py`:
```python
@router.post("/register", response_model=UserRead, status_code=201)
@router.post("/bootstrap", response_model=UserRead, status_code=201)
@router.post("/login", response_model=AccessTokenResponse)
```

From `frontend/src/actions/auth.ts`:
```ts
export async function registerAction(_prev: RegisterState, formData: FormData): Promise<RegisterState>
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Expose a coarse public auth-capability contract</name>
  <files>backend/api/routes/auth.py
backend/schemas/auth.py
tests/test_auth_api.py
tests/test_secure_defaults_api.py</files>
  <read_first>.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
backend/api/routes/auth.py
backend/schemas/auth.py
backend/config/settings.py
tests/test_auth_api.py
tests/test_secure_defaults_api.py</read_first>
  <behavior>
    - The frontend can discover whether registration is open, whether bootstrap is still required, and whether sign-in is the only correct first-run path.
    - The capability contract exposes no secrets or bootstrap token material.
    - Existing register, bootstrap, and login behavior remains intact; this task only adds truthful capability discovery.
  </behavior>
  <action>Extend `backend/schemas/auth.py` with a new response model named `AuthCapabilitiesResponse` containing the exact boolean fields `allow_open_registration`, `bootstrap_required`, and `bootstrap_completed`. Add `GET /v1/auth/capabilities` to `backend/api/routes/auth.py`. The route must read `allow_open_registration` from settings, query whether any admin user exists, set `bootstrap_required=True` when open registration is false and no admin exists, and set `bootstrap_completed=True` when any admin already exists. Do not expose the bootstrap token or any user-identifying data. Extend `tests/test_auth_api.py` and `tests/test_secure_defaults_api.py` so they cover three cases: open registration enabled, secure-default with no admin yet, and secure-default after bootstrap has already completed.</action>
  <acceptance_criteria>`backend/schemas/auth.py` contains `class AuthCapabilitiesResponse`.
`backend/schemas/auth.py` contains `allow_open_registration`.
`backend/schemas/auth.py` contains `bootstrap_required`.
`backend/schemas/auth.py` contains `bootstrap_completed`.
`backend/api/routes/auth.py` contains `@router.get("/capabilities"`.
`backend/api/routes/auth.py` contains `bootstrap_required`.
`backend/api/routes/auth.py` contains `bootstrap_completed`.
`tests/test_auth_api.py` contains `/v1/auth/capabilities`.
`tests/test_secure_defaults_api.py` contains `/v1/auth/capabilities`.
`python3 -m pytest tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short</automated>
  </verify>
  <done>The frontend can now tell whether registration is open, bootstrap is required, or sign-in is the correct first-run path.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace dead-end login and register copy with capability-aware guidance</name>
  <files>frontend/src/lib/api/types.ts
frontend/src/lib/api/runs.ts
frontend/src/actions/auth.ts
frontend/src/app/login/page.tsx
frontend/src/app/register/page.tsx
frontend/src/components/auth/register-form.tsx
frontend/src/components/auth/auth-entry-guidance.tsx
frontend/src/components/auth/auth-entry-guidance.test.tsx</files>
  <read_first>.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
frontend/src/actions/auth.ts
frontend/src/app/login/page.tsx
frontend/src/app/register/page.tsx
frontend/src/components/auth/register-form.tsx
backend/schemas/auth.py
backend/api/routes/auth.py</read_first>
  <behavior>
    - Login and register screens should tell the truth about the current environment instead of always advertising account creation.
    - When registration is closed and bootstrap is already complete, the UI should direct users toward sign-in rather than a dead-end create-account form.
    - When bootstrap is still required, the UI should explain that an operator/bootstrap step is needed instead of implying ordinary self-registration.
  </behavior>
  <action>Extend `frontend/src/lib/api/types.ts` and `frontend/src/lib/api/runs.ts` or create the equivalent existing API helper surface so the frontend can fetch `AuthCapabilitiesResponse` server-side. Create `frontend/src/components/auth/auth-entry-guidance.tsx` as a pure presentational component that renders three exact states: open registration, bootstrap required, and sign-in only. Update `frontend/src/app/login/page.tsx` to fetch auth capabilities server-side and replace the unconditional “Create one” link with `AuthEntryGuidance`. Update `frontend/src/app/register/page.tsx` so when `allow_open_registration` is false and `bootstrap_completed` is true it redirects or links the user back to sign-in instead of rendering the dead-end form; when `bootstrap_required` is true it shows the guidance component instead of the normal registration form. Update `frontend/src/actions/auth.ts` and `frontend/src/components/auth/register-form.tsx` so the disabled-registration error text matches the new capability-aware guidance. Add `frontend/src/components/auth/auth-entry-guidance.test.tsx` to cover all three states.</action>
  <acceptance_criteria>`frontend/src/lib/api/types.ts` contains `AuthCapabilitiesResponse`.
`frontend/src/actions/auth.ts` contains `Registration is disabled`.
`frontend/src/actions/auth.ts` contains `bootstrap`.
`frontend/src/components/auth/auth-entry-guidance.tsx` exists.
`frontend/src/components/auth/auth-entry-guidance.tsx` contains `Create account`.
`frontend/src/components/auth/auth-entry-guidance.tsx` contains `bootstrap`.
`frontend/src/components/auth/auth-entry-guidance.tsx` contains `Sign in`.
`frontend/src/app/login/page.tsx` no longer contains the unconditional text `Create one`.
`frontend/src/app/register/page.tsx` contains `bootstrap_required` or `bootstrapCompleted`.
`frontend/src/components/auth/auth-entry-guidance.test.tsx` exists.
`cd frontend && npm run test -- src/components/auth/auth-entry-guidance.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/auth/auth-entry-guidance.test.tsx</automated>
  </verify>
  <done>First-run auth surfaces now match the secure-default environment instead of pointing users into a dead-end registration flow.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short` after the capability endpoint lands, then rerun `cd frontend && npm run test -- src/components/auth/auth-entry-guidance.test.tsx` after the login/register guidance is updated.
</verification>

<success_criteria>
Phase 12 completes its onboarding scope once the secure-default local stack tells users truthfully whether they should register, bootstrap, or simply sign in before using workspace chat.
</success_criteria>

<output>
After completion, create `.planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-03-SUMMARY.md`
</output>
