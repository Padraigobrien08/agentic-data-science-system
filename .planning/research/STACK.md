# Stack Research

**Domain:** Agentic Data Science System v1.1 stack delta for live SEC validation, remote object storage, and large-payload trace scaling
**Researched:** 2026-04-18
**Confidence:** HIGH

## Recommended Stack

This milestone does **not** need a new backend framework, queue, cache, or frontend data layer. The right move is a small, explicit stack delta on top of the existing Python + FastAPI + SQLAlchemy + Next.js + Postgres architecture.

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `boto3` | `1.42.91` | Remote S3-compatible artifact storage backend | Official AWS SDK; supports custom `endpoint_url`, so one implementation can cover AWS S3, Cloudflare R2, and self-hosted MinIO-compatible stores without changing the existing `ArtifactObjectStore` contract. `upload_fileobj`/`download_fileobj` match the repo's current stream-oriented artifact path. |
| `requests` | `2.33.1` | Live SEC HTTP client for supported `live` and `hybrid` evaluation runs | Keep the existing synchronous SEC fetch path instead of rewriting to a new HTTP stack. The repo already uses `requests.Session`; the milestone only needs a modern floor plus explicit retry/rate-limit policy. |
| `@tanstack/react-virtual` | `3.13.12` | Virtualized rendering for long step, artifact, and model-call lists on trace/transparency pages | Headless virtualization fits the existing custom trace UI better than a heavyweight grid package and solves DOM blowups without introducing a new client-state architecture. |
| `react-json-view-lite` | `2.5.0` | Collapsible raw JSON inspector for admin/debug payload views | The current `JSON.stringify` panels are the wrong tool for large nested payloads. This package is small, React 18+ compatible, and designed for rendering large JSON trees more safely. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyrate-limiter` | `4.1.0` | Enforce SEC fair-access ceilings in live validation flows | Use around live SEC fetch sessions when intentional validation runs could otherwise burst past the SEC's 10 requests/second guidance. Keep it at the SEC boundary, not as generic middleware for the whole app. |
| `moto[s3]` | `5.1.22` | Test the new S3 backend locally and in CI without real cloud credentials | Use in backend tests for the new object-store implementation, resolver behavior, artifact streaming, and retention cleanup. |
| `boto3-stubs[s3]` | `1.42.89` | Type support for new S3 backend code | Use in development if the team wants stronger typing around S3 client calls. This is optional and should stay out of production runtime dependencies. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Existing `pytest` suite | Validate live/hybrid evaluation runner behavior and S3 backend seams | Add milestone-specific tests under the current backend/evaluation test layout; do not introduce a second Python test runner. |
| Existing `Vitest` + `Playwright` setup | Validate lazy-loading, virtualization, and large-payload trace UX | Reuse the current frontend test stack with large synthetic payload fixtures instead of adding a new browser-test framework. |

## Brownfield Integration Points

| Area | Files / Seam | Recommended change |
|------|--------------|--------------------|
| Live SEC + hybrid evaluation | `src/data_fetch.py`, `config.py`, `edgar_project/evaluation/runner.py`, `edgar_project/evaluation/README.md` | Keep the current `requests`-based SEC fetch path, add explicit retry plus rate-limit control, and implement `live`/`hybrid` inside the existing evaluation runner rather than creating a second validation system. Move SEC identity and throttle settings out of hardcoded config and into deployable settings/env. |
| Remote object storage | `backend/storage/protocol.py`, `backend/storage/factory.py`, `backend/storage/resolver.py`, `backend/services/artifact_service.py` | Add one `S3ObjectStore` implementation and scheme-aware factory/resolver wiring. Keep `Artifact.storage_uri`, artifact API routes, and the DB metadata model intact. |
| Large trace/transparency scaling | `backend/api/routes/runs.py`, `backend/schemas/run_transparency.py`, `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`, `frontend/src/components/ui/technical.tsx` | Stop loading raw payload blobs on first paint. Serve typed summary slices first, add explicit debug-only raw payload fetch-on-expand, virtualize long lists, and render raw JSON as a collapsible tree instead of a single huge `<pre>`. |
| Dependency files | `requirements.txt`, `requirements-backend.txt`, `requirements-dev.txt`, `frontend/package.json` | Runtime additions belong in backend requirements and frontend dependencies; S3 mocks/stubs belong in dev requirements only. |

## Installation

```bash
# Backend runtime additions / upgrades
pip install "boto3==1.42.91" "requests>=2.33.1,<2.34" "pyrate-limiter==4.1.0"

# Backend dev / test additions
pip install "moto[s3]==5.1.22" "boto3-stubs[s3]==1.42.89"

# Frontend additions
cd frontend
npm install @tanstack/react-virtual@^3.13.12 react-json-view-lite@^2.5.0
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `boto3` | `minio` Python SDK | Use `minio` only if the product is permanently MinIO-only and you need MinIO-specific APIs. For this milestone, the code should stay S3-compatible and endpoint-agnostic. |
| `boto3` | `s3fs` / `fsspec` | Use only if the product later needs dataframe/filesystem semantics across many backends. The current artifact layer is object-centric, so these add abstraction without buying anything. |
| `@tanstack/react-virtual` | `react-virtualized` | Use only if you want older prebuilt widgets and accept more bundle weight. The current trace UI is custom and benefits more from a headless hook. |
| Existing server fetch + smaller endpoints | `@tanstack/react-query` | Use only if the trace surface turns into a heavily client-driven app with cache invalidation and optimistic updates. That is not this milestone. |
| `requests` + retry/rate-limit policy | `httpx` rewrite | Use only if the broader repo is moving to async HTTP clients across the whole stack. Right now that would be churn, not leverage. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `aioboto3` as the first object-store implementation | The current storage and artifact service layer is synchronous. Introducing async S3 clients would force wider refactors for little milestone value. | `boto3` inside a sync `S3ObjectStore`. |
| `ORJSONResponse` / `orjson` as the primary fix for trace scaling | FastAPI now documents `ORJSONResponse` as deprecated for performance tuning because response models already serialize efficiently. The real issue in this repo is over-fetching and over-rendering. | Smaller typed endpoints, lazy raw payload fetch, and UI virtualization. |
| MinIO-specific assumptions in application code | This milestone needs remote object storage support, not a permanent vendor commitment. | S3-compatible semantics with configurable `endpoint_url`. |
| Redis, Celery, or Kafka just to support live SEC validation | The repo already has a worker model and an evaluation runner. Adding a new distributed subsystem would expand ops scope far beyond the milestone. | Keep validation in the current worker/evaluation architecture; add limiter state only if real concurrency forces it later. |
| Full raw payload fetch on initial trace page load | The current `/trace` page already asks for `include_payloads=true`; that will keep failing at larger sizes no matter which JSON serializer is used. | Typed summary slices by default and explicit admin/debug raw fetch-on-expand. |
| `react-json-view` / other older heavy JSON viewers | Older packages are heavier or stagnated; they do not fit the "large payload, read-only inspector" need as well. | `react-json-view-lite`. |

## Stack Patterns by Variant

**If the remote object store is AWS S3, Cloudflare R2, or self-hosted MinIO:**
- Use one `boto3`-based `S3ObjectStore`.
- Because `endpoint_url`, credentials, bucket, and prefix configuration are enough to support all three without changing the application contract.

**If live SEC validation is operator-invoked and low concurrency:**
- Keep `requests` with retry adapters and a process-local `pyrate-limiter`.
- Because the SEC cap is simple and the milestone goal is intentional validation, not distributed crawling.

**If live SEC validation will run across multiple worker processes on one host:**
- Use a shared `pyrate-limiter` bucket backend.
- Because per-process sleeps do not protect aggregate host throughput.

**If raw payload inspection must remain available:**
- Keep it admin/debug-only and lazy-load it into a collapsible JSON tree.
- Because the primary trace UX should be typed summaries, not giant opaque blobs.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `boto3==1.42.91` | Python 3.12 repo runtime | PyPI lists Python `>=3.9`, which fits the current backend container and local runtime. |
| `requests>=2.33.1,<2.34` | Python 3.12 repo runtime | PyPI lists Python `>=3.10`; this raises the repo floor without conflicting with the current runtime. |
| `pyrate-limiter==4.1.0` | Python 3.12 repo runtime | PyPI lists Python `>=3.10`. |
| `react-json-view-lite@2.5.0` | React 19 / Next 15 | npm states `2.x` supports React 18 and later, so it fits the current frontend stack. |
| `@tanstack/react-virtual@3.13.12` | React 19 / Next 15 | Current docs and npm package target modern React hooks and fit the repo's current UI architecture. |
| `moto[s3]==5.1.22` | `boto3` S3 backend tests | Test-only dependency; do not ship it in runtime images. |

## Milestone Recommendation

The minimum high-leverage stack delta for v1.1 is:

1. Add `boto3` for one S3-compatible object-store backend.
2. Raise the `requests` floor and add explicit SEC rate-limit policy with `pyrate-limiter`.
3. Add `@tanstack/react-virtual` and `react-json-view-lite` for the trace UI.
4. Add `moto[s3]` for local and CI verification of the new storage path.

Do **not** add a new cache, queue, API layer, or frontend state-management framework for this milestone. The repo already has the right architectural seams; it just needs the right libraries at those seams.

## Sources

- https://www.sec.gov/about/developer-resources — verified SEC fair-access guidance and the current 10 requests/second ceiling
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces — verified `data.sec.gov` JSON APIs, no API keys/auth, and real-time updates during the day
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data — verified declared `User-Agent` requirement and EDGAR index/data API access patterns
- https://docs.aws.amazon.com/boto3/latest/reference/core/session.html — verified `endpoint_url` support for a single S3-compatible implementation
- https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/upload_fileobj.html — verified managed multipart upload from file-like objects
- https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/download_fileobj.html — verified managed multipart download to file-like objects
- https://docs.aws.amazon.com/boto3/latest/guide/retries.html — verified runtime retry modes and cautions
- https://docs.aws.amazon.com/botocore/latest/reference/config.html — verified client config knobs for retries and S3 behavior
- https://pypi.org/project/boto3/ — verified current boto3 version and Python support
- https://pypi.org/project/pyrate-limiter/ — verified current rate-limiter version, Python support, and Requests integration
- https://pypi.org/project/moto/ — verified current S3 mocking version
- https://pypi.org/project/boto3-stubs/ — verified current boto3 type-stub version
- https://www.npmjs.com/package/@tanstack/react-virtual — verified current package version
- https://tanstack.com/virtual/latest — verified package fit for large virtualized React lists
- https://www.npmjs.com/package/react-json-view-lite — verified current package version and React 18+ compatibility
- https://fastapi.tiangolo.com/reference/responses/ — verified that `ORJSONResponse` is deprecated as a performance strategy in modern FastAPI

---
*Stack research for: Agentic Data Science System v1.1 stack delta*
*Researched: 2026-04-18*
