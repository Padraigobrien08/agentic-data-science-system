# Phase 3: Secure Defaults - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate insecure production defaults and reduce exposure of sensitive operational data. This phase covers startup enforcement for JWT secrets, default registration posture, protection of operational telemetry endpoints, and safer defaults for persisted run/model/artifact payload visibility.

It does not include full RBAC, enterprise SSO, managed secret-store integration, or broader CI expansion; those belong in later phases.

</domain>

<decisions>
## Implementation Decisions

### Deployment secret enforcement
- **D-01:** Startup must fail if the built-in JWT secret is still active outside tests or an explicit local-development escape hatch.
- **D-02:** The local-development escape hatch must be explicit and operator-controlled, not inferred implicitly from runtime heuristics such as bind address or host environment.

### Registration posture
- **D-03:** New deployments should keep self-service registration closed by default.
- **D-04:** The system must provide an explicit bootstrap path for the first or admin user instead of relying on open registration by default.

### Operational endpoint access
- **D-05:** `/health` and `/ready` remain public.
- **D-06:** `/metrics` and `/v1/worker/health` must be protected by default with a dedicated ops credential, not normal end-user bearer auth and not network-only protection as the secure default.

### Sensitive payload visibility
- **D-07:** Run, model-call, and artifact APIs should default to redacted or summary views.
- **D-08:** Raw run/model payload access should be treated as an explicit debug or privileged ops capability, not something every resource owner automatically gets.
- **D-09:** Normal artifact persistence should stop storing absolute filesystem paths such as `source_path` in exposed metadata.

### the agent's Discretion
- Exact environment/config surface for the local-development JWT-secret escape hatch
- Exact bootstrap mechanism for the first/admin user, as long as it is explicit and does not depend on default-open self-service registration
- Exact credential mechanism for protecting `/metrics` and `/v1/worker/health`, as long as it is a dedicated ops path rather than normal user auth
- Exact redaction schema and privileged/debug gating mechanics for raw payload access, as long as default APIs remain summary-first

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — overall hardening intent, brownfield constraints, and security-default goals for this milestone
- `.planning/REQUIREMENTS.md` — `SECU-01`, `SECU-02`, and `SECU-03` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 3 goal, planned breakdown, and success criteria
- `.planning/STATE.md` — current project position after Phase 2 completion

### Existing security and deployment context
- `.planning/codebase/CONCERNS.md` — documented risks around default JWT secret, open registration, public metrics, and persisted sensitive payloads
- `.planning/codebase/STACK.md` — deployment/runtime posture, env-var surface, and documented self-hosted stack assumptions
- `docs/auth-api.md` — current auth model, public/protected route behavior, and existing registration/login contract
- `docs/local-stack.md` — documented local deployment flow and current operator expectations for the self-hosted stack

### Prior phase decisions that constrain this phase
- `.planning/phases/01-run-isolation/01-CONTEXT.md` — run-scoped workspace and artifact contract decisions that payload redaction must preserve
- `.planning/phases/02-worker-resilience/02-CONTEXT.md` — worker/status observability decisions that security changes must not make ambiguous

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/config/settings.py` — existing validator-based startup sanity checks are the natural seam for secret and registration posture enforcement
- `backend/api/auth_deps.py` and `backend/api/router.py` — existing dependency wiring provides a clear seam for adding protected operational endpoints without reshaping the rest of the API
- `backend/schemas/api_phase_a.py` and `backend/api/routes/runs.py` — current summary-vs-raw response toggles already exist, making tighter gating/redaction an additive change
- `backend/services/artifact_service.py` and `backend/services/recorded_chat_completion_service.py` — centralized persistence seams for artifact metadata and model-call raw payloads

### Established Patterns
- Public and authenticated routes are already separated: `health`, `metrics`, and `auth` are public, while `projects`, `runs`, and `artifacts` sit behind bearer auth
- Owner-based authorization is the only current access model; there is no richer RBAC or ops-role system yet
- Large/sensitive payloads are already hidden by default in several APIs via explicit `include_payloads` or `include_meta` flags, so tightening defaults does not require inventing a new response style from scratch

### Integration Points
- `backend/config/settings.py` and startup flow in `backend/main.py` — secret enforcement, registration defaults, and new secure env/config knobs
- `backend/api/routes/auth.py` and `docs/auth-api.md` — bootstrap and registration posture changes
- `backend/api/routes/metrics.py` and `backend/api/routes/health.py` — protection for operational telemetry surfaces
- `backend/api/routes/runs.py`, `backend/schemas/api_phase_a.py`, `backend/services/artifact_service.py`, and `backend/services/recorded_chat_completion_service.py` — redaction, privileged raw access, and path-sanitized persistence

</code_context>

<specifics>
## Specific Ideas

- User accepted the recommended defaults for all identified gray areas:
  - fail startup when the built-in JWT secret is still active outside tests or an explicit local-dev escape hatch
  - closed-by-default registration with an explicit bootstrap/admin path
  - keep `/health` and `/ready` public, but protect `/metrics` and `/v1/worker/health` with a dedicated ops credential
  - default to redacted/summary payload views, treat raw payloads as explicit debug/privileged access, and stop persisting absolute filesystem paths in normal artifact metadata

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-secure-defaults*
*Context gathered: 2026-04-16*
