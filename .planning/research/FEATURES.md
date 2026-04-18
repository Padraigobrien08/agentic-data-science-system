# Feature Research

**Domain:** v1.1 live validation, remote artifact storage, and large trace/transparency workflows for an EDGAR analysis platform
**Researched:** 2026-04-18
**Confidence:** MEDIUM

Storage and large-trace patterns are HIGH confidence because they map cleanly to official object-storage and UI scaling guidance. Live-validation workflow shape is MEDIUM confidence because it is partly inferred from SEC constraints plus adjacent evaluation products, not from a single SEC-specific product standard.

## Typical Workflow Patterns

### Live validation workflows

- Keep fixture suites as the default regression gate.
- Add a small, curated live suite that operators trigger manually or on a schedule to verify SEC freshness, request-path health, and integration behavior.
- Use hybrid cases to combine stable offline assertions with live-fetch checks; judge live runs on invariants such as availability, schema, artifact presence, timing, and freshness markers, not exact value snapshots.
- Persist live and hybrid results as first-class evaluation runs with case-level outcomes, artifacts, and distinct failure classes so failing live cases can become future deterministic regressions.

### Remote artifact storage

- Keep artifact metadata, lineage, and authorization in the application database; move only blob bytes to object storage.
- Write blobs with streaming uploads, content hashes, scoped object keys, and backend-specific URIs.
- Deliver bytes either through the application's authenticated proxy or through short-lived signed URLs brokered by the app.
- Preserve tombstoned metadata after retention deletes bytes so operators can distinguish policy expiry from unexpected storage loss.

### Large trace and transparency experiences

- Load summaries first: run overview, step summaries, artifact index, and model-call rollups.
- Fetch raw JSON, large payloads, and previews on demand per section.
- Use server-side filtering, pagination, or cursor loading for steps, artifacts, and model calls.
- Give operators jump links, search, and evidence-coverage summaries before exposing raw blobs.

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist once these capabilities are "supported." Missing them makes the milestone feel incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Explicit live and hybrid evaluation entrypoints | "Supported validation" is not credible if `live` and `hybrid` still exist only as skipped modes or ad hoc scripts. | MEDIUM | Extend the existing `edgar_project/evaluation/*` manifests and runner, persist outcomes on `backend/models/evaluation_run.py`, and expose the workflow through the current CLI first, then API/UI. |
| Curated live SEC canary cases | Operators need a small known-good scenario set, not open-ended live traffic, to verify freshness and integration health intentionally. | MEDIUM | Reuse the existing suite/case model; add live-case metadata such as tickers, expected artifact roles, freshness windows, and SEC-specific invariants. |
| Hybrid verdicts with clear failure taxonomy | Live data changes over time, so operators need to know whether a failure is SEC freshness, rate limiting, storage, orchestration, or analytical regression. | HIGH | Build on `summary_json` / `results_json` on `EvaluationRun`; record degraded or skipped classes distinctly instead of flattening everything into generic pass/fail. |
| Remote object-store backend behind the current artifact contract | Moving off shared filesystem storage should not change how users fetch artifacts or how runs reference them. | HIGH | Extend `backend/storage/protocol.py`, `backend/storage/resolver.py`, and `backend/services/artifact_service.py`; keep `Artifact.storage_uri` and `/v1/artifacts/*` as the public contract. |
| Integrity-checked artifact ingest and delivery | Remote blobs must stay auditable and safe to inspect; users expect hashes, byte sizes, and predictable retention behavior to remain trustworthy. | MEDIUM | Preserve `content_sha256`, streaming delivery, and clear 404/410/502 semantics already present in artifact delivery. |
| Summary-first large trace page | Deep-dive transparency must remain usable when run payloads, step counts, and artifact indexes get large. | HIGH | Stop default full-trace hydration from `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`; lean on slim models in `backend/schemas/api_phase_a.py` and `backend/schemas/run_transparency.py`. |
| On-demand drill-down for raw payloads and previews | Operators still need exact evidence, but only when they choose to inspect it. | MEDIUM | Reuse current `include_payloads` and artifact preview/content routes, but fetch detail section-by-section instead of in the initial trace payload. |
| Server-side search, filter, and jump navigation for large runs | Large traces become unusable without a fast way to isolate one step, one artifact role, or one model call. | MEDIUM | Extend the current deep-dive navigation and step/transparency summaries rather than introducing a separate observability product surface. |

### Differentiators (Competitive Advantage)

These are not required to make v1.1 credible, but they meaningfully improve operator trust and product ergonomics.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Scheduled canary live validations with sampling and alerting | Gives continuous freshness and integration confidence without making PR gating or every user run dependent on live SEC traffic. | HIGH | Depends on explicit live suites, failure taxonomy, worker scheduling, and existing metrics/health surfaces. Respect SEC fair-access budgets. |
| Failure-to-fixture promotion loop | Converts real live regressions into permanent deterministic coverage, which is the fastest path to a stronger validation baseline. | MEDIUM | Depends on persisted `EvaluationRun` artifacts plus the existing fixture-first evaluation structure; can begin as operator-assisted export, not full automation. |
| Short-lived signed URL handoff for very large artifacts | Keeps the UI/API responsive for large downloads while preserving application-owned auth and audit decisions. | MEDIUM | Only makes sense after a remote object-store backend exists; the application should broker URLs, not expose long-lived bucket paths. |
| Evidence-coverage and weak-evidence summaries generated at run time | Lets operators judge trustworthiness before opening every raw payload, which matters more as traces get larger. | MEDIUM | Builds on existing `RunTransparencySummary`, `RunStepOutputSummary`, and traceability metadata already present in the backend. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that sound attractive but would create fragility or scope creep in this milestone.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Run the full live suite on every PR, deploy, or user-triggered run | It sounds like maximum confidence. | SEC fair-access limits, upstream instability, and data drift would make CI noisy and user workflows flaky. | Keep fixture suites as the default gate; run curated live canaries manually or on a schedule with explicit budgets and alerting. |
| Exact snapshot or golden assertions against live SEC outputs | It feels objective and easy to automate. | Live SEC responses change over time, so exact-value checks quickly become false regressions. | Assert invariants: request success, freshness bounds, schema/shape, expected artifact roles, bounded counts, and explicit degraded-state handling. |
| Expose raw bucket names, object keys, or long-lived object URLs in the UI/API | It seems convenient for debugging and integrations. | It weakens the auth boundary, leaks storage topology, and hard-couples the product to one storage vendor. | Keep artifact IDs plus proxy delivery first; add brokered short-lived signed URLs only when needed for very large downloads. |
| Load complete run, step, and model payload JSON by default in trace views | It sounds like "full transparency." | It slows large runs, increases memory pressure, and widens the surface area of sensitive retained payloads. | Use summary-first pages, server-side list loading, and explicit detail fetches or admin-gated payload toggles. |

## Feature Dependencies

```text
[Explicit live/hybrid evaluation entrypoints]
    └──requires──> [Curated live SEC canary cases]
                       └──requires──> [Hybrid verdicts with clear failure taxonomy]

[Remote object-store backend]
    └──requires──> [Integrity-checked artifact ingest and delivery]
                       └──enhances──> [Short-lived signed URL handoff]

[Summary-first large trace page]
    └──requires──> [On-demand payload drill-down]
                       └──enhances──> [Server-side search, filter, and jump navigation]

[Failure-to-fixture promotion loop] ──enhances──> [Explicit live/hybrid evaluation entrypoints]

[Full default payload hydration] ──conflicts──> [Summary-first large trace page]
```

### Dependency Notes

- **Explicit live/hybrid evaluation entrypoints require curated live SEC canary cases:** operators need stable scenario IDs and expectations before they can trust scheduled or manual live runs.
- **Curated live SEC canary cases require hybrid verdicts with clear failure taxonomy:** live runs cannot be judged with the same exactness as fixtures, so failure classes must be more expressive than pass/fail.
- **Remote object-store backend requires integrity-checked artifact ingest and delivery:** the storage backend can change only if artifact trust, hashes, retention semantics, and auth-safe delivery stay stable.
- **Short-lived signed URL handoff enhances remote object-store backend:** it is valuable for large downloads, but it is not required to ship the first remote-store implementation.
- **Summary-first large trace page requires on-demand payload drill-down:** inspectability must be preserved, but large traces cannot start by loading every blob eagerly.
- **Server-side search, filter, and jump navigation enhance on-demand drill-down:** once large traces are summary-first, fast narrowing tools become the operator's primary navigation model.
- **Full default payload hydration conflicts with summary-first large trace page:** the current deep-dive fetch posture is the exact behavior this milestone needs to replace.

### Existing Surface Dependencies

- **Validation work should extend, not replace, the current evaluation stack:** `edgar_project/evaluation/README.md`, `edgar_project/evaluation/runner.py`, `edgar_project/cli.py`, and `backend/models/evaluation_run.py` already define the right seam.
- **Remote storage should preserve the current artifact public contract:** `backend/storage/protocol.py`, `backend/storage/resolver.py`, `backend/services/artifact_service.py`, and `/v1/artifacts/*` already separate metadata from blob bytes.
- **Large-trace work should reduce default payload loading, not add a second trace system:** the current trace page and panels already exist in `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` and `frontend/src/components/trace/*`; they need slimmer fetches and better section loading.

## MVP Definition

### Launch With (v1.1)

- [ ] Explicit live and hybrid evaluation runs with curated case manifests, persisted `EvaluationRun` state, case-level result artifacts, and clear skipped/failed/degraded reasons.
- [ ] Remote object-store support that preserves the current artifact metadata model, streaming content routes, checksum fields, and retention tombstone behavior.
- [ ] A large-trace experience that defaults to transparency summaries and lazily loads raw run, step, model-call, and artifact payloads only when an operator expands them.
- [ ] Fast search/filter/jump navigation across steps, artifact roles, and model calls for large runs.

### Add After Validation (v1.x)

- [ ] Scheduled canary live validations with rate-limited sampling and alert routing once the manual workflow is trusted.
- [ ] Short-lived signed URL handoff for very large downloads once the remote-store adapter is stable.
- [ ] Comparison views for fixture vs live vs hybrid runs once enough persisted validation history exists to make comparison useful.

### Future Consideration (v2+)

- [ ] Automatic quarantine and replay workflows for production-discovered validation failures at higher volume.
- [ ] Multi-cloud or tiered object-storage management beyond the first remote backend.
- [ ] Real-time trace streaming, collaborative review, or cross-run observability search as a broader platform feature.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Explicit live and hybrid evaluation runs | HIGH | MEDIUM | P1 |
| Hybrid verdicts with clear failure taxonomy | HIGH | HIGH | P1 |
| Remote object-store backend | HIGH | HIGH | P1 |
| Integrity-checked artifact ingest and delivery | HIGH | MEDIUM | P1 |
| Summary-first large trace page | HIGH | HIGH | P1 |
| On-demand drill-down for raw payloads and previews | HIGH | MEDIUM | P1 |
| Server-side search, filter, and jump navigation | HIGH | MEDIUM | P1 |
| Scheduled canary live validations with alerting | MEDIUM | HIGH | P2 |
| Failure-to-fixture promotion loop | MEDIUM | MEDIUM | P2 |
| Short-lived signed URL handoff | MEDIUM | MEDIUM | P2 |

**Priority key:**

- P1: Must have for this milestone
- P2: Should have once the core milestone features are stable
- P3: Nice to have, future consideration

## Reference Pattern Analysis

These are reference products and platform docs, not direct SEC-analysis competitors, but they show the current pattern language the milestone should follow.

| Feature | Reference A | Reference B | Our Approach |
|---------|-------------|-------------|--------------|
| Offline plus live validation loop | LangSmith separates offline dataset evaluation from online evaluation and promotes a feedback loop from failing production traces back into datasets. | Dagster runs checks inline or on schedules and treats freshness and schema drift as first-class reliability concerns. | Keep fixture-first evaluation as the baseline, add curated live/hybrid SEC canaries, and feed meaningful live failures back into deterministic cases. |
| Large trace UX at scale | Langfuse is moving toward selective field retrieval, cursor-based pagination, and observation-centric tables for large projects. | Modern grid patterns like MUI X use viewport and infinite loading instead of rendering full datasets up front. | Keep the current deep-dive surface, but make it summary-first, server-driven, and section-lazy instead of full-payload by default. |
| Remote artifact delivery | AWS S3 treats checksums, multipart upload, and versioning as standard durability and scale features. | GCS treats signed URLs as time-limited access to a specific object, not a replacement for application auth and metadata. | Keep metadata and auth in the app, use object storage only for blob bytes, and add brokered signed URLs later for large transfers. |

## Sources

- Internal project context:
  - `.planning/PROJECT.md`
  - `edgar_project/evaluation/README.md`
  - `edgar_project/evaluation/runner.py`
  - `backend/models/evaluation_run.py`
  - `backend/storage/protocol.py`
  - `backend/storage/local.py`
  - `backend/storage/resolver.py`
  - `backend/services/artifact_service.py`
  - `backend/schemas/api_phase_a.py`
  - `backend/schemas/run_transparency.py`
  - `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`
- SEC public EDGAR API docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC rate-control / fair-access notice: https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits
- LangSmith evaluation docs: https://docs.langchain.com/langsmith/evaluation
- Dagster data reliability and asset checks: https://dagster.io/blog/ensuring-reliable-data-dagster-plus
- Amazon S3 object integrity: https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html
- Amazon S3 presigned URLs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
- Amazon S3 multipart upload overview: https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html
- Amazon S3 versioning: https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html
- Google Cloud Storage signed URLs: https://docs.cloud.google.com/storage/docs/access-control/signed-urls
- MUI X server-side lazy loading: https://mui.com/x/react-data-grid/server-side-data/lazy-loading/
- Langfuse v4 / fast preview architecture notes: https://langfuse.com/docs/v4

---
*Feature research for: v1.1 live validation, remote artifact storage, and large trace/transparency workflows*
*Researched: 2026-04-18*
