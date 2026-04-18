# Architecture Research

**Domain:** Brownfield EDGAR platform extension for v1.1 live validation, remote object storage, and large trace scaling
**Researched:** 2026-04-18
**Confidence:** HIGH

## Standard Architecture

### System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                     Operator / Analyst Surfaces                     │
├──────────────────────────────────────────────────────────────────────┤
│  Next.js run answer  │  Next.js trace sections  │  Validation UI    │
│  artifact proxy      │  loading.tsx + Suspense  │  suite history    │
└──────────────┬───────────────────────┬───────────────────────┬──────┘
               │                       │                       │
┌──────────────▼───────────────────────▼───────────────────────▼──────┐
│                          FastAPI Product API                         │
├──────────────────────────────────────────────────────────────────────┤
│ runs router (summary / trace sections / raw debug)                  │
│ evaluations router (suite lifecycle / case results / links)         │
│ artifacts router (preview / stream / presigned download redirect)   │
│ health router (db + storage backend truth)                          │
└──────────────┬───────────────────────┬───────────────────────┬──────┘
               │                       │                       │
┌──────────────▼───────────────────────▼───────────────────────▼──────┐
│                    Services / Worker Control Plane                   │
├──────────────────────────────────────────────────────────────────────┤
│ EdgarPipelineExecutionService      │ existing run execution          │
│ EvaluationExecutionService         │ NEW suite / case orchestration  │
│ TraceProjectionService             │ NEW lightweight read models     │
│ ArtifactService + ObjectStoreRegistry │ local + S3 backend switch    │
└──────────────┬───────────────────────┬───────────────────────┬──────┘
               │                       │                       │
┌──────────────▼───────────────────────▼───────────────────────▼──────┐
│             Orchestration / Deterministic Analytical Core            │
├──────────────────────────────────────────────────────────────────────┤
│ edgar_project/evaluation runner/checks  │ AnalysisAgent / MCP tools  │
│ src/ deterministic SEC fetch + features │ report / anomaly pipeline  │
└──────────────┬───────────────────────┬───────────────────────┬──────┘
               │                       │                       │
┌──────────────▼───────────────────────▼───────────────────────▼──────┐
│                     Data / Storage / External Systems                │
├──────────────────────────────────────────────────────────────────────┤
│ Postgres: analysis_runs, run_steps, artifacts, model_calls,         │
│           evaluation_runs, NEW evaluation_case_results              │
│ Object store: local filesystem (existing) or S3-compatible (new)    │
│ SEC APIs: data.sec.gov + Archives, rate-limited and identified       │
└──────────────────────────────────────────────────────────────────────┘
```

### New Components

| Component | Responsibility | Why it should exist |
|-----------|----------------|---------------------|
| `backend/api/routes/evaluations.py` | Operator-facing API for suite creation, case progress, reruns, and result retrieval | `EvaluationRun` exists in the schema but is not yet a supported product surface |
| `backend/services/evaluation_execution_service.py` | Owns suite lifecycle, case fan-out, status aggregation, and retries | Keeps validation workflow orchestration out of `edgar_project/evaluation/runner.py` and out of run routes |
| `backend/models/evaluation_case_result.py` | Persists one row per benchmark case with `analysis_run_id` link when applicable | Avoids stuffing all supported workflow results into `evaluation_runs.results_json` blobs |
| `backend/services/trace_projection_service.py` | Builds compact trace summaries and section payloads without loading raw blobs by default | Large trace pages need a read model, not direct rendering from monolithic JSON |
| `backend/storage/s3.py` | S3-backed `ArtifactObjectStore` implementation using managed upload/download APIs | The storage seam already exists; remote backend should be a first-class implementation, not special-case code in routes |
| `backend/storage/registry.py` | Resolves write backend from settings and read backend from `storage_uri` scheme | `factory.py` and `resolver.py` are currently local-only |
| `frontend/src/app/projects/[projectId]/validations/` | Validation dashboard, suite detail, and case drill-down routes | Live validation should be intentional and inspectable, not hidden in CLI-only flows |
| `frontend/src/components/trace/sections/` | Independently loaded trace sections with focused loading states | Trace UI must stop assuming one giant server render payload |

### Modified Components

| Component | Change | Integration impact |
|-----------|--------|--------------------|
| `edgar_project/evaluation/runner.py` | Keep checks/scoring logic, but delegate live and hybrid execution to backend services instead of skipping or calling `src` ad hoc | Preserves existing benchmark semantics while validating the real product path |
| `backend/services/edgar_pipeline_execution_service.py` | Accept evaluation context metadata on child runs and expose stable links back to the parent suite/case | Live and hybrid cases should reuse the exact run execution path already used by operators |
| `backend/services/artifact_service.py` | Replace `get_local_object_store()` defaulting with registry-based backend selection; preserve opaque `storage_uri` writes | Existing artifact persistence remains intact while gaining remote storage |
| `backend/storage/factory.py` and `backend/storage/resolver.py` | Support multiple schemes, `head`-style metadata access, and optional presign helpers | Needed for remote reads, health checks, and efficient artifact delivery |
| `backend/api/routes/artifacts.py` | Authorize first, then choose preview stream, API proxy stream, or short-lived presigned redirect based on backend and artifact size | Prevents the API from becoming the bottleneck for every large remote download |
| `backend/api/routes/runs.py` | Add summary/section trace endpoints and avoid raw payload selection on normal trace loads | Current `/runs/{id}` plus `/steps` pattern is too coarse for large payloads |
| `backend/api/routes/health.py` | Include storage backend readiness/degraded reporting | Operational clarity requires truthful storage status, not DB-only green checks |
| `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` | Fetch trace summary first, then stream/lazy-load sections and raw debug panels separately | Current page eagerly pulls payload-heavy run, steps, artifacts, and model calls in one request batch |

## Recommended Project Structure

```text
backend/
├── api/routes/
│   ├── evaluations.py          # NEW: suite lifecycle and case-result APIs
│   ├── runs.py                 # MOD: trace summary/section endpoints
│   ├── artifacts.py            # MOD: remote-store delivery modes
│   └── health.py               # MOD: storage backend truth
├── models/
│   ├── evaluation_run.py       # existing suite parent
│   └── evaluation_case_result.py  # NEW: one persisted row per case
├── services/
│   ├── evaluation_execution_service.py  # NEW: case fan-out + status aggregation
│   ├── evaluation_run_service.py        # NEW: CRUD / lifecycle helpers
│   ├── trace_projection_service.py      # NEW: trace read-model builder
│   ├── artifact_service.py              # MOD: backend-agnostic writes
│   └── edgar_pipeline_execution_service.py  # MOD: child run linkage
├── storage/
│   ├── s3.py                   # NEW: remote object-store implementation
│   ├── registry.py             # NEW: scheme/backend lookup
│   ├── factory.py              # MOD: configured write backend
│   └── resolver.py             # MOD: scheme-based read/delete/head
└── schemas/
    ├── evaluation_api.py       # NEW: suite + case DTOs
    └── run_trace.py            # NEW: summary/section DTOs

edgar_project/
└── evaluation/
    ├── runner.py               # MOD: fixture checks stay here; live/hybrid delegate
    ├── live_case_executor.py   # NEW: adapter for child analysis runs
    └── result_scoring.py       # NEW: shared case verdict assembly

frontend/src/
├── app/projects/[projectId]/validations/   # NEW validation surface
├── components/validations/                 # NEW suite/case UI
├── components/trace/sections/              # NEW lazy trace sections
└── lib/api/
    ├── evaluations.ts                      # NEW validation API client
    └── runs.ts                             # MOD trace summary/section fetchers
```

### Structure Rationale

- **`backend/services/evaluation_*`:** Put supported validation workflow logic inside the product service layer, not inside CLI-only code, so API, worker, and tests share the same control plane.
- **`backend/storage/registry.py`:** A scheme registry is cleaner than sprinkling `if uri.startswith("s3:")` across routes and services.
- **`backend/services/trace_projection_service.py`:** Large trace scaling is a read-model problem; isolate it so UI payload shaping does not leak into execution services.
- **`frontend/src/components/trace/sections/`:** The current trace page is monolithic; section components make Suspense/lazy loading practical without redesigning the whole UI tree.

## Architectural Patterns

### Pattern 1: Parent Evaluation Run, Child Analysis Runs

**What:** Treat `EvaluationRun` as the operator-facing suite container and `AnalysisRun` as the execution unit for any live or hybrid case. Fixture-only cases remain evaluation-only, but live and hybrid cases link to a child `analysis_run_id`.

**When to use:** Any supported validation case that must prove the real SEC/MCP/backend/frontend execution path, not just deterministic fixture scoring.

**Trade-offs:** This adds one more table and join path, but it preserves the system’s core audit model instead of inventing a second execution record format.

**Example:**
```python
# New evaluation control-plane flow
suite = evaluation_run_service.create(project_id=project_id, suite_id="live_smoke_v1")
case = case_result_service.start(suite.id, case_id="aapl_live", input_mode="live")

run = analysis_run_service.create(
    project_id=project_id,
    orchestration_goal_text=case.goal,
    input_payload_json={"tickers": case.tickers, "refresh": case.refresh},
    meta_json={"evaluation": {"evaluation_run_id": str(suite.id), "case_id": case.case_id}},
)
run_queue_service.enqueue_after_create(run.id)
case_result_service.link_analysis_run(case.id, run.id)
```

### Pattern 2: Scheme-Based Object Storage With API-Owned Authorization

**What:** Keep `Artifact.storage_uri` opaque and backend-specific (`local:` now, `s3:` next). The API remains the authorization layer. The object store implementation only handles bytes, metadata lookup, and optional presigned delivery.

**When to use:** All artifact writes and reads, especially once API and worker no longer share a single filesystem reliably.

**Trade-offs:** Delivery logic becomes slightly more complex, but it preserves compatibility with existing artifact rows and keeps security decisions out of the bucket itself.

**Example:**
```python
store = object_store_registry.for_write(settings)
stored = store.put_fileobj(
    key=artifact_key,
    source=fh,
    content_type=mime_type,
)
# Persist stored.uri on Artifact.storage_uri; routes later resolve by scheme.
```

### Pattern 3: Small Summary First, Heavy Trace Sections On Demand

**What:** Replace the current "load raw run payloads, all steps, all artifacts, and all model calls up front" trace page with a summary endpoint plus section endpoints for steps, artifacts, model calls, report evidence, and raw debug blobs.

**When to use:** Every trace/transparency surface outside explicit admin debug mode.

**Trade-offs:** More API endpoints and slightly more UI plumbing, but far lower latency and memory use for large runs.

**Example:**
```typescript
// Server page
const summary = await getRunTraceSummary(runId);

return (
  <>
    <TraceOverview summary={summary} />
    <Suspense fallback={<StepsSkeleton />}>
      <TraceStepsSection runId={runId} />
    </Suspense>
    <Suspense fallback={<ArtifactsSkeleton />}>
      <TraceArtifactsSection runId={runId} />
    </Suspense>
  </>
);
```

### Pattern 4: Shared SEC Access Policy for Live Validation

**What:** All live and hybrid validation traffic should reuse the same SEC client policy already present in `src/data_fetch.py`: declared `User-Agent`, bounded request rate, refresh-aware caching, and captured raw responses.

**When to use:** Any case that touches `data.sec.gov` or `www.sec.gov/Archives`.

**Trade-offs:** Lower peak concurrency, but it is compliant and predictable. This matters more than raw throughput because the SEC explicitly limits automated access.

## Data Flow

### Live / Hybrid Validation Flow

```text
[Operator starts suite]
    ↓
POST /v1/evaluations
    ↓
EvaluationExecutionService creates EvaluationRun + case rows
    ↓
For live/hybrid cases:
EvaluationExecutionService → AnalysisRunService / RunQueueService
    ↓
Worker → EdgarPipelineExecutionService → AnalysisAgent / MCP / src/*
    ↓
ArtifactService → ObjectStoreRegistry → local or S3 backend
    ↓
Case scorer reads child run status + artifacts + checks
    ↓
evaluation_case_results updated
    ↓
EvaluationRun summary/status updated
```

### Remote Artifact Storage Flow

```text
[Pipeline or evaluation case produces file]
    ↓
ArtifactService builds object key + role metadata
    ↓
Configured object store writes bytes (`put_fileobj`)
    ↓
Artifact row stores opaque `storage_uri`
    ↓
Artifact request hits FastAPI
    ↓
Auth check against DB row ownership
    ↓
preview → API bounded read
download → API stream or short-lived presigned redirect
```

### Large Trace / Transparency Flow

```text
[User opens /runs/{id}/trace]
    ↓
Trace summary endpoint (no raw payloads)
    ↓
Next.js renders shell immediately
    ↓
Section components fetch:
steps (paged) / artifacts / model calls / report evidence
    ↓
Raw `output_payload_json` or `meta_json` fetched only from explicit debug endpoints
```

### State Management

```text
URL params / route segments
    ↓
Server Components fetch compact trace summary
    ↓
Suspense boundaries fetch section payloads independently
    ↓
Client widgets keep only local UI state (expanded rows, active tab, cursor)
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current hardened stack / low operator count | Keep monolith, one worker pool, local filesystem for dev, remote store optional |
| Multi-user self-hosted deployment / larger run payloads | Remote object store becomes default for non-dev, trace summary endpoints replace raw trace loads, evaluation runs use background execution |
| High validation volume or very large artifacts | Split worker concurrency by queue type (`analysis` vs `evaluation`), prefer presigned downloads for large artifacts, add pagination/cursors for steps and model calls, consider async projection generation for trace sections |

### Scaling Priorities

1. **First bottleneck:** Trace pages currently over-fetch JSON and per-run related rows. Fix this with summary/section endpoints plus SQLAlchemy field deferral for raw JSON columns on non-debug paths.
2. **Second bottleneck:** API-proxied artifact delivery becomes expensive once storage is remote. Fix this with `head_object`, ranged reads for previews, and short-lived presigned download redirects for large files.

## Anti-Patterns

### Anti-Pattern 1: Running Supported Live Validation Outside the Product Control Plane

**What people do:** Add live/hybrid logic directly inside `edgar_project/evaluation/runner.py` that calls `src` or SEC fetch helpers and writes local files.

**Why it's wrong:** It bypasses persisted `AnalysisRun` audit trails, worker retry semantics, artifact registration, and the run trace model the rest of the product depends on.

**Do this instead:** Let the evaluation layer schedule or invoke real `AnalysisRun`s for live/hybrid cases, then score the persisted outputs.

### Anti-Pattern 2: Treating the Bucket URL as the Product Contract

**What people do:** Store raw HTTPS URLs or leak bucket/object paths to the UI and let the browser fetch them directly.

**Why it's wrong:** It breaks the existing `storage_uri` abstraction, couples the product to one provider layout, and pushes authorization into infrastructure instead of the app boundary.

**Do this instead:** Keep DB metadata and `storage_uri` authoritative; authorize in FastAPI, then stream or presign only after access checks pass.

### Anti-Pattern 3: Rendering Trace Pages From Raw Payload Blobs by Default

**What people do:** Fetch `include_payloads=true` run data plus all steps, artifacts, and model calls for every trace view.

**Why it's wrong:** Large runs will pay the latency and memory cost even when the user only needs summary context, and the current page shape blocks progressive rendering.

**Do this instead:** Serve typed summaries first and move raw payload fetches into explicit debug affordances.

### Anti-Pattern 4: Keeping Supported Case Results Only in `evaluation_runs.results_json`

**What people do:** Persist all case output inside one big JSON blob on the parent run.

**Why it's wrong:** It prevents paging, filtering, per-case retry, and durable links to child analysis runs.

**Do this instead:** Add a case-result table and use the parent `EvaluationRun` only for aggregate state.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| SEC `data.sec.gov` and EDGAR archives | Shared SEC client with declared `User-Agent`, bounded request rate, refresh flag, and raw capture reuse | Official SEC guidance limits automated access to 10 requests/second and requires declared user-agent headers |
| Amazon S3 API remote object store | `upload_fileobj` for writes, `head_object` for metadata/readiness, `get_object` for streamed reads, presigned GET/HEAD for large downloads | Use S3 API semantics as the contract; validate non-AWS endpoint compatibility against the chosen deployment target |
| Local filesystem object store | Keep as existing default for local development and focused tests | Preserves current workflows and gives a migration path instead of a forced cutover |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `edgar_project/evaluation` ↔ `backend/services/evaluation_execution_service.py` | Direct service API | Runner keeps scoring logic; backend service owns persisted workflow control |
| `EvaluationExecutionService` ↔ `EdgarPipelineExecutionService` | Direct service call or queued child `AnalysisRun` | Reuse the same execution path used by product runs |
| `ArtifactService` ↔ `backend/storage/*` | Protocol + registry | Storage backend choice must stay behind a stable interface |
| `backend/api/routes/runs.py` ↔ `TraceProjectionService` | Typed DTOs | Summary endpoints should not expose raw payload internals as their primary contract |
| Next.js trace routes ↔ FastAPI trace/artifact routes | Server-side fetch via existing BFF pattern | Use `loading.tsx` and Suspense so large trace sections stream in independently |

## Suggested Build Order

1. **Remote storage foundation**
   - Add `S3ObjectStore`, storage registry, config, and storage health reporting.
   - Keep local storage as the default in dev and tests.
   - Rationale: this is the cleanest existing seam and unblocks shared deployment scale without touching deterministic analysis logic.

2. **Trace read-model decomposition**
   - Add trace summary/section APIs, defer raw JSON columns on normal reads, and move the Next trace page to Suspense-based section loading.
   - Keep raw debug payload endpoints separate and explicit.
   - Rationale: large-payload inspection is already a pain point and will only get worse once live validation becomes common.

3. **Validation control plane**
   - Add `EvaluationRunService`, `EvaluationExecutionService`, `evaluation_case_results`, and evaluation APIs/UI.
   - Initially support fixture runs through the new control plane to prove lifecycle, auth, and result rendering.
   - Rationale: establish the operator-facing workflow boundary before adding live SEC execution complexity.

4. **Live and hybrid case execution**
   - Teach the evaluation layer to create/link child `AnalysisRun`s for live/hybrid cases, reuse existing worker execution, and score persisted artifacts/results.
   - Add SEC-aware concurrency caps and explicit freshness metadata per case.
   - Rationale: by this point the storage, UI, and control-plane seams are in place, so live execution lands as an additive adapter instead of a cross-cutting rewrite.

5. **Operational hardening**
   - Add compose/browser/live smoke coverage for remote storage, suite execution, and trace-section loading.
   - Alert on degraded storage backend, stuck evaluation cases, and SEC throttling/fair-access failures.
   - Rationale: supported live validation is only credible if ops surfaces report the real failure mode.

## Sources

- Existing codebase seams:
  - `backend/storage/protocol.py`, `backend/storage/resolver.py`, `backend/services/artifact_service.py`
  - `backend/models/evaluation_run.py`, `edgar_project/evaluation/runner.py`, `backend/api/routes/runs.py`
  - `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`, `frontend/src/components/trace/run-trace-experience.tsx`
- SEC: Accessing EDGAR Data — rate limit and user-agent declaration: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- SEC: EDGAR API docs — real-time updates, nightly bulk ZIPs, API surface: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC: Developer Resources — fair-access guidance: https://www.sec.gov/about/developer-resources
- AWS S3 presigned URLs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
- AWS S3 performance guidelines (`Range`, concurrency, retries): https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance-guidelines.html
- Boto3 `upload_fileobj`: https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/upload_fileobj.html
- Boto3 `get_object`: https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_object.html
- Boto3 `head_object`: https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/head_object.html
- Next.js Route Handlers: https://nextjs.org/docs/app/getting-started/route-handlers
- Next.js loading and streaming in the App Router: https://nextjs.org/docs/app/getting-started/linking-and-navigating

---
*Architecture research for: Agentic Data Science System v1.1 Live Validation and Scale*
*Researched: 2026-04-18*
