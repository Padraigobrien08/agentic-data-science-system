# Phase 03: Secure Defaults - Research

**Researched:** 2026-04-16
**Domain:** Deployment-secret enforcement, default-closed registration, protected ops surfaces, and raw payload redaction
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Startup must fail if the built-in JWT secret is still active outside tests or an explicit local-development escape hatch.
- **D-02:** The local-development escape hatch must be explicit and operator-controlled, not inferred from runtime heuristics.
- **D-03:** New deployments should keep self-service registration closed by default.
- **D-04:** The system must provide an explicit bootstrap path for the first or admin user instead of relying on open registration by default.
- **D-05:** `/health` and `/ready` remain public.
- **D-06:** `/metrics` and `/v1/worker/health` must be protected by default with a dedicated ops credential, not normal end-user bearer auth.
- **D-07:** Run, model-call, and artifact APIs should default to redacted or summary views.
- **D-08:** Raw run/model payload access should be treated as an explicit debug or privileged capability, not automatic owner access.
- **D-09:** Normal artifact persistence should stop storing absolute filesystem paths such as `source_path` in exposed metadata.

### Claude's Discretion
- Exact env-var surface for the JWT-secret escape hatch
- Exact bootstrap mechanism for the first/admin user
- Exact credential mechanism for protecting `/metrics` and `/v1/worker/health`
- Exact redaction and privileged-access mechanics for raw payload/meta expansions

### Deferred Ideas (OUT OF SCOPE)
- Full RBAC
- SSO or external identity providers
- Secret-manager integration
- Cross-service CI expansion beyond what Phase 3 needs for secure-default regressions
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SECU-01 | Deployment fails fast when the default JWT secret is still configured outside tests | Settings-level equality check against the built-in dev secret, plus an explicit local-dev override flag |
| SECU-02 | New deployments keep self-service registration disabled unless an operator explicitly enables it | `allow_open_registration=False` by default plus a bootstrap-admin route guarded by an operator secret |
| SECU-03 | Metrics endpoints and persisted sensitive payload fields are protected or redacted by default | Dedicated ops-token dependency for `/metrics` and `/v1/worker/health`, admin-gated payload/meta expansions, sanitized artifact provenance |
</phase_requirements>

## Summary

The current codebase already has the right brownfield seams for this phase: `backend/config/settings.py` centralizes startup validation, `backend/api/routes/auth.py` already owns the registration/login boundary, `backend/api/auth_deps.py` already defines bearer-auth dependencies, and `backend/api/routes/runs.py` plus `backend/api/routes/artifacts.py` already default to slim responses unless `include_payloads` or `include_meta` is requested. This phase should harden those seams instead of introducing a new auth stack.

The main gap is that the current "production" validator only checks JWT-secret length. The built-in default secret is long enough to satisfy that check, so a production-like deployment can still start with a known shared secret. At the same time, `allow_open_registration` still defaults to `true`, `docker-compose.yml` still bakes in an insecure JWT fallback and default-open registration, `/metrics` and `/v1/worker/health` are public, and artifact ingestion still stores an absolute `source_path` into artifact metadata.

The second planning risk is capability mixing. There is no existing admin role, no separate ops credential, and no richer RBAC surface. The plan therefore needs to introduce the smallest new privileges that satisfy the locked decisions without rewriting owner-based authorization: an explicit bootstrap-admin path for application-level privileged access, plus a separate dedicated ops token for infrastructure endpoints.

**Primary recommendation:** keep the current JWT + owner-based model, add explicit `is_admin` bootstrap capability for privileged payload access, protect ops-only routes with a separate ops token, and sanitize artifact provenance at persistence time so absolute paths never reach stored metadata.

## Preserve vs Change

- Preserve the current FastAPI route layout, owner-based access checks, and summary-first response shapes.
- Preserve JWT bearer auth for normal application users.
- Preserve `/health` and `/ready` as public health endpoints.
- Change startup validation so the built-in JWT secret is rejected unless an explicit dev-only override is enabled.
- Change registration posture so self-service registration is opt-in, not opt-out.
- Change user persistence to track an explicit `is_admin` capability for bootstrap-created operators.
- Change `/metrics` and `/v1/worker/health` from public routes to ops-token-protected routes.
- Change raw payload and artifact-meta expansions from "owner can opt in" to "admin-only opt in".
- Change artifact ingestion so it persists sanitized provenance (`source_filename`, workspace-relative path) instead of absolute filesystem paths.

## Standard Stack

### Core

| Library / Surface | Version / Source | Purpose | Why Standard |
|-------------------|------------------|---------|--------------|
| FastAPI security dependencies already in repo | current repo | Bearer parsing for JWT users and a second bearer dependency for ops routes | No new web framework or auth package needed |
| Pydantic settings + validators | current repo | Fail-fast env validation for JWT secret, onboarding posture, and ops token | Current settings architecture already owns startup sanity |
| SQLAlchemy + Alembic | current repo | Persist `users.is_admin` and migrate brownfield auth state safely | Existing schema/migration path is already established |
| Existing slim API schemas | `backend/schemas/api_phase_a.py` | Keep summary-first responses while tightening privileged expansions | Avoids route rewrites and preserves frontend compatibility |

### Supporting

| Library / Surface | Purpose | When to Use |
|-------------------|---------|-------------|
| `tests/conftest.py` env bootstrap | Keep broad legacy tests working when defaults become stricter | Use for stable test-only env such as bootstrap and ops tokens |
| `frontend/src/actions/auth.ts` and register page | User-facing guidance when registration is disabled by default | Use only for messaging, not for frontend-auth redesign |
| `docker-compose.yml` + `.env.example` | Deployment defaults and local-operator contract | Must be updated so docs and runtime defaults match the hardened backend |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `is_admin` + bootstrap token | Full RBAC / role table | Too large for a hardening phase; no current role system exists |
| Dedicated ops bearer token | Network-only protection or reuse user JWTs | Violates locked decision D-06 and blurs application vs ops access |
| Sanitized artifact provenance | Continue storing absolute `source_path` and just hide it in the UI | Still leaves sensitive paths persisted and retrievable |

**Installation**

```bash
# No new dependency is recommended for Phase 3.
# Use the existing FastAPI / SQLAlchemy / Alembic stack already declared in the repo.
```

## Architecture Patterns

### Pattern 1: Explicit Unsafe-Dev Opt-In

**What:** Reject the built-in JWT secret by exact value match unless an explicit boolean such as `EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true` is set.

**When to use:** During `Settings` validation, before app startup.

**Why:** Length-only validation is insufficient because the current built-in secret is long enough to pass the existing check.

**Recommendation:** Keep the override narrow. It should bypass only the built-in-secret prohibition, not the rest of startup validation.

### Pattern 2: Default-Closed Registration With Bootstrap Admin

**What:** Set `allow_open_registration` to `False` by default and add a `POST /v1/auth/bootstrap` route guarded by `X-EDGAR-Bootstrap-Token`.

**When to use:** First-user onboarding and operator-controlled local/dev setup.

**Why:** The codebase has no current admin concept. The smallest brownfield-safe addition is `users.is_admin` plus a one-time bootstrap path.

**Recommendation:** Make bootstrap succeed only when no admin user exists yet. Once the first admin is created, later operator flows can use explicit reconfiguration or future admin endpoints instead of leaving bootstrap indefinitely open.

### Pattern 3: Separate Ops Credential for Infrastructure Endpoints

**What:** Require a dedicated bearer token such as `EDGAR_BACKEND_OPS_API_TOKEN` on `/metrics` and `/v1/worker/health`.

**When to use:** Ops-only routes that are not part of normal end-user application behavior.

**Why:** Locked decision D-06 explicitly rejects normal user JWTs as the protection mechanism for these endpoints.

**Recommendation:** Keep `/health` and `/ready` public, but make the ops token a required startup setting in normal app configuration so the protected routes are never accidentally left public.

### Pattern 4: Admin-Gated Expansion on Existing Owner Routes

**What:** Keep run/artifact/model-call routes owner-scoped, but require `current_user.is_admin` before honoring `include_payloads=true` or `include_meta=true`.

**When to use:** `GET /v1/runs/{id}`, `GET /v1/runs/{id}/steps`, `GET /v1/runs/{id}/model-calls`, and `GET /v1/artifacts/{id}`.

**Why:** The route shapes already default to summary mode. The missing guard is on the expansion flags.

**Recommendation:** Return `403` with explicit detail when a non-admin owner asks for raw payload/meta expansions. Do not change the default summary response shape.

### Pattern 5: Sanitized Artifact Provenance

**What:** Persist `source_filename` and, when applicable, `source_workspace_relative_path` instead of absolute `source_path`.

**When to use:** `ArtifactService.ingest_pipeline_file(...)`.

**Why:** Phase 1 now gives every persisted run a durable workspace contract, so provenance can stay meaningful without exposing filesystem roots.

**Recommendation:** If the ingested file lives under `settings.run_workspace_root/<run_id>/`, store a path relative to that run workspace such as `artifacts/report.md`. Otherwise store only the basename.

## Anti-Patterns to Avoid

- **Length-only JWT validation:** the built-in secret already satisfies the current minimum-length check.
- **Implicit dev heuristics:** do not infer the insecure-secret bypass from `debug`, bind address, or container names alone.
- **Leaving bootstrap unspecified:** if registration is closed, the bootstrap path must be documented and wired.
- **Protecting ops endpoints only at the network layer:** Phase 3 requires in-app authentication.
- **Letting any owner request raw payloads:** the current `include_payloads` and `include_meta` flags are the exact exposure seam this phase needs to tighten.
- **Persisting absolute artifact paths and hoping the UI never renders them:** the risk lives in persistence as well as presentation.

## Common Pitfalls

### Pitfall 1: Global Test Breakage After Flipping `allow_open_registration`

**What goes wrong:** many backend tests use `tests/api_auth.py` and start failing immediately when registration defaults to closed.

**How to avoid:** make test-only env explicit in `tests/conftest.py` and add dedicated secure-default tests that clear `get_settings.cache_clear()` or instantiate `Settings(...)` directly.

### Pitfall 2: Header Collision Between User JWT and Ops Credential

**What goes wrong:** trying to reuse the same credential mechanism on routes that already require end-user bearer auth leads to ambiguous semantics.

**How to avoid:** reserve the dedicated ops token for ops-only routes, and use `is_admin` for privileged expansions on owner routes.

### Pitfall 3: Bootstrap Route That Never Closes

**What goes wrong:** leaving bootstrap usable after the first admin exists creates a second hidden registration surface.

**How to avoid:** reject bootstrap once any admin user exists, or require a future explicit admin-managed flow beyond this phase.

### Pitfall 4: Sanitizing Responses but Not Persistence

**What goes wrong:** API defaults look safe, but absolute paths are still stored in DB rows and can leak later through debug views, exports, or logs.

**How to avoid:** sanitize artifact provenance before persistence, not only at response serialization time.

## Open Questions

1. **Should bootstrap create only the first admin or also serve as an admin-managed create-user path later?**
   - Recommendation: first-admin-only for Phase 3. It keeps the privilege surface narrow and meets D-04 without inventing broader user management.

2. **Should ops-token presence fail startup or only disable ops endpoints?**
   - Recommendation: fail startup when the token is absent in normal app configuration. Silent disablement is too easy to miss and weakens the secure-default posture.

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|-------------|-----------|-------|
| Python / pytest | Backend settings and API regressions | ✓ | Existing suite already covers auth and health endpoints |
| Alembic | `users.is_admin` migration | ✓ | Existing migration workflow is already in place |
| Docker Compose | Docs/stack alignment checks | ✓ | Compose currently bakes insecure defaults and must be updated |
| Frontend toolchain | Registration copy alignment | ✓ | Frontend already has register page and auth server actions |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` 8.4.2 for backend, existing Vitest setup available for frontend if needed |
| Config file | `pytest.ini` and `frontend/vitest.config.ts` |
| Quick run command | `python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q` |
| Full backend suite | `python3 -m pytest tests/ -q --tb=short` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SECU-01 | Built-in JWT secret fails startup unless explicit unsafe-dev override is set | unit / settings | `python3 -m pytest tests/test_secure_defaults_settings.py -q` | ❌ Wave 0 |
| SECU-02 | Registration is closed by default and first-admin bootstrap is explicit | API integration | `python3 -m pytest tests/test_auth_api.py tests/test_secure_defaults_api.py -q` | ⚠️ partial |
| SECU-03 | Ops endpoints require ops token, raw payload/meta expansions require privileged access, and artifact provenance is sanitized | API integration + persistence | `python3 -m pytest tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q` | ⚠️ partial |

### Sampling Rate

- **After every task commit:** run the targeted module(s) named in the task `<verify>` block.
- **After every plan wave:** run the quick Phase 3 backend command from the table above.
- **Before `$gsd-execute-phase 3` completion:** rerun the full Phase 3 backend command and any docs/frontend checks added by Plan 03-03.

### Wave 0 Gaps

- [ ] `tests/test_secure_defaults_settings.py` — direct `Settings(...)` regression coverage for JWT-secret rejection and explicit escape hatch behavior
- [ ] `tests/test_secure_defaults_api.py` — bootstrap-admin flow, ops-token protection, and admin-only payload/meta expansion coverage
- [ ] Existing auth and artifact tests updated for closed-by-default registration and sanitized artifact provenance
- [ ] Compose/docs regression surface updated so local stack instructions match the new required env vars and bootstrap flow

## Sources

### Primary (HIGH confidence)

- Current repository code:
  - `backend/config/settings.py`
  - `backend/api/routes/auth.py`
  - `backend/api/auth_deps.py`
  - `backend/api/routes/metrics.py`
  - `backend/api/routes/health.py`
  - `backend/api/routes/runs.py`
  - `backend/api/routes/artifacts.py`
  - `backend/services/artifact_service.py`
  - `backend/services/recorded_chat_completion_service.py`
  - `backend/models/user.py`
  - `docs/auth-api.md`
  - `docs/local-stack.md`
  - `docker-compose.yml`
  - `.env.example`
  - `tests/test_auth_api.py`
  - `tests/test_backend_health.py`
  - `tests/test_artifact_storage.py`
  - `tests/test_run_isolation_execution_service.py`
  - `frontend/src/actions/auth.ts`
  - `frontend/src/app/register/page.tsx`

### Secondary (MEDIUM confidence)

- `.planning/codebase/CONCERNS.md`
- `.planning/codebase/STACK.md`
- `.planning/phases/01-run-isolation/01-CONTEXT.md`
- `.planning/phases/02-worker-resilience/02-CONTEXT.md`

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all recommended mechanisms are already present in the repo architecture
- Architecture: HIGH - grounded in current settings, auth, routes, docs, and test helpers
- Validation: HIGH - existing auth/health/artifact tests expose the exact seams Phase 3 needs to lock down

**Research date:** 2026-04-16
**Valid until:** 2026-05-16
