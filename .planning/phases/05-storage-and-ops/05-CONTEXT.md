# Phase 5: Storage and Ops - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Make storage and observability behave truthfully and scale with sustained usage. This phase covers explicit degraded-state signaling when dependency-backed health and metrics reads fail, less copy-heavy artifact ingestion into managed storage, and operator-controlled retention bounds for run and model-call history without losing the audit trail required for supported use cases.

It does not include remote object-store rollout, broader cloud/platform expansion, or a redesign of the run/workspace model established in earlier phases.

</domain>

<decisions>
## Implementation Decisions

### Degraded-state contract
- **D-01:** DB-backed health and metrics surfaces must report dependency degradation explicitly instead of substituting zero or healthy-looking queue values.
- **D-02:** Operator-facing queue truth must distinguish "no work is queued" from "queue state is currently unknown because dependency reads failed."

### Artifact ingest strategy
- **D-03:** Artifact ingestion should move large files into managed storage using streamed copy/hash behavior rather than reading the full file into memory first.
- **D-04:** This phase should preserve the current object-store contract and local storage backend; it is not a remote-storage migration project.

### Retention policy scope
- **D-05:** Operators must be able to bound retained run history and raw model payload history with explicit policy.
- **D-06:** Retention must preserve a minimal auditable record for supported use cases even when raw payloads or stored blobs age out.
- **D-07:** Artifact/blob cleanup should be coupled to retained audit metadata rather than defaulting to aggressive deletion with no trace of what existed.

### Retention execution model
- **D-08:** Retention should run through an explicit maintenance workflow or job with dry-run and reporting capability, not as hidden deletion inside normal request-path reads or writes.

### the agent's Discretion
- Exact degraded-state schema for `/metrics` and `/v1/worker/health`, as long as dependency failures are explicit and not silently encoded as zero activity
- Exact streamed-ingest mechanics inside the storage abstraction, as long as large-file movement avoids unnecessary full-memory copies
- Exact retention config surface, preserved metadata shape, and operator policy defaults, as long as the required audit trail remains intact
- Exact maintenance trigger or invocation seam, as long as retention remains explicit, testable, and operator-visible

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — brownfield hardening intent and why storage and operational truth are the remaining trust boundary
- `.planning/REQUIREMENTS.md` — `OPER-01`, `OPER-02`, and `OPER-03` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 5 goal, planned breakdown, and success criteria
- `.planning/STATE.md` — current project position after Phase 4 completion

### Prior phase decisions that constrain this phase
- `.planning/phases/01-run-isolation/01-CONTEXT.md` — run-scoped workspace and artifact-path contracts must remain canonical
- `.planning/phases/02-worker-resilience/02-CONTEXT.md` — worker queue truthfulness and attempt history semantics must remain accurate under degraded conditions
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — ops surfaces are protected and raw payload exposure is privileged/summary-first by default
- `.planning/phases/04-ci-coverage/04-CONTEXT.md` — CI now gates the documented stack, so new storage/ops behavior needs stable automated verification seams

### Existing storage and observability context
- `.planning/codebase/CONCERNS.md` — documents the zero-fill metrics behavior, full-memory artifact ingest, and missing retention policy
- `.planning/codebase/STACK.md` — current local-storage/runtime posture and deployment assumptions
- `.planning/codebase/TESTING.md` — current backend and integration test posture for health, worker, and artifact behavior
- `docs/local-stack.md` — documented local operational flow and current stack expectations around API, worker, and metrics
- `docs/auth-api.md` — secure-default treatment of protected ops endpoints that this phase must preserve

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/repositories/run_execution_job_repository.py` — already centralizes queue observability snapshot logic and last-terminal-job lookup for health and metrics surfaces
- `backend/storage/local.py` and `backend/storage/protocol.py` — current object-store seams where streamed ingest can land without widening backend scope
- `backend/services/artifact_service.py` — central path for ingesting pipeline files and attaching persisted artifact metadata
- `backend/services/recorded_chat_completion_service.py` — centralized persistence seam for raw model request/response payloads
- `backend/models/analysis_run.py`, `backend/models/model_call.py`, and `backend/models/artifact.py` — persisted history surfaces retention policy must bound without breaking auditability

### Established Patterns
- `/health` already reports a degraded top-level status when the DB probe fails, but `/v1/worker/health` and Prometheus queue gauges currently collapse DB failures into zero values
- Artifact persistence already separates metadata rows from object-store bytes, so ingest improvements can stay inside the existing storage abstraction
- Secure-default APIs now treat raw payloads as privileged/debug access, which means retention policy can prioritize trimming raw history while preserving summary/audit records
- There is no existing retention workflow, TTL policy, or cleanup job in the backend today

### Integration Points
- `backend/api/routes/health.py` and `backend/schemas/health.py` — worker-health response contract and degraded-state shape
- `backend/observability/metrics.py` — Prometheus queue gauge refresh logic that currently zero-fills on DB read failure
- `backend/services/artifact_service.py`, `backend/storage/local.py`, and `backend/storage/protocol.py` — large-file ingest path and storage backend capabilities
- `backend/services/recorded_chat_completion_service.py`, `backend/repositories/analysis_run_repository.py`, `backend/repositories/model_call_repository.py`, and related models — retention policy targets and audit-minimum semantics

</code_context>

<specifics>
## Specific Ideas

- User accepted the recommended defaults for all identified gray areas:
  - health and metrics should expose explicit degraded/error state instead of silently zero-filling
  - artifact ingest should use streamed copy/hash behavior while keeping the current local object-store contract
  - retention policy should bound run history and raw model payload history first while preserving an auditable minimum record
  - retention should run as an explicit maintenance workflow/job with dry-run and reporting, not implicit request-path deletion

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-storage-and-ops*
*Context gathered: 2026-04-17*
