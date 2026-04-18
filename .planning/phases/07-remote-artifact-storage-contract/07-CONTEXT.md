# Phase 7: Remote Artifact Storage Contract - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Add one S3-compatible remote object-store backend behind the existing artifact contract so users and operators can use remote artifact storage without changing artifact identity, authorization, or audit semantics. This phase covers the canonical remote-storage contract, backend selection and coexistence with existing `local:` artifacts, opaque storage locators, and explicit reconciliation or tombstone behavior when Postgres and blob storage diverge.

It does not include presigned URL rollout as the primary delivery path, multi-cloud orchestration, a mandatory bulk migration of all historic local artifacts, or broader evaluation/trace product changes outside what is required to keep artifact storage trustworthy.

</domain>

<decisions>
## Implementation Decisions

### Canonical S3 semantics
- **D-01:** Standard AWS S3 semantics should define the canonical remote-storage contract for this phase.
- **D-02:** The implementation should remain configurable for S3-compatible endpoints, but this phase should add only one S3-compatible backend rather than widening into multi-cloud storage orchestration.

### Cutover and coexistence
- **D-03:** New artifacts should write to the configured backend, while existing persisted `local:` artifacts remain readable; this phase should not require a one-shot bulk migration before rollout.
- **D-04:** Artifact identity, authorization, and product-facing routes must stay stable across mixed local and remote history; backend selection should come from configuration plus persisted URI scheme, not separate user-facing paths.

### Opaque locator and delivery contract
- **D-05:** `Artifact.storage_uri` should remain an app-owned opaque locator, not a raw bucket/key product contract.
- **D-06:** Artifact content should continue to flow through the existing application-owned authorized delivery path; this phase must not expose bucket names, object keys, or long-lived object URLs in normal product surfaces.

### DB and object-store divergence
- **D-07:** Postgres and object storage must be treated as separate systems; upload, delete, and retention flows should use explicit repairable states instead of assuming atomic cross-system success.
- **D-08:** Checksums, lineage, tombstones, and reconciliation signals must remain explicit even when the storage backend is remote and deletion/versioning semantics differ from local disk.

### the agent's Discretion
- Exact `boto3` config surface for endpoint URL, region, credentials, and path-style behavior, as long as AWS S3 semantics stay canonical
- Exact remote URI scheme format (`s3:` vs `s3+alias:` or equivalent), as long as it stays opaque to product surfaces and round-trips through resolver logic
- Exact reconciliation/reporting mechanism for orphaned DB rows or blobs, as long as divergence is visible and repairable
- Exact rollout/test strategy for configured-write mixed-read behavior, as long as brownfield compatibility and audit trust remain intact

</decisions>

<specifics>
## Specific Ideas

- User accepted the recommended defaults for all identified gray areas in one step:
  - AWS S3 semantics are the canonical contract, while configuration may still target S3-compatible endpoints
  - cutover should be configured-write with mixed-read support rather than mandatory bulk migration
  - remote storage locators should stay opaque and app-owned rather than exposing bucket/key details
  - Postgres/object-store mismatch should be handled with explicit reconciliation state, not false atomicity assumptions

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — current milestone intent, brownfield constraints, and post-v1.0 trust posture
- `.planning/REQUIREMENTS.md` — `STOR-01`, `STOR-02`, and `OPS-02` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 7 goal, dependencies, and success criteria
- `.planning/STATE.md` — current project position after Phase 6 completion

### Milestone research and storage pitfalls
- `.planning/research/SUMMARY.md` — milestone synthesis, recommended stack delta (`boto3`/`moto`), and anti-features around bucket-coupled APIs
- `.planning/research/FEATURES.md` — remote-storage table stakes and explicit rejection of raw bucket/key exposure in product surfaces
- `.planning/research/PITFALLS.md` — object-store atomicity, checksum, delete/versioning, and delivery-path pitfalls this phase is meant to prevent

### Prior phase decisions that constrain this phase
- `.planning/phases/01-run-isolation/01-CONTEXT.md` — run-scoped workspaces and artifact identity must stay canonical while storage moves off shared disk
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — artifact delivery and sensitive metadata remain summary-first and protected by application auth
- `.planning/phases/05-storage-and-ops/05-CONTEXT.md` — retention tombstones, streamed ingest, and explicit degraded-state reporting must survive remote storage rollout
- `.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md` — evaluation artifacts must remain isolatable from normal user work as later validation-control-plane phases build on this storage contract

### Existing storage and delivery surfaces
- `backend/storage/protocol.py` — current object-store contract that the remote backend must implement
- `backend/storage/local.py` — local reference backend and current URI/key semantics
- `backend/storage/resolver.py` — URI-scheme dispatch seam for read/delete operations
- `backend/storage/factory.py` — current single-backend construction seam
- `backend/services/artifact_service.py` — artifact write, ingest, delete, and lineage contract
- `backend/api/routes/artifacts.py` — auth-safe content and preview delivery path that must remain stable
- `backend/models/artifact.py` — persisted artifact metadata contract, including opaque `storage_uri` and retention tombstones
- `docs/artifact-delivery.md` — documented artifact content/preview contract and user-visible error semantics
- `docs/local-stack.md` — current deployment posture and local-storage assumptions that planning must evolve safely

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/storage/protocol.py` — already defines a backend-agnostic object-store seam with `put`, `put_fileobj`, `open_reader`, `delete`, and URI round-tripping
- `backend/storage/resolver.py` — already treats `storage_uri` as scheme-dispatched and contains an explicit future hook for `s3:` handling
- `backend/services/artifact_service.py` — already centralizes artifact writes, streamed ingest, row persistence, and delete behavior around the storage abstraction
- `backend/api/routes/artifacts.py` — already serves artifact bytes through app-owned auth-safe routes and strips internal locator details from error responses
- `tests/test_artifact_storage.py` and `tests/test_artifact_content_delivery.py` — already lock the storage contract, tombstone semantics, and “no bucket/key leak” behavior in a backend-agnostic style

### Established Patterns
- `Artifact.storage_uri` is already treated as a backend-specific locator rather than a client-consumable path
- The product already differentiates retention-expired artifacts (`410`) from missing storage blobs (`404`) and unsupported backend/configuration (`502`)
- Artifact metadata, lineage, and authorization remain in Postgres while blob bytes live behind storage abstraction and content routes
- Retention and delete behavior are already modeled as logical row state plus storage action rather than simple filesystem removal assumptions

### Integration Points
- `backend/config/settings.py` and `backend/storage/factory.py` — backend selection and configuration surface for the first remote store
- `backend/storage/resolver.py` and `backend/api/routes/artifacts.py` — mixed-read delivery behavior for both legacy `local:` and new remote URIs
- `backend/services/artifact_service.py` — configured-write behavior, checksum persistence, and repairable dual-write semantics
- `backend/maintenance/retention.py` and `backend/repositories/artifact_repository.py` — remote-aware retention and tombstone flows
- `docs/local-stack.md`, `docs/artifact-delivery.md`, and storage-focused tests — rollout and regression seams that must stay truthful as the backend changes

</code_context>

<deferred>
## Deferred Ideas

- Brokered short-lived signed URLs for very large artifacts — later v1.1/v2 work once proxy-delivery limits are proven
- Mandatory migration/backfill of all historical `local:` artifacts into remote storage — separate rollout or maintenance workstream if needed
- Multi-cloud or provider-specific orchestration beyond the first S3-compatible backend

</deferred>

---

*Phase: 07-remote-artifact-storage-contract*
*Context gathered: 2026-04-18*
