# Roadmap: Agentic Data Science System

## Milestones

- [ ] **v1.5 Durable Chat History** — active · preserve prior conversations when `New chat` creates a fresh thread
- [x] **v1.6 Measured Agency and Visible Observability** — shipped 2026-08-08 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.6-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.6-REQUIREMENTS.md) · unplanned track, shipped ahead of v1.5
- [x] **v1.0 Hardening** — shipped 2026-04-17 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.0-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.0-REQUIREMENTS.md)
- [x] **v1.1 Live Validation and Scale** — shipped 2026-04-18 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-REQUIREMENTS.md) · [audit](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-MILESTONE-AUDIT.md)
- [x] **v1.2 Chat-First Analysis Experience** — shipped 2026-04-19 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.2-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.2-REQUIREMENTS.md) · [audit](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.2-MILESTONE-AUDIT.md)
- [x] **v1.3 Narrative Answers and Visual Evidence** — shipped 2026-04-25 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.3-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.3-REQUIREMENTS.md) · [audit](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.3-MILESTONE-AUDIT.md)
- [x] **v1.4 Conversation-First Information Architecture** — shipped 2026-04-25 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.4-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.4-REQUIREMENTS.md) · [audit](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.4-MILESTONE-AUDIT.md)

## Active Planning

### Milestone v1.5: Durable Chat History

**Status:** Active
**Phases:** 27-30 planned
**Total Plans:** 0 planned yet

### Phase 27: History Persistence Semantics

**Goal**: Define and enforce stable conversation identity so a new chat never makes a prior conversation disappear from the visible history model.
**Depends on**: Shipped `v1.4` conversation-first shell
**Plans**: 0 plans yet
**Status**: Pending

Expected outcome:

- prior chats remain visible and reopenable immediately after new-chat creation

### Phase 28: New Chat Creation Flow

**Goal**: Make `New chat` create a distinct empty thread instead of replacing or hijacking the current history selection.
**Depends on**: Phase 27
**Plans**: 0 plans yet
**Status**: Pending

Expected outcome:

- new chat is a clean thread with clear active-state behavior

### Phase 29: History Selection and Resume

**Goal**: Ensure selecting an older chat restores the right persisted thread and latest answer instead of whichever shell state was loaded most recently.
**Depends on**: Phase 28
**Plans**: 0 plans yet
**Status**: Pending

Expected outcome:

- history items behave like durable conversation handles, not transient run cards

### Phase 30: Continuity Hardening and Regression Coverage

**Goal**: Lock the new history model down across refresh, run completion, and future shell changes.
**Depends on**: Phase 29
**Plans**: 0 plans yet
**Status**: Pending

Expected outcome:

- continuity regressions are caught before ship

### Milestone v1.4: Conversation-First Information Architecture

**Status:** Shipped 2026-04-25
**Phases:** 22-26 complete
**Total Plans:** 15 complete

### Phase 22: Conversation-First Shell

**Goal**: Remove visible workspace-first framing from the primary product surface and make chat the unmistakable entrypoint.
**Depends on**: Shipped `v1.3` narrative answer baseline
**Plans**: 3 plans
**Status**: Complete

Plans:

- [x] 22-01: Replace workspace-heavy shell labels and chrome with a conversation-first chat shell
- [x] 22-02: Introduce clearer new-conversation and primary history affordances without changing backend project ownership
- [x] 22-03: Align top-level navigation and entry flow so the product opens as chat with history instead of workspace management

**Details:**
- Requirements: `CONV-01`, `CONV-02`, `SURF-01`
- Outcome: the app reads like a chat product immediately instead of exposing internal workspace structure

### Phase 23: Chat History and Continuity

**Goal**: Make history feel like conversation history rather than a list of generic analyses or runs.
**Depends on**: Phase 22
**Plans**: 3 plans
**Status**: Complete

Plans:

- [x] 23-01: Reframe the left rail and history model around conversations and prior answers rather than generic analysis cards
- [x] 23-02: Tighten persisted history selection and reopening behavior so continuing a prior conversation feels natural
- [x] 23-03: Harden history naming, ordering, and empty states so users can understand what each prior conversation contains

**Details:**
- Requirements: `CONV-03`, `HIST-01`
- Outcome: prior work becomes easy to revisit as chat history, not as hidden run state

### Phase 24: Lightweight Scope Context

**Goal**: Treat scope as lightweight chat context that is visible and editable without turning it back into workspace configuration.
**Depends on**: Phase 23
**Plans**: 3 plans
**Status**: Complete

Plans:

- [x] 24-01: Redesign visible scope presentation as quiet chat-context metadata instead of workspace setup chrome
- [x] 24-02: Make scope editing inline and conversational while preserving the existing project-backed scope contract
- [x] 24-03: Clarify how current scope affects future prompts and when a prompt narrows scope within the active conversation

**Details:**
- Requirements: `SCOPE-01`, `SCOPE-02`
- Outcome: users keep scope control without feeling like they are leaving the chat flow to configure a workspace

### Phase 25: Answer Surface Tightening

**Goal**: Tighten the answer layout so the question, answer, confidence, proof, and composer feel like one coherent reading flow.
**Depends on**: Phase 24
**Plans**: 3 plans
**Status**: Complete

Plans:

- [x] 25-01: Pull the answer upward and reduce dead space between the user prompt and the start of the response
- [x] 25-02: Integrate the confidence pill directly with the answer header and rebalance editorial spacing across the answer block
- [x] 25-03: Compress supplemental evidence rows and bottom spacing so proof stays secondary and the composer feels better placed

**Details:**
- Requirements: `LAY-01`, `LAY-02`, `LAY-03`
- Outcome: the answer surface reads more like a polished conversation than a stacked application layout

### Phase 26: Secondary Surface Cleanup

**Goal**: Keep trace and artifact routes coherent as technical deep dives after workspace and run language are demoted in the primary UI.
**Depends on**: Phase 25
**Plans**: 3 plans
**Status**: Complete

Plans:

- [x] 26-01: Align trace and artifact wording, back-links, and route affordances to the conversation-first model
- [x] 26-02: Remove remaining user-facing workspace and run terminology where it conflicts with the primary chat/history framing
- [x] 26-03: Harden secondary-route navigation so technical deep dives always point back to the right conversation context

**Details:**
- Requirements: `SURF-02`, `SURF-03`
- Outcome: secondary surfaces stay useful and technical without undermining the new chat-first information architecture

## Archive Notes

- Completed milestone phase directories remain in `.planning/phases/` as raw execution history.
- Use `$gsd-cleanup` later if you want to archive those phase directories under `.planning/milestones/`.

## Progress

| Milestone | Phases | Plans | Status | Shipped |
|-----------|--------|-------|--------|---------|
| v1.0 Hardening | 1-5 | 17 | Complete | 2026-04-17 |
| v1.1 Live Validation and Scale | 6-11 | 18 | Complete | 2026-04-18 |
| v1.2 Chat-First Analysis Experience | 12-16 | 15 | Complete | 2026-04-19 |
| v1.3 Narrative Answers and Visual Evidence | 17-21 | 15 | Complete | 2026-04-25 |
| v1.4 Conversation-First Information Architecture | 22-26 | 15 | Complete | 2026-04-25 |
| v1.5 Durable Chat History | 27-30 | 0 | Active | — |
| v1.6 Measured Agency and Visible Observability | 31, 32, 34 | 8 | Complete | 2026-08-08 |
