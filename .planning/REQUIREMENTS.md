# Requirements: Agentic Data Science System v1.2

**Defined:** 2026-04-18
**Core Value:** Every EDGAR run must produce trustworthy, isolated, auditable results that the user can inspect without ambiguity.

## v1 Requirements

### Chat Experience

- [x] **CHAT-01**: User can receive the completed analysis answer as a workspace chat message instead of using the standalone run page as the primary place to read the result
- [x] **CHAT-02**: User can read top findings, confidence, and caveats inline within the chat-delivered answer
- [x] **CHAT-03**: User can continue the workspace conversation after a completed run while retaining visible linkage to the run that produced the answer

### Evidence Navigation

- [x] **NAV-01**: User can open report, evidence, artifacts, critic output, and trace links from one compact navigation area attached to the chat answer
- [x] **NAV-02**: User can jump from a finding or caveat in chat to the exact supporting artifact or trace target
- [x] **NAV-03**: User can use a simplified run detail page as a secondary inspection surface focused on verification rather than primary answer reading

### Request Handling

- [x] **PROMPT-01**: User can submit common single-company deterioration or anomaly requests in normal analyst phrasing without unsupported-intent failures
- [x] **PROMPT-02**: User can submit common peer-comparison requests in normal analyst phrasing without unsupported-intent failures
- [x] **PROMPT-03**: When a request still cannot map to a supported analysis path, user sees actionable rewrite guidance instead of a dead-end error

### Runtime Reliability

- [x] **RUN-01**: User can launch a chat-driven run in the documented Compose stack without run-workspace permission failures
- [x] **RUN-02**: User can rely on queued/background execution in the documented Compose stack because the worker starts cleanly and can claim work
- [x] **RUN-03**: User can see truthful chat-visible status when background delivery is degraded or unavailable

## v2 Requirements

### Onboarding

- **AUTH-01**: User sees environment-aware account-creation and bootstrap guidance instead of dead-end registration paths in secure-default deployments

### Chat Expansion

- **CHAT-04**: User can compare or revisit multiple prior runs from one conversation without leaving the workspace thread

### Deep-Dive Enhancements

- **NAV-04**: User can curate grouped evidence bundles from findings for later review or sharing

## Out of Scope

| Feature | Reason |
|---------|--------|
| New anomaly-detection models or broader financial-analysis feature work | This milestone is about answer delivery, prompt routing, and runtime reliability, not expanding the analytical model surface |
| Full redesign of every trace, artifact, and evaluation screen | The priority is moving primary reading into chat; deep-dive pages only need enough simplification to become secondary inspection surfaces |
| Mobile, push notifications, or standalone messaging clients | The immediate problem is the web workspace experience, not expanding to additional client platforms |
| Broader live-validation or onboarding programs beyond the immediate chat flow blockers | Those remain valuable, but they are not the fastest path to a coherent chat-first answer experience |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHAT-01 | Phase 14 | Complete |
| CHAT-02 | Phase 15 | Complete |
| CHAT-03 | Phase 14 | Complete |
| NAV-01 | Phase 15 | Complete |
| NAV-02 | Phase 15 | Complete |
| NAV-03 | Phase 16 | Complete |
| PROMPT-01 | Phase 13 | Complete |
| PROMPT-02 | Phase 13 | Complete |
| PROMPT-03 | Phase 13 | Complete |
| RUN-01 | Phase 12 | Complete |
| RUN-02 | Phase 12 | Complete |
| RUN-03 | Phase 12 | Complete |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-04-19 after Phase 16 completion*
