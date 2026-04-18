# Phase 07: Remote Artifact Storage Contract - Research

**Researched:** 2026-04-18
**Domain:** S3-compatible artifact storage behind the existing artifact contract
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Standard AWS S3 semantics define the canonical remote-storage contract for this phase.
- **D-02:** Configuration may still target S3-compatible endpoints, but this phase adds only one S3-compatible backend.
- **D-03:** New artifacts write to the configured backend while existing `local:` artifacts remain readable; no mandatory bulk migration.
- **D-04:** Artifact identity, authorization, and product-facing routes stay stable across mixed local and remote history.
- **D-05:** `Artifact.storage_uri` remains an app-owned opaque locator, not a raw bucket or object-key product contract.
- **D-06:** Artifact bytes continue to flow through the existing application-owned authorized delivery path; no presigned URL rollout in this phase.
- **D-07:** Postgres and object storage are separate systems; upload, delete, and retention flows must use explicit repairable divergence handling instead of false atomicity.
- **D-08:** Checksums, lineage, tombstones, and reconciliation signals remain explicit after remote storage is introduced.

### the agent's Discretion
- Exact settings names and defaults for S3 bucket, prefix, endpoint URL, and path-style behavior
- Exact remote URI format, as long as it stays app-owned and does not expose bucket names in normal product surfaces
- Exact reconciliation metadata shape, as long as divergence remains repairable and operator-visible
- Exact test split between new backend-specific files and extensions to existing artifact tests

### Deferred Ideas (OUT OF SCOPE)
- Presigned URL or signed-download delivery as the primary artifact path
- Mandatory bulk migration of all historical `local:` artifacts into remote storage
- Multi-cloud or provider-specific backend matrix beyond the first S3-compatible target
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-01 | Operator can configure one S3-compatible remote object-store backend for artifact blobs without changing artifact IDs, authorization rules, or opaque storage URIs in product surfaces | Add one S3-compatible store behind the existing protocol, plus settings-driven write selection and scheme-driven mixed reads. |
| STOR-02 | Artifact writes, reads, deletes, and retention workflows preserve checksums, lineage, and audit-visible tombstone or reconciliation state across local and remote backends | Keep logical artifact keys and SHA-256 contract, avoid ETag-as-truth, and make delete or prune divergence explicit instead of silent. |
| OPS-02 | Users can retrieve large retained artifacts through an authorized delivery path that remains compatible with remote storage without exposing raw bucket or object identifiers | Keep the current `/v1/artifacts/*` routes as the delivery boundary, add remote-backed route regressions, and document that `storage_uri` is not a client-side transport contract. |
</phase_requirements>

## Summary

The codebase already has the right storage seam for this phase. `backend/storage/protocol.py` defines a backend-agnostic object-store contract, `backend/storage/resolver.py` already treats `storage_uri` as scheme-dispatched and has an explicit future hook for S3, `backend/services/artifact_service.py` centralizes writes and deletes, and `backend/api/routes/artifacts.py` already keeps delivery app-owned and auth-gated. The missing work is not a rewrite; it is filling the gaps the repo already points at.

The two highest-risk details are locator design and divergence handling. Because `storage_uri` is exposed in artifact metadata responses, persisting raw `s3://bucket/key` locators would leak infrastructure details and would quickly turn a backend implementation detail into a de facto product contract. At the same time, the current artifact flow already proves DB and storage are separate systems: writes happen object-first, and deletes or retention actions can fail independently. Phase 7 should make both of those truths explicit rather than hiding them.

The lowest-risk implementation is therefore three additive slices. First, add one S3-compatible store implementation plus settings-driven factory and resolver dispatch, with the persisted `s3:` URI carrying only the app-owned logical artifact key while bucket and prefix remain config-only. Second, update artifact-service and retention flows so configured-write works for S3, checksums stay local-SHA-based, and delete or prune divergence is left repairable instead of falsely tombstoned or silently orphaned. Third, prove that the existing artifact routes, auth, and docs still hold when the bytes live remotely, and wire the optional env surface into Compose and runbooks without changing the local default.

**Primary recommendation:** keep the persisted remote locator as `s3:{logical_key}` where `{logical_key}` is the same app-owned path shape already used under `local:`. The actual provider object path should be derived as `{configured_prefix}/{logical_key}` inside the S3 backend, with the configured bucket hidden entirely from `storage_uri`. That keeps product surfaces opaque while preserving brownfield compatibility and mixed-read simplicity.

Repo note: `AGENTS.md` was applied. No repository-local `.claude/skills/` or `.agents/skills/` directory exists under the project root.

## Standard Stack

### Core

| Library / Seam | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `boto3` | `>=1.42.91` | S3-compatible client for upload, stream, head, list, and delete | The milestone research already recommends `boto3`, and it matches the AWS-semantics-first decision. |
| `moto[s3]` | `>=5.1.22` | Deterministic S3 test harness | Lets the repo exercise a real S3 client contract in pytest without external infrastructure. |
| Existing `ArtifactObjectStore` protocol | in-repo seam | Backend abstraction for local and S3 stores | Already defines the exact write, stream, list, and delete surface this phase needs. |
| Existing `ArtifactService` + artifact routes | in-repo seam | Persist metadata, stream content, preserve auth boundary | The brownfield-safe path is to keep these as the product boundary and make storage pluggable underneath them. |
| `pytest 8.4.2` via `pytest.ini` | local env | Storage contract, delivery, and retention regressions | Existing backend work already uses pytest and artifact-specific test files. |

### Supporting

| Library / Seam | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `backend/storage/factory.py` + `backend/storage/resolver.py` | in-repo seam | Settings-based write backend and URI-scheme read routing | Use for configured-write plus mixed-read rollout. |
| `backend/maintenance/retention.py` | in-repo seam | Remote-aware prune behavior and error reporting | Use when delete or prune semantics need to remain truthful after remote storage lands. |
| `.env.example`, `docker-compose.yml`, `docs/local-stack.md` | in-repo ops seam | Optional remote-storage configuration without changing local defaults | Use to keep operator setup truthful and reproducible. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Persist logical `s3:` locators with config-owned bucket/prefix | Persist raw `s3://bucket/prefix/key` or provider URLs | Simpler to implement, but it leaks infrastructure details directly into product metadata and weakens the “opaque locator” requirement. |
| Keep app-owned artifact delivery through `/v1/artifacts/*` | Add presigned URLs now | Better for very large objects later, but it widens scope into auth brokering and object identifier exposure before the basic remote contract is proven. |
| Configured-write plus mixed-read | Bulk-migrate all `local:` artifacts before enabling S3 | Operationally noisy and unnecessary for a brownfield rollout. |
| Local SHA-256 on upload | Trust provider ETag as the artifact digest | Incorrect for multipart uploads and many S3-compatible providers; it would break the current checksum contract. |
| Explicit divergence and reconciliation metadata | Pretend DB row changes and blob operations are atomic | False safety; the code already shows they are separate systems. |

## Architecture Patterns

### Pattern 1: Logical `s3:` URIs, Config-Owned Bucket and Prefix

**What:** Persist `storage_uri` as an app-owned logical locator such as `s3:artifacts/analysis_runs/<run_id>/<artifact_id>_panel.csv`, while the actual provider object path is resolved as `{configured_prefix}/{logical_key}` inside the S3 backend.

**When to use:** Every new artifact written through the configured S3 backend.

**Why:** `storage_uri` is surfaced in metadata APIs today. Hiding bucket and provider-specific path details keeps those APIs storage-topology-agnostic and avoids making infrastructure values part of the product contract.

**Recommended contract:**
- `local:` keeps its current meaning and logical key shape.
- `s3:` uses the same logical key shape, not `bucket/key`.
- Bucket, endpoint URL, credentials, region, and prefix live only in settings.

### Pattern 2: Configured-Write, Scheme-Dispatched Mixed-Read

**What:** Use settings to choose the default write backend, but resolve reads and deletes from the scheme stored on each artifact row.

**When to use:** Brownfield rollout where old rows remain `local:` and new rows may be `s3:`.

**Why:** This preserves historical readability without forcing migration and keeps the artifact routes stable.

**Recommended behavior:**
- `ArtifactService` writes through one configured store for this deployment.
- `read_bytes()`, `open_reader()`, and `delete_at_uri()` dispatch by URI scheme.
- A deployment configured for S3 must still read legacy `local:` rows as long as the local blob root exists.

### Pattern 3: Checksum Truth Comes From the App, Not the Provider

**What:** Continue computing and persisting SHA-256 in the app layer during upload.

**When to use:** All local and S3 writes.

**Why:** Current artifact rows already use `content_sha256`, and S3 ETags are not a reliable content hash for multipart or provider-specific implementations.

**Recommended behavior:**
- `StoredObject.sha256_hex` remains the source of truth.
- Route ETags continue to use `content_sha256`.
- Remote uploads compute the digest while streaming, just like the local store already does.

### Pattern 4: Best-Effort Cleanup Plus Explicit Repair State

**What:** Treat upload and delete divergence as a repair flow, not as a hidden implementation detail.

**When to use:** Any object-first write or blob-delete path where Postgres and storage can disagree.

**Why:** The current service already writes the blob before the row and can fail between those steps. Remote storage makes that truth more obvious, not less.

**Recommended behavior:**
- On upload success followed by row-insert failure, attempt best-effort blob cleanup and emit a structured repair signal if cleanup also fails.
- On row-backed delete or retention prune failure, do not mark the row deleted or tombstoned; leave a repair marker in operator-visible metadata instead.
- Only set `blob_deleted_at` after the blob delete actually succeeds.

### Pattern 5: Keep Delivery App-Owned and Generic on Failure

**What:** Continue serving bytes and previews through the FastAPI routes, even when the blob lives in S3.

**When to use:** Normal artifact download and preview behavior in this phase.

**Why:** The app already enforces auth, tenant ownership, retention semantics, and generic failure responses there.

**Recommended route semantics:**
- `200` for successful local or S3 content and preview reads.
- `410` for tombstoned rows before any storage read.
- `404` for unexpected missing blobs without a tombstone.
- `502` for misconfigured or unsupported storage backends, with no bucket or object-key leakage.

## Implementation Slices

### Slice A: Remote Backend Foundation and Scheme Dispatch

Focus files:
- `requirements-backend.txt`
- `requirements-dev.txt`
- `backend/config/settings.py`
- `backend/storage/factory.py`
- `backend/storage/resolver.py`
- `backend/storage/s3.py`
- `tests/test_artifact_storage_s3.py`

Deliver:
- one S3-compatible object store
- settings-driven backend selection
- scheme-dispatched mixed-read resolver
- remote backend contract tests with moto

### Slice B: Artifact-Service and Retention Reconciliation

Focus files:
- `backend/services/artifact_service.py`
- `backend/maintenance/retention.py`
- `tests/test_artifact_storage.py`
- `tests/test_retention_maintenance.py`

Deliver:
- configured-write through the selected backend
- stable logical key layout and SHA-256 persistence for S3 writes
- delete and prune ordering that does not falsely mark success
- explicit repair metadata or reporting for row-backed divergence

### Slice C: Delivery, Metadata, and Ops Documentation

Focus files:
- `backend/api/routes/artifacts.py`
- `tests/test_artifact_content_delivery.py`
- `.env.example`
- `docker-compose.yml`
- `docs/local-stack.md`
- `docs/artifact-delivery.md`

Deliver:
- route regressions proving local and S3 artifacts share the same auth-safe delivery path
- metadata and error semantics that stay opaque and no-leak
- optional Compose and runbook support for remote-storage config while local disk remains the default

## Validation Architecture

Phase 07 only needs one new Wave 0 test file because the repo already has strong local artifact, retention, and delivery coverage.

**Recommended quick command:**
```bash
python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py tests/test_artifact_content_delivery.py tests/test_retention_maintenance.py -q --tb=short
```

**Recommended full command:**
```bash
python3 -m pytest tests/ -q --tb=short
```

**Required new or expanded tests:**
- `tests/test_artifact_storage_s3.py`
  - S3 store put/get/open/list/delete contract
  - settings-driven configured-write plus mixed-read
  - logical `s3:` URIs do not expose configured bucket
- `tests/test_artifact_storage.py`
  - artifact service writes and reads through S3
  - upload cleanup on row-insert failure
  - delete failure leaves repairable row state
- `tests/test_retention_maintenance.py`
  - remote prune success sets `blob_deleted_at`
  - prune failure reports an error and leaves repair state instead of a false tombstone
- `tests/test_artifact_content_delivery.py`
  - S3-backed artifact content and preview route success
  - generic route failures do not leak bucket, key, endpoint, or provider details
  - metadata route keeps `storage_uri` as a logical `s3:` locator

## Pitfalls and Boundaries

- Do not expose raw bucket names or provider object keys in `storage_uri`, docs, or error payloads.
- Do not rely on S3 ETag as the artifact checksum contract.
- Do not change the existing artifact route shape or move delivery to direct object URLs in this phase.
- Do not force historical `local:` artifacts to migrate before S3 can be used.
- Do not set `blob_deleted_at` or delete rows before the blob operation actually succeeds.
- Do not let Compose or docs imply that MinIO or another local object store is newly required; the local default remains filesystem-backed unless the operator opts in.

## Recommended Plan Shape

Phase 07 should be planned as **3 sequential plans**:

1. **Remote backend foundation** — add settings, S3 store, and scheme-dispatched resolver with mixed-read coverage
2. **Artifact-service reconciliation** — make configured-write, checksum, delete, and retention flows truthful across local and S3 backends
3. **Delivery and ops surface** — prove auth-safe routes still work for remote blobs and wire the optional config into runbooks and Compose

This sequence keeps the most structural work first, the divergence-risk logic second, and the route/docs proof last. Each plan can verify the previous one rather than widening scope all at once.

## Sources

### Primary
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md`
- `.planning/research/SUMMARY.md`
- `.planning/research/FEATURES.md`
- `.planning/research/PITFALLS.md`
- `backend/storage/protocol.py`
- `backend/storage/local.py`
- `backend/storage/factory.py`
- `backend/storage/resolver.py`
- `backend/storage/types.py`
- `backend/services/artifact_service.py`
- `backend/api/routes/artifacts.py`
- `backend/models/artifact.py`
- `backend/maintenance/retention.py`
- `tests/test_artifact_storage.py`
- `tests/test_artifact_content_delivery.py`
- `tests/test_retention_maintenance.py`
- `docs/artifact-delivery.md`
- `docs/local-stack.md`
- `.env.example`
- `docker-compose.yml`

### Prior Phases
- `.planning/phases/01-run-isolation/01-CONTEXT.md`
- `.planning/phases/03-secure-defaults/03-CONTEXT.md`
- `.planning/phases/05-storage-and-ops/05-CONTEXT.md`
- `.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md`

---
*Phase: 07-remote-artifact-storage-contract*
*Research completed: 2026-04-18*
