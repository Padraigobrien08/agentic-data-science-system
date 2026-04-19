# Roadmap: Agentic Data Science System

## Milestones

- [x] **v1.0 Hardening** — shipped 2026-04-17 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.0-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.0-REQUIREMENTS.md)
- [x] **v1.1 Live Validation and Scale** — shipped 2026-04-18 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-REQUIREMENTS.md) · [audit](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-MILESTONE-AUDIT.md)
- [ ] **v1.2 Chat-First Analysis Experience** — active

## Active Planning

### Milestone v1.2: Chat-First Analysis Experience

**Goal:** Make workspace chat the primary place where users receive, inspect, and continue analysis answers, while fixing the delivery and prompt-handling seams that currently break that experience.

**Phases:** 12-16  
**Requirements:** 12 mapped

### Phase 12: Runtime Reliability for Chat Delivery

**Goal**: Users can rely on the documented local stack to create run workspaces, execute runs, report background-delivery degradation truthfully, and enter the product through capability-aware onboarding before chat becomes the primary answer surface.  
**Depends on**: Phase 11 milestone archive baseline  
**Plans**: 3/3 completed  
**Completed**: 2026-04-18

**Details:**
- Requirements: `RUN-01`, `RUN-02`, `RUN-03`
- Success criteria:
  1. Compose-backed run execution no longer fails on run-workspace creation or other local runtime setup gaps.
  2. The worker process starts cleanly and can claim queued work in the documented stack.
  3. The UI and health surfaces report background-delivery degradation clearly instead of implying queued chat delivery still works.
  4. Secure-default local auth surfaces tell users whether to register, bootstrap, or sign in instead of pointing them into a dead-end create-account path.

### Phase 13: Analyst Prompt Routing

**Goal**: Normal analyst phrasing in chat maps to supported deterioration, anomaly, and peer-comparison flows, and unsupported prompts fail with guidance instead of dead ends.  
**Depends on**: Phase 12  
**Plans**: 3/3 completed  
**Completed**: 2026-04-18

**Details:**
- Requirements: `PROMPT-01`, `PROMPT-02`, `PROMPT-03`
- Success criteria:
  1. Common single-company deterioration and anomaly prompts in ordinary analyst language route to supported plans.
  2. Common peer-comparison prompts in ordinary analyst language route to supported plans.
  3. Unsupported requests return actionable rewrite guidance with suggested next phrasing instead of opaque intent failures.

### Phase 14: Chat-Native Result Contract

**Goal**: Completed run results become first-class chat answers with stable run linkage so the workspace conversation becomes the primary answer-reading surface.  
**Depends on**: Phase 13  
**Plans**: 3/3 completed  
**Completed**: 2026-04-19

**Details:**
- Requirements: `CHAT-01`, `CHAT-03`
- Success criteria:
  1. Completed analyses render their primary answer directly inside workspace chat instead of requiring the run page as the primary reader.
  2. The chat answer retains stable linkage back to the underlying run and its persisted context.
  3. Users can continue the same conversation after the answer arrives without losing the association to the completed run.

### Phase 15: Evidence Navigation in Chat

**Goal**: Users can inspect findings, caveats, and linked evidence directly from the chat answer through one coherent navigation surface.  
**Depends on**: Phase 14  
**Plans**: 3/3 completed
**Completed**: 2026-04-19

**Details:**
- Requirements: `CHAT-02`, `NAV-01`, `NAV-02`
- Success criteria:
  1. Top findings, confidence, and caveats are visible inline in the chat-delivered answer.
  2. Report, evidence, artifacts, critic output, and trace surfaces are reachable from one compact navigation area rather than repeated per-finding chips.
  3. Finding-level links jump to the exact supporting artifact or trace target when deeper verification is needed.

### Phase 16: Secondary Run Inspection

**Goal**: The standalone run page becomes a secondary verification and deep-dive surface instead of the primary place users read the answer.  
**Depends on**: Phase 15  
**Plans**: 0 planned

**Details:**
- Requirements: `NAV-03`
- Success criteria:
  1. The run detail page is simplified around inspection and verification tasks instead of duplicating the full primary answer.
  2. Redundant findings and repeated action chips are compressed or removed in favor of deep-dive navigation.
  3. Navigation between chat and run-inspection surfaces is explicit and reversible.

## Archive Notes

- Completed milestone phase directories remain in `.planning/phases/` as raw execution history.
- Use `$gsd-cleanup` later if you want to archive those phase directories under `.planning/milestones/`.

## Progress

| Milestone | Phases | Plans | Status | Shipped |
|-----------|--------|-------|--------|---------|
| v1.0 Hardening | 1-5 | 17 | Complete | 2026-04-17 |
| v1.1 Live Validation and Scale | 6-11 | 18 | Complete | 2026-04-18 |
| v1.2 Chat-First Analysis Experience | 12-16 | 12 | Active | — |
