# Requirements: Agentic Data Science System v1.1

**Defined:** 2026-04-18
**Core Value:** Every EDGAR run must produce trustworthy, isolated, auditable results that the user can inspect without ambiguity.

## v1 Requirements

### Validation Workflows

- [ ] **VALID-01**: Operator can start fixture, hybrid, and live evaluation runs through a supported workflow with mode-specific policy and persisted observation metadata
- [x] **VALID-02**: Operator can inspect case-level validation outcomes with explicit degradation classes that distinguish upstream SEC freshness or availability issues from product regressions
- [x] **VALID-03**: Live SEC validation enforces explicit fair-access controls and does not become a default merge-blocking or user-run path

### Artifact Storage

- [x] **STOR-01**: Operator can configure one S3-compatible remote object-store backend for artifact blobs without changing artifact IDs, authorization rules, or opaque storage URIs in product surfaces
- [x] **STOR-02**: Artifact writes, reads, deletes, and retention workflows preserve checksums, lineage, and audit-visible tombstone or reconciliation state across local and remote backends

### Trace and Transparency

- [ ] **TRACE-01**: User can open large run trace views that load typed summaries first without default full-payload hydration
- [ ] **TRACE-02**: User can search, filter, paginate, or jump through large step, artifact, and model-call collections without overwhelming the browser or API
- [ ] **TRACE-03**: Privileged users can fetch raw payload sections on demand in bounded views instead of receiving all raw trace blobs by default

### Evaluation Control Plane

- [ ] **EVAL-01**: Operator can manage supported evaluation runs and case results as first-class persisted records instead of ad hoc script output
- [ ] **EVAL-02**: Live and hybrid validation cases execute through linked child analysis runs so existing run audit trails, workers, and artifacts remain canonical

### Delivery and Ops

- [ ] **OPS-01**: Health and metrics surfaces report SEC upstream or remote-storage degradation truthfully for supported validation and artifact flows
- [x] **OPS-02**: Users can retrieve large retained artifacts through an authorized delivery path that remains compatible with remote storage without exposing raw bucket or object identifiers

## v2 Requirements

### Validation Expansion

- **VALID-04**: Operator can schedule recurring live canary suites with alerting and explicit request-budget controls
- **EVAL-03**: Operator can promote failing live or hybrid cases into deterministic fixture regressions

### Storage Optimization

- **STOR-03**: Very large artifact downloads can use brokered short-lived delivery URLs when proxy delivery becomes a bottleneck

### Transparency Expansion

- **TRACE-04**: Operator can inspect cross-run evidence-coverage and weak-evidence summaries

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full live SEC suite on every pull request, deploy, or normal user run | SEC fair-access limits and live-data drift would make CI and user workflows noisy instead of trustworthy |
| Exact snapshot assertions against live SEC outputs | Live SEC data changes over time, so exact-value goldens would create false regressions |
| Exposing bucket names, object keys, or long-lived object URLs in product surfaces | The artifact auth boundary must remain app-owned and storage-topology-agnostic |
| Multi-cloud storage orchestration beyond the first S3-compatible backend | v1.1 should prove one remote object-store contract before expanding the backend matrix |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VALID-01 | Phase 9 | Pending |
| VALID-02 | Phase 6 | Complete |
| VALID-03 | Phase 6 | Complete |
| STOR-01 | Phase 7 | Complete |
| STOR-02 | Phase 7 | Complete |
| TRACE-01 | Phase 8 | Pending |
| TRACE-02 | Phase 8 | Pending |
| TRACE-03 | Phase 8 | Pending |
| EVAL-01 | Phase 9 | Pending |
| EVAL-02 | Phase 10 | Pending |
| OPS-01 | Phase 10 | Pending |
| OPS-02 | Phase 7 | Complete |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-04-18 after Phase 7 completion*
