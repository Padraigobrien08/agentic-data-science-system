# Roadmap: Agentic Data Science System

## Milestones

- [x] **v1.0 Hardening** - Phases 1-5 (shipped 2026-04-17)
- [x] **v1.1 Live Validation and Scale** - Phases 6-10 (completed 2026-04-18; ready to archive)

<details>
<summary>[x] v1.0 Hardening (Phases 1-5) - SHIPPED 2026-04-17</summary>

- [x] **Phase 1: Run Isolation** - Isolate every run behind a stable workspace and artifact-path contract.
- [x] **Phase 2: Worker Resilience** - Keep queued execution lease-safe, retry-safe, and auditable on one run identity.
- [x] **Phase 3: Secure Defaults** - Fail closed for auth, ops access, and privileged raw payload exposure.
- [x] **Phase 4: CI Coverage** - Gate the documented stack and critical regressions in pull requests.
- [x] **Phase 5: Storage and Ops** - Make storage and operational surfaces truthful, streamed, and retention-aware.

</details>

## Phases

- [x] **Phase 6: Validation Boundaries and Policy** - Define validation verdicts and safe live-use guardrails before broader rollout.
- [x] **Phase 7: Remote Artifact Storage Contract** - Add one S3-compatible artifact backend behind the existing artifact contract.
- [x] **Phase 8: Summary-First Large Trace Views** - Make large trace inspection fast, bounded, and summary-first.
- [x] **Phase 9: Evaluation Control Plane** - Promote evaluation runs and case results into supported persisted workflows.
- [x] **Phase 10: Live/Hybrid Execution Hardening** - Link live and hybrid validation to canonical runs and truthful ops reporting.

## Phase Details

### Phase 6: Validation Boundaries and Policy
**Goal**: Operators can interpret validation outcomes with explicit degradation taxonomy and keep live validation intentionally gated away from default user and merge workflows.
**Depends on**: Phase 5
**Requirements**: VALID-02, VALID-03
**Success Criteria** (what must be TRUE):
  1. Operator can inspect a validation case and tell whether it degraded because of SEC freshness or availability issues or because the product regressed.
  2. Live SEC validation requires explicit fair-access policy and does not become the default merge-blocking or normal user-run path.
  3. Validation outcomes surface enough policy and degradation context for an operator to decide whether follow-up belongs to upstream monitoring or product debugging.
**Plans**: 3 (completed 2026-04-18)

### Phase 7: Remote Artifact Storage Contract
**Goal**: Users and operators can use remote artifact storage without changing artifact identity, authorization, or audit semantics.
**Depends on**: Phase 6
**Requirements**: STOR-01, STOR-02, OPS-02
**Success Criteria** (what must be TRUE):
  1. Authorized artifact reads and downloads work through the same application-owned delivery path whether blobs live locally or in the configured S3-compatible backend.
  2. Artifact IDs, authorization rules, and opaque storage URIs remain stable even after moving artifact blobs to remote storage.
  3. Artifact writes, deletes, and retention workflows preserve checksums, lineage, and audit-visible tombstone or reconciliation state across local and remote backends.
**Plans**: 3 (completed 2026-04-18)

### Phase 8: Summary-First Large Trace Views
**Goal**: Users can inspect very large runs through summary-first trace views without default full-payload hydration.
**Depends on**: Phase 7
**Requirements**: TRACE-01, TRACE-02, TRACE-03
**Success Criteria** (what must be TRUE):
  1. User can open a large run trace and receive a typed summary view before raw step, artifact, or model-call payloads are fetched.
  2. User can search, filter, paginate, or jump through large step, artifact, and model-call collections without overwhelming the browser or API.
  3. Privileged users can fetch bounded raw payload sections on demand, while standard trace loads stay summary-first by default.
**Plans**: 3 (completed 2026-04-18)
**UI hint**: yes

### Phase 9: Evaluation Control Plane
**Goal**: Operators can start and review supported evaluation workflows through first-class persisted evaluation records.
**Depends on**: Phase 8
**Requirements**: VALID-01, EVAL-01
**Success Criteria** (what must be TRUE):
  1. Operator can start fixture, hybrid, and live evaluation runs through a supported workflow with mode-specific policy and persisted observation metadata.
  2. Operator can list and reopen evaluation runs and their case results as first-class persisted records instead of relying on ad hoc script output.
  3. Operator can revisit stored evaluation history later and still see the run mode, observation metadata, and case-level outcomes captured at execution time.
**Plans**: 3 (completed 2026-04-18)

### Phase 10: Live/Hybrid Execution Hardening
**Goal**: Live and hybrid validation execute through the canonical run infrastructure and report upstream or storage degradation truthfully.
**Depends on**: Phase 9
**Requirements**: EVAL-02, OPS-01
**Success Criteria** (what must be TRUE):
  1. Live and hybrid validation cases execute through linked child analysis runs, and operators can inspect those child runs through the existing run audit trail, workers, and artifacts.
  2. Operator can move from an evaluation case result to its linked child analysis run without relying on separate opaque execution logs.
  3. Health and metrics surfaces report SEC upstream or remote-storage degradation truthfully for supported validation and artifact flows instead of showing false green state.
**Plans**: 3 (completed 2026-04-18)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Run Isolation | 4/4 | Complete | 2026-04-15 |
| 2. Worker Resilience | 3/3 | Complete | 2026-04-16 |
| 3. Secure Defaults | 3/3 | Complete | 2026-04-16 |
| 4. CI Coverage | 3/3 | Complete | 2026-04-17 |
| 5. Storage and Ops | 4/4 | Complete | 2026-04-17 |
| 6. Validation Boundaries and Policy | 3/3 | Complete | 2026-04-18 |
| 7. Remote Artifact Storage Contract | 3/3 | Complete | 2026-04-18 |
| 8. Summary-First Large Trace Views | 3/3 | Complete | 2026-04-18 |
| 9. Evaluation Control Plane | 3/3 | Complete | 2026-04-18 |
| 10. Live/Hybrid Execution Hardening | 3/3 | Complete | 2026-04-18 |
