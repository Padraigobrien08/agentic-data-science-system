# Requirements: Agentic Data Science System

**Defined:** 2026-04-19
**Core Value:** Every EDGAR run must produce trustworthy, isolated, auditable results that the user can inspect without ambiguity.

## v1.3 Requirements

### Narrative Answer

- [ ] **ANSR-01**: User can read a multi-paragraph analyst answer in chat that explains the thesis, supporting evidence, and watchouts instead of a one-line summary card
- [ ] **ANSR-02**: User can receive a stable non-boilerplate fallback answer when evidence is limited, so successful runs never collapse into vague placeholder text
- [ ] **ANSR-03**: User can treat the narrative answer as the primary reading surface, with findings and supporting detail clearly subordinate to it

### Confidence Experience

- [ ] **CONF-01**: User can see evidence strength inline in the answer header with semantic status styling for `Good`, `Medium`, `Bad`, and `Not rated`
- [ ] **CONF-02**: User can open a compact explainer from that header status and understand why the evidence strength received its current rating
- [ ] **CONF-03**: User can review the main caveat drivers inside the explainer without leaving chat

### Supplemental Evidence

- [ ] **EVID-01**: User can expand or collapse supplemental evidence beneath the narrative answer instead of reading evidence cards as the primary response
- [ ] **EVID-02**: User can scan slim supporting evidence cards that explain why each source matters and jump directly to the relevant artifact or trace target
- [ ] **EVID-03**: User can still access report, evidence, artifacts, critic output, and trace through one compact secondary navigation strip below the supplemental evidence

### Visual Evidence

- [ ] **CHRT-01**: User can see deterministic inline charts in chat when trusted run data supports a visual explanation
- [ ] **CHRT-02**: Charts are rendered from explicit backend-safe chart specs derived from trusted run artifacts or metrics, not ad hoc frontend inference
- [ ] **CHRT-03**: Each inline chart includes a short caption explaining what it shows and why it is relevant to the answer

## v2 Requirements

### Conversation Expansion

- **CHAT-04**: User can compare multiple prior runs within one narrative answer instead of only reading one run at a time

### Visual Expansion

- **CHRT-04**: User can pin or revisit generated charts across follow-up messages without rerunning the entire analysis

### Evidence Expansion

- **EVID-04**: User can save supplemental evidence bundles for later verification or sharing

## Out of Scope

| Feature | Reason |
|---------|--------|
| Freeform LLM-generated charts without deterministic backing data | This milestone is about trust-preserving visual evidence, not generative visualization |
| Full redesign of every trace, artifact, and evaluation page | The primary goal is the chat answer itself; secondary technical surfaces can remain mostly intact |
| Arbitrary user-authored chart builder inside chat | That is a separate product capability from rendering trusted inline evidence visuals |
| New anomaly models or broader analytical feature expansion | The current priority is answer form, confidence explanation, and evidence presentation |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ANSR-01 | Phase 17 | Pending |
| ANSR-02 | Phase 17 | Pending |
| ANSR-03 | Phase 19 | Pending |
| CONF-01 | Phase 18 | Pending |
| CONF-02 | Phase 18 | Pending |
| CONF-03 | Phase 18 | Pending |
| EVID-01 | Phase 19 | Pending |
| EVID-02 | Phase 19 | Pending |
| EVID-03 | Phase 19 | Pending |
| CHRT-01 | Phase 20 | Pending |
| CHRT-02 | Phase 20 | Pending |
| CHRT-03 | Phase 20 | Pending |

**Coverage:**
- v1.3 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-04-19*
*Last updated: 2026-04-19 after starting v1.3 Narrative Answers and Visual Evidence*
