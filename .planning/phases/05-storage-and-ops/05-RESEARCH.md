# Phase 05: Storage and Ops - Research

**Researched:** 2026-04-17
**Domain:** Backend storage, truthful ops observability, and retention maintenance
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** DB-backed health and metrics surfaces must report dependency degradation explicitly instead of substituting zero or healthy-looking queue values.
- **D-02:** Operator-facing queue truth must distinguish "no work is queued" from "queue state is currently unknown because dependency reads failed."
- **D-03:** Artifact ingestion should move large files into managed storage using streamed copy/hash behavior rather than reading the full file into memory first.
- **D-04:** This phase should preserve the current object-store contract and local storage backend; it is not a remote-storage migration project.
- **D-05:** Operators must be able to bound retained run history and raw model payload history with explicit policy.
- **D-06:** Retention must preserve a minimal auditable record for supported use cases even when raw payloads or stored blobs age out.
- **D-07:** Artifact/blob cleanup should be coupled to retained audit metadata rather than defaulting to aggressive deletion with no trace of what existed.
- **D-08:** Retention should run through an explicit maintenance workflow or job with dry-run and reporting capability, not as hidden deletion inside normal request-path reads or writes.

### Claude's Discretion
- Exact degraded-state schema for `/metrics` and `/v1/worker/health`, as long as dependency failures are explicit and not silently encoded as zero activity
- Exact streamed-ingest mechanics inside the storage abstraction, as long as large-file movement avoids unnecessary full-memory copies
- Exact retention config surface, preserved metadata shape, and operator policy defaults, as long as the required audit trail remains intact
- Exact maintenance trigger or invocation seam, as long as retention remains explicit, testable, and operator-visible

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPER-01 | Health and metrics surfaces report dependency degradation explicitly instead of silently zeroing queue and worker state | Use one shared queue-observability result for both `/v1/worker/health` and `/metrics`; make worker-health counts nullable/unknown on DB failure; add explicit Prometheus health/error metrics and stop zero-filling business gauges. |
| OPER-02 | Artifact ingestion avoids full in-memory copies for large files when moving outputs into managed storage | Extend the storage abstraction with streamed write support; implement temp-file copy plus rolling SHA-256 in `backend/storage/local.py`; make `ArtifactService.ingest_pipeline_file()` delegate instead of calling `Path.read_bytes()`. |
| OPER-03 | Run history and model payload retention can be bounded by policy without losing the audit trail required for supported use cases | Add explicit retention settings and a maintenance module with dry-run/reporting; compact or redact payload-heavy fields in place; add tombstone state for pruned blobs/payloads; add retention tests and migration-backed indexes. |
</phase_requirements>

## Summary

Phase 05 should stay inside the existing backend seams. Queue truth already centralizes around `RunExecutionJobRepository.queue_observability_snapshot()`, artifact ingest already centralizes in `ArtifactService` and `LocalFilesystemStore`, and there is currently no retention workflow at all. The plan should therefore be three additive backend changes, not a platform redesign: one shared degraded-state contract, one streamed storage write path, and one explicit maintenance module.

The most important planning insight is that retention is not just "delete old rows." `AnalysisRun` owns `RunStep`, `ToolCall`, `Artifact`, `ModelCall`, and `RunExecutionJob` relationships with `cascade="all, delete-orphan"`, so deleting a run row would also delete the audit rows this phase is supposed to preserve. Separately, `Artifact.storage_uri` is non-null and artifact delivery currently treats missing bytes as generic storage loss, so blob pruning needs an explicit tombstone state or retained artifacts will look corrupted rather than intentionally expired.

The lowest-risk implementation path is: keep the existing FastAPI + SQLAlchemy + Alembic + local object-store stack, add a shared observability result object for JSON and Prometheus surfaces, add streamed local writes inside the storage abstraction using Python stdlib primitives, and implement retention as an operator-invoked maintenance command with settings-driven policy, dry-run output, and additive tombstone/redaction markers.

**Primary recommendation:** Use shared degraded-state snapshot objects for health and metrics, add a streamed temp-file write API inside `backend/storage`, and implement retention as an explicit settings-driven maintenance module that redacts payloads and prunes blobs only after durable audit tombstones exist.

Repo note: `AGENTS.md` was applied. No `CLAUDE.md`, `.claude/skills/`, or `.agents/skills/` directory was found in the repository root.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | Repo floor `>=0.115.0`; current release `0.136.0` (2026-04-16) | Typed JSON contracts for `/health`, `/v1/worker/health`, and additive retention metadata | Already owns these routes and response models; no new web framework seam is needed. |
| SQLAlchemy ORM | Repo floor `>=2.0.36`; local env `2.0.49`; current release `2.0.49` (2026-04-03) | Queue snapshot queries, retention selectors, batch updates, and same-row compaction | Existing repositories and relationships already encode the product's retention risks and audit ownership rules. |
| Alembic | Repo floor `>=1.14.0`; local env `1.14.0`; current release `1.18.4` (2026-02-10) | Add tombstone/redaction columns and retention indexes safely | Existing schema evolution path; required for explicit retention state rather than implicit missing data. |
| prometheus-client | Repo floor `>=0.21.0`; local env `0.23.1`; current release `0.25.0` (2026-04-09) | Queue gauges, health/error gauges, and retention counters on `/metrics` | Already powers `/metrics`; current docs confirm Gauge semantics remain stable. |
| Python stdlib (`hashlib`, `shutil`, `tempfile`, `os`) | Project runtime `3.12+`; local host `3.11.0` | Streamed local-file ingest, hashing, temp staging, and atomic replace | All required large-file primitives already exist in stdlib; no new storage dependency is justified. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | Repo floor `>=2.0.0`; local env `2.11.0`; current release `2.13.1` (2026-02-19) | Operator retention knobs and maintenance settings | Add `EDGAR_BACKEND_RETENTION_*` settings instead of hard-coded windows. |
| structlog | Repo floor `>=24.4.0` | Maintenance job reporting and degraded-path warnings | Emit explicit event-style logs for retention dry-runs, apply runs, and observability failures. |
| Existing storage abstraction (`ArtifactObjectStore`, `resolver.py`) | In-repo seam | Keep `local:` URI behavior stable while changing write mechanics | All ingest changes should land here so later `PLAT-01` work stays incremental. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing FastAPI + Pydantic health schemas | Ad hoc dict responses | Faster to hack, but increases drift between `/health`, `/worker/health`, and typed clients/tests. |
| Existing local object-store abstraction | Direct filesystem copies in `ArtifactService` or route handlers | Slightly less code now, but it hard-codes local-disk assumptions and bypasses the future storage seam. |
| Explicit maintenance module | Hidden request-path cleanup or an in-process scheduler thread | Lower setup overhead, but violates the locked requirement for dry-run/reporting and creates surprise latency or deletion behavior. |
| Same-row compaction plus tombstones | Hard-delete old `AnalysisRun` rows | Hard-delete is simpler short term, but it triggers ORM cascades and destroys the very audit trail Phase 05 must keep. |

**Installation:**
```bash
pip install -r requirements-dev.txt
```

**Version verification:** No new frontend/npm packages are needed for this phase. Current Python package releases were verified on 2026-04-17 against official PyPI project pages. Local environment versions were probed directly and differ from the repo floors in a few places: FastAPI `0.115.6`, SQLAlchemy `2.0.49`, Alembic `1.14.0`, prometheus-client `0.23.1`, and pydantic-settings `2.11.0`.

## Architecture Patterns

### Recommended Project Structure

```text
backend/
├── api/routes/health.py          # explicit degraded worker-health JSON
├── api/routes/metrics.py         # scrape endpoint stays thin
├── schemas/health.py             # nullable/known-vs-unknown queue fields
├── observability/metrics.py      # queue_observability_up + NaN-on-unknown gauges
├── storage/protocol.py           # add streamed write seam
├── storage/local.py              # temp-file + rolling-hash + atomic replace
├── services/artifact_service.py  # delegate ingest_pipeline_file to storage write API
├── repositories/                 # retention selectors and batch updates
├── maintenance/retention.py      # new explicit dry-run/apply entrypoint
└── config/settings.py            # EDGAR_BACKEND_RETENTION_* knobs
alembic/versions/
└── 010_storage_ops_retention.py  # tombstones, redaction markers, indexes
tests/
├── test_backend_health.py
├── test_artifact_storage.py
├── test_artifact_content_delivery.py
└── test_retention_maintenance.py
```

### Pattern 1: One Queue-Observability Result for JSON and Prometheus

**What:** Introduce one internal result object for queue observability, e.g. `QueueObservabilityResult(ok, snapshot, last_terminal_job_at, error_detail)`, and make both `backend/api/routes/health.py` and `backend/observability/metrics.py` use it.

**When to use:** Any DB-backed queue truth exposed to operators.

**Why:** The repo currently duplicates failure handling and silently collapses errors into zeroes in two places. One shared result prevents route drift and makes degraded-state tests deterministic.

**Recommended contract:**
- `/v1/worker/health` should add a top-level `status` (`ok` or `degraded`), a dependency slice (`database.ok`, `database.detail`), and nullable queue counts when the queue state is unknown.
- `/metrics` should add explicit health/error metrics, e.g. `edgar_worker_queue_observability_up` and `edgar_worker_queue_observability_last_error_unixtime`.
- On failed DB refresh, queue gauges should become `NaN`, not `0`. This is an inference from official Prometheus text-format support for `NaN` plus a local runtime probe showing the current Python client emits `NaN` correctly.

**Example:**
```python
# Sources:
# - https://prometheus.io/docs/instrumenting/exposition_formats/
# - https://prometheus.github.io/client_python/instrumenting/gauge/
# - repo: backend/api/routes/health.py, backend/observability/metrics.py
from math import nan
import time
from prometheus_client import Gauge
from sqlalchemy.exc import SQLAlchemyError

WORKER_QUEUE_OBSERVABILITY_UP = Gauge(
    "edgar_worker_queue_observability_up",
    "1 when DB-backed queue metrics are current, 0 when queue state is unknown",
)
WORKER_QUEUE_OBSERVABILITY_LAST_ERROR_UNIXTIME = Gauge(
    "edgar_worker_queue_observability_last_error_unixtime",
    "Unix time of the most recent queue-observability refresh failure",
)

def refresh_worker_queue_gauges_from_db(session, *, max_attempts: int):
    repo = RunExecutionJobRepository(session)
    try:
        snap = repo.queue_observability_snapshot(max_attempts=max_attempts)
    except SQLAlchemyError as exc:
        WORKER_QUEUE_OBSERVABILITY_UP.set(0)
        WORKER_QUEUE_OBSERVABILITY_LAST_ERROR_UNIXTIME.set(time.time())
        WORKER_QUEUE_DEPTH.set(nan)
        WORKER_QUEUE_PENDING_CLAIMABLE.set(nan)
        WORKER_QUEUE_JOBS_RUNNING_LEASE_OK.set(nan)
        WORKER_QUEUE_JOBS_RUNNING_STALE_LEASE.set(nan)
        WORKER_QUEUE_OPEN_ON_CANCELLED_RUN.set(nan)
        return {"ok": False, "error_detail": str(exc)}

    WORKER_QUEUE_OBSERVABILITY_UP.set(1)
    WORKER_QUEUE_DEPTH.set(snap.pending_claimable)
    WORKER_QUEUE_PENDING_CLAIMABLE.set(snap.pending_claimable)
    WORKER_QUEUE_JOBS_RUNNING_LEASE_OK.set(snap.jobs_running_lease_ok)
    WORKER_QUEUE_JOBS_RUNNING_STALE_LEASE.set(snap.jobs_running_stale_lease)
    WORKER_QUEUE_OPEN_ON_CANCELLED_RUN.set(snap.open_jobs_on_cancelled_run)
    return {"ok": True, "snapshot": snap}
```

### Pattern 2: Stream Writes Inside the Storage Layer, Not in `ArtifactService`

**What:** Extend `ArtifactObjectStore` with a streamed write method such as `put_fileobj()` or `put_path()`, and implement it in `LocalFilesystemStore` using chunked copy, rolling SHA-256, a temp file in the destination directory, and `os.replace()` at the end.

**When to use:** Any ingest path that starts from a file already written by the pipeline.

**Why:** `ArtifactService.ingest_pipeline_file()` currently does `Path.read_bytes()`, which defeats the object-store abstraction and scales peak memory with file size. The fix belongs in storage, not in every caller.

**Example:**
```python
# Sources:
# - https://docs.python.org/3.12/library/shutil.html
# - https://docs.python.org/3.11/library/tempfile.html
# - https://docs.python.org/3.11/library/os.html
# - repo: backend/storage/local.py, backend/storage/types.py
import hashlib
import os
import tempfile
from pathlib import Path

CHUNK_SIZE = 1024 * 1024

def put_fileobj(self, key: str, source, *, content_type: str | None = None) -> StoredObject:
    path = self._abs_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    digest = hashlib.sha256()
    byte_size = 0
    try:
        with os.fdopen(fd, "wb") as tmp:
            while chunk := source.read(CHUNK_SIZE):
                digest.update(chunk)
                tmp.write(chunk)
                byte_size += len(chunk)
        os.replace(tmp_name, path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return StoredObject(
        uri=self.make_uri(key),
        byte_size=byte_size,
        sha256_hex=digest.hexdigest(),
        content_type=content_type,
    )
```

### Pattern 3: Two-Tier Retention with Explicit Tombstones

**What:** Treat retention as two tiers:
- full-fidelity retention: raw model payloads, run payload blobs, and artifact bytes remain available;
- audit retention: rows remain queryable, but raw payloads or blobs are explicitly marked as redacted or pruned.

**When to use:** Only in a maintenance command or job, never in request handlers or worker hot paths.

**Why:** The current schema has no way to tell "intentionally pruned" from "storage broken," and hard-deleting `AnalysisRun` will cascade away child audit history. Same-row compaction plus tombstone markers is the brownfield-safe path.

**Recommended additive schema:**
- `model_calls.payloads_redacted_at TIMESTAMP NULL`
- `artifacts.blob_deleted_at TIMESTAMP NULL`
- `analysis_runs.compacted_at TIMESTAMP NULL` or `analysis_runs.archived_at TIMESTAMP NULL`
- retention indexes on whichever timestamp drives selection, preferably `analysis_runs.finished_at`, `model_calls.created_at`, and `artifacts.created_at`

**Implementation order:**
1. Redact `ModelCall.request_payload_json` and `response_payload_json`, but keep model, prompt ids, token counts, latency, status, timestamps, and error detail.
2. Compact or archive old terminal runs in place rather than deleting the parent row.
3. Prune artifact bytes only after the artifact row carries explicit retention state so metadata routes can still explain what existed.

### Anti-Patterns to Avoid

- **Zero-fill on DB failure:** This is the current bug. It makes degraded state look healthy and invalidates alerts.
- **Separate truth logic in `/v1/worker/health` and `/metrics`:** The semantics will drift again.
- **`Path.read_bytes()` for pipeline artifact ingest:** This makes large-file memory use proportional to artifact size.
- **Direct parent-run deletion for retention:** `AnalysisRun` cascades to every major audit child row.
- **Pruning blobs without a tombstone field:** Current artifact delivery will surface that as generic storage loss.
- **Hidden retention in API or worker request paths:** Violates the locked explicit-maintenance requirement and makes failures harder to reason about.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Prometheus response formatting | Manual text exposition strings | `prometheus_client` metrics plus `generate_latest()` in the existing route | Keeps content type and wire format correct; Phase 05 is about truthfulness, not replacing the metrics library. |
| Storage URI parsing and backend dispatch | File-path branching in services/routes | `ArtifactObjectStore`, `LocalFilesystemStore`, and `resolver.py` | Preserves the current `local:` contract and keeps `PLAT-01` incremental. |
| Background retention scheduler | In-process cron loops or cleanup inside web requests | A dedicated `python -m backend.maintenance.retention` module run by cron/Compose/system scheduler | Matches the locked dry-run/reporting requirement and stays operationally visible. |
| "Pruned" state inference | Convention that missing bytes imply retention | Explicit `*_deleted_at` / `*_redacted_at` state | Makes auditability and troubleshooting possible. |
| New storage backend | S3/MinIO work in this phase | Keep the local filesystem store and local resolver contract | Remote object storage is explicitly deferred to `PLAT-01`. |

**Key insight:** The hard part of this phase is not inventing new infrastructure. It is making existing storage and ops surfaces honest without breaking the brownfield seams that Phase 1-4 already stabilized.

## Common Pitfalls

### Pitfall 1: Silent Unknown -> Zero Collapse

**What goes wrong:** `/v1/worker/health` and `/metrics` report `0` queue depth and no stale jobs when the DB read actually failed.

**Why it happens:** Current exception handlers return zeroed values or set gauges to zero on `SQLAlchemyError`.

**How to avoid:** Introduce explicit degraded-state fields in JSON and explicit health/error metrics in Prometheus; use `NaN` for queue gauges when the value is unknown.

**Warning signs:** Queue gauges stay at zero during DB outages while logs show `worker_queue_gauges_refresh_failed`.

### Pitfall 2: Partial or Corrupt Writes During Streamed Ingest

**What goes wrong:** A failed ingest leaves a partially written object at the final key or a mismatched hash.

**Why it happens:** Streaming directly to the final destination path makes failure cleanup ambiguous.

**How to avoid:** Always stream to a temp file under the destination directory, compute the digest as bytes flow, and finish with `os.replace()`.

**Warning signs:** Zero-byte or truncated artifacts under the target key after a failed ingest test.

### Pitfall 3: Retention Deletes the Audit Trail

**What goes wrong:** Old run cleanup removes run steps, model calls, execution jobs, and artifacts together.

**Why it happens:** `AnalysisRun` relationships are configured with `cascade="all, delete-orphan"`, which is correct for normal run deletion but dangerous for retention.

**How to avoid:** Compact or archive runs in place first; only hard-delete rows if a separate audit representation already exists.

**Warning signs:** A retention prototype deletes one run row and every child record disappears from the DB.

### Pitfall 4: Intentional Pruning Looks Like Storage Corruption

**What goes wrong:** Operators cannot tell whether an artifact blob was pruned by policy or lost unexpectedly.

**Why it happens:** `Artifact.storage_uri` is non-nullable and current delivery routes map missing bytes to a generic 404.

**How to avoid:** Add explicit blob-retention state and surface it in metadata and docs; optionally distinguish intentional expiry in the content route.

**Warning signs:** Support output says only "Artifact content not found in storage" with no retention metadata present on the row.

### Pitfall 5: Retention Jobs Get Slower as the Tables Grow

**What goes wrong:** Maintenance dry-runs or apply runs degenerate into table scans as run history grows.

**Why it happens:** The large tables do not currently have retention-oriented timestamp indexes, and run listing is unpaginated.

**How to avoid:** Add indexes in the same migration as the retention state fields and target only terminal runs for compaction/pruning.

**Warning signs:** SQL query plans show sequential scans on `analysis_runs`, `model_calls`, or `artifacts` for cutoff-based selection.

### Pitfall 6: Local Verification Uses the Wrong Python Runtime

**What goes wrong:** A locally tested implementation behaves differently from the documented stack.

**Why it happens:** The host machine currently has Python `3.11.0`, while the project target and CI use Python `3.12`.

**How to avoid:** Treat Docker/CI Python 3.12 as the authoritative runtime for final validation of this phase.

**Warning signs:** Local-only behavior diverges from CI or Docker results for the same tests.

## Code Examples

Verified patterns from official sources and current repo seams:

### Explicit Degraded Metrics With Unknown Queue Values

```python
# Sources:
# - https://prometheus.io/docs/instrumenting/exposition_formats/
# - https://prometheus.github.io/client_python/instrumenting/gauge/
# - repo: backend/observability/metrics.py
from math import nan

def mark_queue_state_unknown() -> None:
    WORKER_QUEUE_OBSERVABILITY_UP.set(0)
    WORKER_QUEUE_DEPTH.set(nan)
    WORKER_QUEUE_PENDING_CLAIMABLE.set(nan)
    WORKER_QUEUE_JOBS_RUNNING_LEASE_OK.set(nan)
    WORKER_QUEUE_JOBS_RUNNING_STALE_LEASE.set(nan)
    WORKER_QUEUE_OPEN_ON_CANCELLED_RUN.set(nan)
```

### Streamed Local Ingest With Rolling SHA-256

```python
# Sources:
# - https://docs.python.org/3.12/library/shutil.html
# - https://docs.python.org/3.11/library/tempfile.html
# - https://docs.python.org/3.11/library/os.html
# - repo: backend/services/artifact_service.py, backend/storage/local.py
import uuid

def ingest_pipeline_file(self, source_path: Path, *, role_key: str, analysis_run_id: UUID) -> Artifact:
    path = source_path.expanduser().resolve()
    _kind, mime = infer_artifact_kind_and_mime(path)
    artifact_id = uuid.uuid4()
    with path.open("rb") as source:
        stored = self._store.put_fileobj(
            key=self._build_object_key(
                artifact_id=artifact_id,
                role_key=role_key,
                file_suffix=path.suffix,
                analysis_run_id=analysis_run_id,
                evaluation_run_id=None,
            ),
            source=source,
            content_type=mime,
        )
```

### Explicit Dry-Run Maintenance Entry Point

```python
# Sources:
# - repo: backend/worker/__main__.py
# - repo: backend/dev/llm_context_compare.py
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    with SessionLocal() as db:
        report = RetentionMaintenanceService(db, settings=settings).run(dry_run=args.dry_run)
        print(report.to_json(indent=2))
        if not args.dry_run:
            db.commit()
    return 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Whole-file reads followed by `write_bytes()` | Streamed copy plus rolling digest and atomic replace | Python stdlib already supports the required primitives; `hashlib.file_digest` exists in Python 3.11+ | Keeps peak memory bounded and reduces partial-write risk. |
| Silent zero/healthy fallback on dependency read failure | Explicit degraded/unknown signaling in JSON plus explicit health/error metrics in Prometheus | Prometheus text format still explicitly supports `NaN` values in 2026 docs | Operators can distinguish "queue empty" from "queue state unknown". |
| Implicit indefinite payload/blob growth | Policy-driven compaction and pruning through a dry-run maintenance job | Locked by Phase 05 context on 2026-04-17 | Makes storage growth intentional and auditable instead of accidental. |

**Deprecated/outdated:**
- `ArtifactService.ingest_pipeline_file()` using `Path.read_bytes()`: outdated for large outputs because it scales memory with file size.
- Zeroing queue gauges on `SQLAlchemyError`: outdated because it violates the phase's truthfulness requirement.
- Treating missing artifact content as always-corrupt or accidental: outdated once intentional retention exists.

## Open Questions

1. **Should intentionally pruned artifact content return `410 Gone` or stay `404` with metadata flags?**  
What we know: current content routes return `404` when the blob is missing, and there is no tombstone field today.  
What's unclear: whether any existing client or test expects `404` specifically for all missing-content cases.  
Recommendation: prefer explicit tombstone metadata either way; if compatibility allows it, `410 Gone` is the clearest signal for intentional expiry.

2. **What policy defaults should ship in v1?**  
What we know: the phase requires explicit operator-controlled bounds, but there are no existing defaults.  
What's unclear: whether this deployment should prune automatically by default or only when an operator opts in.  
Recommendation: ship conservative defaults that do nothing until configured, but document recommended production windows and example env vars.

3. **Is same-row compaction enough, or does the unpaginated run list require an archived-run seam in this phase?**  
What we know: `GET /v1/runs` returns all owned runs newest-first, with no pagination, and payload compaction alone does not reduce row count.  
What's unclear: expected run volumes for supported deployments.  
Recommendation: plan for same-row compaction first, but keep an additive `archived_at` or `include_archived` seam in scope if list growth is already operationally relevant.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend implementation and tests | ✓ | `3.11.0` | Use Docker/CI Python `3.12` for authoritative validation because the project target is `3.12+`. |
| Pytest | Phase verification | ✓ | `8.4.2` | - |
| Alembic | Retention/tombstone migration work | ✓ | `1.14.0` | - |
| Docker | Full-stack or runtime-parity verification | ✓ | `29.3.1` | Use focused local pytest where full stack is unnecessary. |
| Docker Compose | Full-stack validation and documented stack parity | ✓ | `v5.1.1` | Use CI workflows if local Compose is not practical. |
| `pg_isready` | Local Postgres readiness checks | ✗ | - | Use Docker service health or SQLAlchemy-based test setup. |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- `pg_isready` is not installed locally; use Docker health checks or the existing CI/Postgres workflow instead.
- Host Python is `3.11.0`, below the documented target `3.12+`; use Docker or CI for final verification.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 8.4.2` |
| Config file | `pytest.ini` |
| Quick run command | `python -m pytest tests/test_backend_health.py tests/test_artifact_storage.py -q --tb=short` |
| Full suite command | `python -m pytest tests/ -q --tb=short` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPER-01 | `/metrics` and `/v1/worker/health` show explicit degraded/unknown state when DB-backed queue reads fail | integration | `python -m pytest tests/test_backend_health.py -q --tb=short` | ✅ |
| OPER-02 | Artifact ingest streams large files into managed storage without `read_bytes()`-style full-memory copies and preserves digest/metadata behavior | integration | `python -m pytest tests/test_artifact_storage.py -q --tb=short` | ✅ |
| OPER-03 | Retention dry-run/apply compacts payloads and prunes blobs while preserving audit-visible state | unit/integration | `python -m pytest tests/test_retention_maintenance.py -q --tb=short` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_backend_health.py tests/test_artifact_storage.py -q --tb=short`
- **Per wave merge:** `python -m pytest tests/test_backend_health.py tests/test_artifact_storage.py tests/test_artifact_content_delivery.py tests/test_retention_maintenance.py -q --tb=short`
- **Phase gate:** `python -m pytest tests/ -q --tb=short`

### Wave 0 Gaps

- [ ] `tests/test_backend_health.py` needs degraded-path assertions for nullable JSON fields, explicit status, and metrics `NaN` / `_up` behavior.
- [ ] `tests/test_artifact_storage.py` or a new `tests/test_artifact_ingest_streaming.py` should assert temp-file cleanup, streaming write path usage, and digest correctness for large-source ingest.
- [ ] `tests/test_artifact_content_delivery.py` needs intentional-retention behavior once blob tombstones exist.
- [ ] `tests/test_retention_maintenance.py` is missing and should cover dry-run reporting, payload redaction, blob pruning, audit markers, and idempotent re-runs.
- [ ] Retention-specific API/type assertions may need updates if additive tombstone fields are surfaced on run/model-call/artifact responses.

## Sources

### Primary (HIGH confidence)

- Repository inspection:
  - `backend/api/routes/health.py`
  - `backend/api/routes/metrics.py`
  - `backend/observability/metrics.py`
  - `backend/repositories/run_execution_job_repository.py`
  - `backend/services/artifact_service.py`
  - `backend/storage/local.py`
  - `backend/storage/protocol.py`
  - `backend/storage/resolver.py`
  - `backend/models/analysis_run.py`
  - `backend/models/model_call.py`
  - `backend/models/artifact.py`
  - `backend/api/routes/artifacts.py`
  - `backend/schemas/api_phase_a.py`
  - `backend/config/settings.py`
  - `docs/local-stack.md`
  - `docs/auth-api.md`
  - `tests/test_backend_health.py`
  - `tests/test_artifact_storage.py`
  - `tests/test_artifact_content_delivery.py`
- Prometheus exposition format: https://prometheus.io/docs/instrumenting/exposition_formats/
- Prometheus Python client Gauge docs: https://prometheus.github.io/client_python/instrumenting/gauge/
- Python `hashlib` docs: https://docs.python.org/3.11/library/hashlib.html
- Python `shutil` docs: https://docs.python.org/3.12/library/shutil.html
- Python `tempfile` docs: https://docs.python.org/3.11/library/tempfile.html
- Python `os` docs: https://docs.python.org/3.11/library/os.html
- SQLAlchemy cascade docs: https://docs.sqlalchemy.org/20/orm/cascades.html
- FastAPI PyPI page: https://pypi.org/project/fastapi/
- SQLAlchemy PyPI page: https://pypi.org/project/SQLAlchemy/
- Alembic PyPI page: https://pypi.org/project/alembic/
- prometheus-client PyPI page: https://pypi.org/project/prometheus-client/
- pydantic-settings PyPI page: https://pypi.org/project/pydantic-settings/
- Local runtime verification on 2026-04-17:
  - `prometheus_client` currently emits `NaN` for gauges set to `float("nan")`
  - `hashlib.file_digest` is available in the local Python runtime

### Secondary (MEDIUM confidence)

- None.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - the phase can stay entirely on the existing backend stack, and current package/runtime facts were verified against official PyPI pages and local probes.
- Architecture: HIGH - the recommended seams come directly from current repo structure plus official docs for Prometheus and Python file primitives.
- Pitfalls: HIGH - each major risk is visible in current code or tests, and the most uncertain metric detail (`NaN`) was verified both against official Prometheus docs and a local runtime probe.

**Research date:** 2026-04-17
**Valid until:** 2026-05-17
