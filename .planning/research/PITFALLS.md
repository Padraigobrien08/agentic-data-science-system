# Pitfalls Research

**Domain:** Brownfield EDGAR analysis platform adding live SEC validation, remote object storage, and large trace/transparency scaling
**Researched:** 2026-04-18
**Confidence:** HIGH

The main milestone risk is not generic reliability work. The repo already hardened run isolation, lease safety, secure defaults, CI, and retention-aware storage. The real danger is undoing those trust boundaries by reusing existing run, artifact, and transparency surfaces for new live and scale features without adding explicit mode, payload, and storage seams.

Suggested future phases used below:

1. **Phase 1: Live Validation Workflow Boundaries**
2. **Phase 2: Remote Object Store Contract**
3. **Phase 3: Large-Payload Trace API Decomposition**
4. **Phase 4: Reconciliation, Rollout, and Scale Verification**

## Critical Pitfalls

### Pitfall 1: Treating live SEC validation as deterministic regression testing

**What goes wrong:**
Live SEC runs get wired into the same pass/fail expectations as fixture-backed regression runs. Fresh filings, SEC indexing lag, and post-acceptance corrections create false regressions, noisy CI, and repeated reruns until something happens to pass.

**Why it happens:**
Brownfield teams reuse the existing run API and test harness because it already works, but forget that live EDGAR data is not stable at the same timescale as fixture data. SEC explicitly notes a current max rate of 10 requests/second, 1-3 minute publication lag under normal conditions, higher lag under load, and later correction/delete behavior in indexes.

**How to avoid:**
Split validation into three modes with separate semantics: fixture regression, hybrid comparison, and live smoke validation. Persist `validation_mode`, observation timestamp, SEC source window, and drift policy on every run. Keep live validations out of merge-blocking CI by default. Compare live runs against tolerances and metadata, not byte-for-byte artifact identity.

**Warning signs:**
The same code and inputs produce different artifact counts or summaries across reruns. Failures cluster around filing publication times. Engineers start describing reruns as the fix. CI is green on fixtures but flaky only on live mode.

**Phase to address:**
Phase 1: Live Validation Workflow Boundaries

---

### Pitfall 2: Letting evaluation traffic pollute normal product runs

**What goes wrong:**
Live and hybrid validation runs appear in the same operator-facing run lists, storage prefixes, metrics, and retention paths as user work. Audit evidence gets mixed with product history, storage costs become noisy, and user-facing trust drops because “system validation” runs look like normal analyses.

**Why it happens:**
The easiest brownfield move is to reuse `AnalysisRun` and existing artifact prefixes with one new flag or none at all. That shortcut preserves compatibility short-term but leaks new semantics into established surfaces.

**How to avoid:**
Give validation workflows explicit identity: mode labels, dedicated project or namespace policy, separate artifact prefixes, retention rules, and metrics dimensions. Default the UI to hide or visually isolate evaluation runs. Make validation evidence queryable without being mistaken for end-user work.

**Warning signs:**
Operators see benchmark or canary runs in normal project histories. Retention jobs delete validation evidence that was supposed to be durable, or preserve validation artifacts longer than user data. Storage dashboards jump with no corresponding increase in user activity.

**Phase to address:**
Phase 1: Live Validation Workflow Boundaries

---

### Pitfall 3: Ignoring SEC fair-access and live-data lag behavior once concurrency increases

**What goes wrong:**
Live validation works in ad hoc local testing, then fails under worker concurrency, scheduled validations, or multi-user load with `Access Denied`, throttling, or inconsistent freshness. The system misclassifies upstream rate limiting or indexing lag as internal product failure.

**Why it happens:**
A brownfield system often already has a working SEC fetch path, but it was tuned for deterministic runs or manual usage. Adding background validation multiplies request rate and turns local assumptions into shared-IP behavior.

**How to avoid:**
Centralize SEC access behind one rate-limited client with declared `User-Agent`, request budgeting, jittered backoff, and lag-aware freshness windows. Distinguish `upstream_degraded`, `stale_source`, and `product_regression` in run outcomes and dashboards. Capture observation time and source endpoint metadata on every live validation run.

**Warning signs:**
403 or `Access Denied` errors appear only when multiple workers run. Validation failures increase during market hours or around new filing bursts. Run health says “error” but manual retry later passes without code changes.

**Phase to address:**
Phase 1: Live Validation Workflow Boundaries

---

### Pitfall 4: Treating remote object storage like a shared filesystem

**What goes wrong:**
Code paths quietly depend on local path semantics, directory walks, temp-file rename assumptions, or immediate filesystem inspection. The remote backend then breaks artifact ingest, delete, preview, or recovery flows that looked correct against `local:` URIs.

**Why it happens:**
The current repo already has a clean local object-store seam, but it still reflects filesystem thinking: `LocalFilesystemStore`, `local:` URIs, and resolver branches that only know one backend. Brownfield migrations usually miss the long tail of path-shaped assumptions outside the core storage interface.

**How to avoid:**
Lock the contract down to object-store operations only: `put`, `open_reader`, `head/read`, `delete`, integrity metadata, and logical key naming. Ban raw filesystem paths from DB rows and UI contracts. Add backend-agnostic contract tests that run against both local and remote stores before introducing migration code.

**Warning signs:**
New code asks the store for a `Path`, shell path, or directory listing. Feature work needs “download to temp file first” for metadata that should be returned by the storage interface. Tests only exercise local storage.

**Phase to address:**
Phase 2: Remote Object Store Contract

---

### Pitfall 5: Assuming the database and object store can be updated atomically

**What goes wrong:**
The system creates orphaned objects with no DB row, DB rows pointing to missing blobs, or retention states that disagree between Postgres and storage. Audit trails become ambiguous because “artifact exists” depends on which system you ask.

**Why it happens:**
Brownfield code often extends the existing transaction boundary outward and mentally treats blob writes like table writes. Remote object storage does not participate in the same ACID transaction as Postgres.

**How to avoid:**
Design explicit dual-write semantics: stable object keys, checksum-first upload, DB row creation after successful upload, reconciliation jobs for orphan detection, and repair tooling for tombstoning or relinking rows. Treat object existence and logical artifact visibility as related but separate states.

**Warning signs:**
Artifact metadata returns successfully but content fetches 404 or 502. Bucket/object counts grow faster than artifact rows. Manual cleanup scripts start appearing. Retention jobs claim success while auditors still find blobs.

**Phase to address:**
Phase 2: Remote Object Store Contract

---

### Pitfall 6: Reusing local integrity and deletion assumptions in S3-style storage

**What goes wrong:**
Large uploads validate against the wrong hash, deletes behave unexpectedly under versioning or Object Lock, and retention reports lie because “deleted” only means “delete marker created” or “logical row hidden.”

**Why it happens:**
Filesystem-backed storage makes it feel natural to equate one file path with one blob and one hash. S3-style storage is different: multipart ETags are not reliable whole-object content hashes, versioning creates multiple object states, and Object Lock can prevent deletion or overwrite.

**How to avoid:**
Persist an explicit content checksum in the product data model and verify against that, not ETag semantics. Make versioning and Object Lock first-class configuration, not invisible infra details. Model logical deletion, physical deletion, and retention lock status separately in the API and ops tooling.

**Warning signs:**
Integrity mismatches happen only on large uploads or KMS-backed objects. “Deleted” artifacts still appear in cloud billing or inventory. Retention workflows pass in application logs but physical bytes remain present or undeletable.

**Phase to address:**
Phase 2: Remote Object Store Contract

---

### Pitfall 7: Trying to fix large trace views in the frontend while keeping monolithic payload APIs

**What goes wrong:**
The UI gets spinners, tabs, or lazy panels, but the server still fetches and serializes huge run payloads up front. Response time, memory pressure, and database load keep climbing because the expensive part is the API contract, not only the DOM.

**Why it happens:**
Brownfield teams optimize the visible symptom first. In this repo, the trace page already loads run details, steps, artifacts, and model calls in parallel, and it asks for raw payloads on the main trace surface. That pattern does not survive large payload growth.

**How to avoid:**
Set payload budgets and split the API into typed summaries by default, with raw payloads behind demand-loaded admin/debug endpoints only. Add pagination or windowing for steps, model calls, and artifacts. Stream route segments with Suspense and ensure the self-hosted proxy path does not buffer streamed responses.

**Warning signs:**
The trace page is slow even when the number of visible components is modest. Next.js server memory or CPU spikes with large runs. Most bytes on the wire are raw JSON the user never expands. Frontend work improves perceived polish but not p95 latency.

**Phase to address:**
Phase 3: Large-Payload Trace API Decomposition

---

### Pitfall 8: Keeping ever-larger trace blobs on hot run rows

**What goes wrong:**
`output_payload_json` and `meta_json` keep absorbing more traceability data, so each run update rewrites large row payloads, increases TOAST usage, and raises lock contention around status transitions or step persistence.

**Why it happens:**
Appending more JSON onto an existing run row is the lowest-migration path in a brownfield system. PostgreSQL supports large JSON documents, but updates still take a row-level lock on the whole row and large values spill through TOAST.

**How to avoid:**
Keep the run row small and summary-oriented. Move large trace slices into append-only child tables or object storage, and persist only compact indexes and typed summaries on the run row. Enforce size budgets on `meta_json` and `output_payload_json`, with alerts when limits are exceeded.

**Warning signs:**
Run update latency rises with payload size. Autovacuum and table bloat grow disproportionately on run tables. Lock waits appear during long executions. Simple run-detail queries get slower even when the artifact store is healthy.

**Phase to address:**
Phase 3: Large-Payload Trace API Decomposition

---

### Pitfall 9: Scaling artifacts and trace delivery through double proxies without new observability

**What goes wrong:**
Large artifact and trace traffic is funneled through FastAPI and then through Next.js proxy routes, so app servers become bandwidth brokers. When object-store latency, buffering, or URL expiry issues appear, health checks stay green while users experience slow or broken downloads.

**Why it happens:**
The current auth model correctly keeps backend credentials off the browser, and the current frontend proxies artifact content through Next.js. That is safe for today’s sizes, but it becomes a scale bottleneck if remote storage and large payload viewing both expand without new delivery strategy and observability.

**How to avoid:**
Decide explicitly which flows stay proxy-based and which should use tightly scoped short-lived delivery URLs or dedicated download channels. Instrument end-to-end artifact latency, response size, proxy buffering behavior, and content delivery error classes. Add synthetic checks that fetch a real retained artifact and a large trace summary through the same user path.

**Warning signs:**
API health is green while artifact downloads are slow or fail. p95 artifact fetch time tracks app-server load rather than object-store load. Next.js instances show high outbound bandwidth and memory pressure during trace-heavy usage.

**Phase to address:**
Phase 4: Reconciliation, Rollout, and Scale Verification

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Reuse normal run records for live validation without a first-class mode boundary | Fastest path to a demo | Polluted audits, mixed retention, misleading metrics, user confusion | Never |
| Keep adding trace data to `analysis_run.output_payload_json` and `meta_json` | No schema change, easy compatibility | TOAST bloat, row lock contention, slow run-detail APIs | Only as a temporary bridge with explicit size caps and a migration date |
| Keep proxying all large artifact and trace traffic through app servers | Preserves current auth pattern | App servers become the bandwidth bottleneck; scale cost moves to the wrong tier | Small previews only |
| Infer object integrity from S3 ETag | Easy to implement | Wrong for multipart and some encrypted objects; false integrity confidence | Never |
| Skip reconciliation because “upload then DB insert is usually fine” | Less initial code | Silent orphan growth and ambiguous audits | Never |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SEC EDGAR live access | Treating the current fetch path as concurrency-safe without centralized throttling or declared user-agent | Use one SEC client policy with request budgeting, declared user-agent, lag-aware retries, and explicit degraded-state handling |
| SEC filing freshness | Assuming acceptance timestamp equals immediate public availability | Record observation time, allow 1-3 minute normal lag, and avoid byte-stable expectations for live mode |
| S3 multipart upload | Assuming ETag is the whole-object checksum or implementing multipart manually without integrity checks | Persist your own checksum, use SDK-managed multipart upload, and verify integrity explicitly |
| S3 retention | Treating delete as final even with versioning or Object Lock | Model logical delete separately and surface versioning/lock-aware retention state |
| Next.js self-hosting | Adding Suspense boundaries but leaving proxy buffering enabled | Configure the deployment path so streaming is not buffered away |
| Brownfield storage migration | Swapping backend config without backend-agnostic contract tests | Prove the same artifact lifecycle against local and remote stores before migration rollout |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Initial trace route loads full run payloads, full steps, full artifacts, and full model-call context | Slow trace loads, server memory spikes, oversized JSON responses | Summary-first APIs, raw payload lazy loading, pagination, and route-level streaming | Once runs carry multi-MB payloads or many steps/artifacts |
| Large JSON blobs are repeatedly merged into the same run row during execution | Lock waits, DB growth, slower status updates | Append-only child records or object-backed raw trace storage | Once long-running runs accumulate large transparency state |
| Artifact delivery stays fully proxy-based across API and Next.js | Good correctness but poor throughput | Keep proxying previews; move bulk delivery to better-fitted channels with strict auth controls | Once retained artifacts are frequently downloaded or previews get large |
| Live validation runs share the same worker pool and request budget as user runs | User work slows down when validations run | Separate queue classes or budgets, and cap live validation concurrency | Once scheduled live validations run alongside normal usage |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Issuing long-lived or over-broad presigned object URLs | Artifact data becomes bearer-token accessible outside intended sessions | Use short TTLs, path-scoped permissions, and audit logs; prefer proxy delivery for small/private views |
| Relaxing bucket access controls to “make the frontend easy” | Private artifacts become publicly reachable or cross-tenant readable | Keep buckets private, use IAM/policy scoping, and preserve server-side authorization boundaries |
| Re-exposing raw run payloads by default while trying to support large trace UIs | Secrets, prompts, or internal debug context leak into normal user flows | Keep raw payload access behind admin/debug gates and summary-first APIs |
| Storing operator contact details or tokens carelessly in validation metadata | Sensitive operational metadata leaks into artifacts, traces, or exports | Minimize stored headers/credentials and redact before persistence |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Live, hybrid, and fixture validations look the same in the UI | Users cannot tell whether drift is expected or alarming | Label mode, observed-at time, and freshness status on every validation run |
| “Upstream degraded” and “product failed” share the same presentation | Operators lose trust and chase the wrong incident | Distinguish upstream lag/rate-limit/dependency issues from product regressions |
| Large trace views default to raw JSON dumps | Users get a technically complete but practically unusable deep dive | Start with typed summaries and linked evidence, then allow drill-down to raw payloads |
| Deleted or retained artifacts are not clearly differentiated from missing artifacts | Users cannot tell whether data expired, failed to upload, or is temporarily inaccessible | Use separate states and copy for expired, missing, locked, and permission-denied artifacts |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Live validation mode:** Missing `validation_mode`, observed-at timestamp, and drift policy on persisted runs.
- [ ] **SEC integration:** Missing centralized rate limiting, declared user-agent, and degraded-state classification.
- [ ] **Hybrid evaluation:** Missing separation between fixture pass/fail rules and live-data tolerance rules.
- [ ] **Remote object store:** Missing backend-agnostic contract tests for upload, preview, read, delete, and retention flows.
- [ ] **Object integrity:** Missing explicit checksum persistence and verification independent of ETag behavior.
- [ ] **Retention:** Missing logical-delete vs physical-delete vs locked-version visibility in the API and ops tooling.
- [ ] **Large trace scaling:** Missing summary-first endpoints, pagination/windowing, and payload budgets.
- [ ] **Streaming UX:** Missing proxy/self-hosting config checks that confirm streaming is not buffered away in production.
- [ ] **Scale observability:** Missing p95 payload size, artifact delivery latency, DB row-size alarms, and orphan reconciliation metrics.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Live SEC validation noise is breaking trust | MEDIUM | Freeze live-mode gating, compare failing runs by observation window and SEC metadata, convert failures to degraded/canary status, and keep fixture regressions as the merge gate |
| DB rows and remote blobs diverged | HIGH | Run reconciliation to classify orphaned rows vs orphaned objects, tombstone broken rows, restore object versions where possible, and backfill integrity metadata |
| Run rows became too large for acceptable trace performance | HIGH | Stop adding raw trace to hot rows, migrate historical raw payloads to child tables or object storage, retain summary fields only, and add size caps before reopening rollout |
| Artifact delivery path is saturating app servers | MEDIUM | Throttle large downloads, shift bulk paths to a better delivery channel, keep previews proxied, and add end-to-end latency instrumentation before re-enabling scale traffic |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Treating live SEC validation as deterministic regression testing | Phase 1 | A run record shows mode, observation time, drift policy, and live runs are excluded from merge-blocking CI by default |
| Letting evaluation traffic pollute normal product runs | Phase 1 | Validation runs can be listed and retained separately from normal user runs |
| Ignoring SEC fair-access and lag behavior once concurrency increases | Phase 1 | Load tests and scheduled validations stay within request budget and classify SEC throttling as upstream degradation |
| Treating remote object storage like a shared filesystem | Phase 2 | The same storage contract tests pass against local and remote backends without path-specific logic |
| Assuming the database and object store can be updated atomically | Phase 2 | Reconciliation tooling can detect and repair orphan rows/objects in a controlled test |
| Reusing local integrity and deletion assumptions in S3-style storage | Phase 2 | Large multipart uploads validate via explicit checksums and delete/retention flows reflect versioning or lock state accurately |
| Trying to fix large trace views in the frontend while keeping monolithic payload APIs | Phase 3 | The primary trace route loads without raw payload flags and raw data is fetched only on demand |
| Keeping ever-larger trace blobs on hot run rows | Phase 3 | Run-row payload size budgets hold under stress and DB lock/bloat metrics remain stable |
| Scaling artifacts and trace delivery through double proxies without new observability | Phase 4 | Synthetic end-to-end checks exercise a large artifact and large trace path with size and latency SLOs |

## Sources

- SEC: Accessing EDGAR Data. https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- SEC: Webmaster Frequently Asked Questions. https://www.sec.gov/about/webmaster-frequently-asked-questions
- AWS: Checking object integrity for data uploads in Amazon S3. https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html
- AWS: Download and upload objects with presigned URLs. https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
- AWS: Retaining multiple versions of objects with S3 Versioning. https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- AWS: Object Lock considerations. https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html
- AWS: What is Amazon S3? https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- PostgreSQL 15 docs: JSON Types. https://www.postgresql.org/docs/15/datatype-json.html
- PostgreSQL 15 docs: TOAST. https://www.postgresql.org/docs/15/storage-toast.html
- Next.js 15 docs: Fetching Data. https://nextjs.org/docs/15/app/getting-started/fetching-data
- Next.js 15 docs: Self-Hosting. https://nextjs.org/docs/15/app/guides/self-hosting
- Repo inspection: `backend/storage/local.py`, `backend/storage/resolver.py`, `backend/services/artifact_service.py`, `backend/api/routes/runs.py`, `backend/api/routes/artifacts.py`, `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`, `frontend/src/app/api/artifacts/[artifactId]/content/route.ts`

---
*Pitfalls research for: Agentic Data Science System v1.1 Live Validation and Scale*
