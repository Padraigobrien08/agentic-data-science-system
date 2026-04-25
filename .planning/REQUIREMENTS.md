# Requirements: Agentic Data Science System

**Defined:** 2026-04-25
**Core Value:** Every EDGAR run must produce trustworthy, isolated, auditable results that the user can inspect without ambiguity.

## v1.4 Requirements

### Conversation Model

- [x] **CONV-01**: User can enter the product as a conversation-first surface without prominent workspace-first framing or redundant shell chrome
- [x] **CONV-02**: User can start a new conversation from the history rail without understanding or configuring a separate workspace construct
- [x] **CONV-03**: User can reopen a prior conversation from history and continue from the same persisted context

### History and Scope

- [x] **HIST-01**: User can scan a clear history list organized around prior conversations and answers rather than generic analysis-run labels
- [x] **SCOPE-01**: User can view the active analysis scope as lightweight chat context instead of as workspace configuration
- [x] **SCOPE-02**: User can edit that scope inline from the conversation surface and understand that the change affects future messages in the current chat

### Answer Layout

- [x] **LAY-01**: User sees the answer begin close to the triggering prompt with minimal dead space between question and response
- [x] **LAY-02**: User sees evidence strength aligned to the answer header as part of one unified answer block
- [x] **LAY-03**: User can read slimmer supplemental evidence rows with quieter source actions and cleaner spacing above the composer

### Secondary Surfaces

- [x] **SURF-01**: User sees chat, history, and scope language in primary navigation where the experience is conversational, instead of workspace-heavy terminology
- [x] **SURF-02**: User can reach trace and artifact detail as technical deep dives from chat without those surfaces pretending to be alternate primary reading destinations
- [x] **SURF-03**: Secondary routes, back-links, and labels remain coherent after visible workspace and run terminology are demoted

## v2 Requirements

### Conversation Expansion

- **CONV-04**: User can compare multiple prior conversations or answers side by side inside one chat history
- **HIST-02**: User can pin important answers or conversations in history for later return

### Scope Expansion

- **SCOPE-03**: User can save and reuse named scope presets across conversations

## Out of Scope

| Feature | Reason |
|---------|--------|
| Removing the backend project, run, or artifact model | Persistence, ownership, and traceability still depend on those existing brownfield contracts |
| Collaborative shared chat threads or multi-user live presence | This milestone is about single-user information architecture, not real-time collaboration |
| Cross-thread memory synthesis or automatic prior-answer comparison | That is a separate product capability after the core conversation model is simplified |
| Reopening the narrative answer contract or chart trust model | `v1.3` already shipped the right answer architecture; this milestone changes product framing and layout around it |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONV-01 | Phase 22 | Complete |
| CONV-02 | Phase 22 | Complete |
| CONV-03 | Phase 23 | Complete |
| HIST-01 | Phase 23 | Complete |
| SCOPE-01 | Phase 24 | Complete |
| SCOPE-02 | Phase 24 | Complete |
| LAY-01 | Phase 25 | Complete |
| LAY-02 | Phase 25 | Complete |
| LAY-03 | Phase 25 | Complete |
| SURF-01 | Phase 22 | Complete |
| SURF-02 | Phase 26 | Complete |
| SURF-03 | Phase 26 | Complete |

**Coverage:**
- v1.4 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-04-25*
*Last updated: 2026-04-25 after defining v1.4 Conversation-First Information Architecture*
