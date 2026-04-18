# Phase 7: Remote Artifact Storage Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 07-Remote Artifact Storage Contract
**Areas discussed:** Canonical S3 target, Cutover model, Opaque locator contract, DB/object-store mismatch handling

---

## Canonical S3 target

| Option | Description | Selected |
|--------|-------------|----------|
| A | Treat standard AWS S3 semantics as the canonical contract while keeping configuration compatible with S3-style endpoints | ✓ |
| B | Treat R2 or MinIO-specific behavior as canonical first and leave AWS compatibility best-effort | |
| C | Design only for a lowest-common-denominator object store with no canonical provider semantics | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted AWS S3 semantics as the planning baseline while keeping endpoint configuration flexible for S3-compatible deployments.

---

## Cutover model

| Option | Description | Selected |
|--------|-------------|----------|
| A | Use configured-write plus mixed-read so new artifacts follow the configured backend while existing `local:` artifacts remain readable | ✓ |
| B | Force a bulk migration of all existing local artifacts before enabling remote storage | |
| C | Dual-write every artifact to both local and remote storage by default | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted the brownfield-safe coexistence model instead of requiring an all-at-once migration or permanent dual-write complexity.

---

## Opaque locator contract

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep `storage_uri` as an app-owned opaque locator rather than a raw bucket/key product contract | ✓ |
| B | Expose bucket names or object keys in admin/debug product surfaces for convenience | |
| C | Make presigned/direct object URLs the normal product contract | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted preserving the existing artifact auth boundary and avoiding bucket-coupled API/UI semantics.

---

## DB/object-store mismatch handling

| Option | Description | Selected |
|--------|-------------|----------|
| A | Treat Postgres and object storage as separate systems and model divergence through explicit reconciliation or repairable states | ✓ |
| B | Assume uploads/deletes and DB row changes are effectively atomic enough in practice | |
| C | Block remote storage unless cross-system atomicity can be guaranteed | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted explicit reconciliation semantics so the phase stays trustworthy even when DB rows and blob storage drift.

---

## the agent's Discretion

- Exact `boto3` configuration and endpoint-shape details
- Exact remote URI scheme and storage-registry wiring
- Exact reconciliation reporting or repair mechanism
- Exact mixed-read/configured-write rollout and regression-test shape

## Deferred Ideas

- Brokered signed URLs for very large artifacts
- Bulk migration/backfill of historic local artifacts
- Multi-cloud/provider orchestration beyond the first S3-compatible backend
