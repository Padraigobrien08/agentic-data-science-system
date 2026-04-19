# Roadmap: Agentic Data Science System

## Milestones

- [x] **v1.0 Hardening** — shipped 2026-04-17 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.0-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.0-REQUIREMENTS.md)
- [x] **v1.1 Live Validation and Scale** — shipped 2026-04-18 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-REQUIREMENTS.md) · [audit](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.1-MILESTONE-AUDIT.md)
- [x] **v1.2 Chat-First Analysis Experience** — shipped 2026-04-19 · [archive](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.2-ROADMAP.md) · [requirements](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.2-REQUIREMENTS.md) · [audit](/Users/padraigobrien/agentic_data_science_system/.planning/milestones/v1.2-MILESTONE-AUDIT.md)
- [ ] **v1.3 Narrative Answers and Visual Evidence** — active · phases 17-21

## Active Planning

### Milestone v1.3: Narrative Answers and Visual Evidence

**Status:** In planning
**Phases:** 17-21
**Total Plans:** 15 planned

### Phase 17: Narrative Answer Contract

**Goal**: Replace the short summary-card contract with a fuller narrative analyst answer that can still fail gracefully when support is limited.
**Depends on**: Phase 16 and shipped `v1.2` chat-first baseline
**Plans**: 3 plans

Plans:

- [ ] `17-narrative-answer-contract-01-PLAN.md` — Define a backend-safe narrative answer contract that promotes thesis, support, and watchouts into first-class answer fields
- [ ] `17-narrative-answer-contract-02-PLAN.md` — Refactor the chat answer builder, live reply path, and history hydration around the longer narrative contract
- [ ] `17-narrative-answer-contract-03-PLAN.md` — Render the centered narrative-first answer body and harden fallback states so successful runs never degrade into vague placeholder prose

**Details:**
- Requirements: `ANSR-01`, `ANSR-02`
- Outcome: the primary answer reads like a substantive analyst reply instead of a compressed summary

### Phase 18: Confidence Explainer

**Goal**: Move evidence strength into the answer header and let users understand the rating through a compact explainer instead of a large standalone caveat block.
**Depends on**: Phase 17
**Plans**: 3 plans

Plans:

- [ ] 18-01: Extend the answer and transparency contract with explicit confidence rationale fields that explain coverage, caveats, and trust limits
- [ ] 18-02: Implement the inline evidence-strength badge with semantic color treatment and a responsive shadcn popover/dialog explainer
- [ ] 18-03: Collapse redundant caveat chrome into the explainer and keep only the most important rider inline with the answer

**Details:**
- Requirements: `CONF-01`, `CONF-02`, `CONF-03`
- Outcome: confidence posture is visible at a glance and explainable without overwhelming the main answer body

### Phase 19: Supplemental Evidence Disclosure

**Goal**: Make evidence clearly supplemental by moving supporting cards into a disclosure beneath the answer and keeping navigation pills secondary.
**Depends on**: Phase 18
**Plans**: 3 plans

Plans:

- [ ] 19-01: Redesign the chat answer layout so narrative prose is central and evidence is disclosed below it instead of competing alongside it
- [ ] 19-02: Implement long, slim evidence cards with one-line justification and exact-jump links into the relevant artifact or trace target
- [ ] 19-03: Keep the report/evidence/artifacts/critic/trace pills as a compact secondary strip under the supplemental evidence section

**Details:**
- Requirements: `ANSR-03`, `EVID-01`, `EVID-02`, `EVID-03`
- Outcome: the answer is what users read first, while proof remains easy to inspect without dominating the layout

### Phase 20: Inline Charts in Chat

**Goal**: Add deterministic inline visual evidence to the chat answer so the system can show trends and comparisons, not only describe them.
**Depends on**: Phase 19
**Plans**: 3 plans

Plans:

- [ ] 20-01: Define backend-safe chart spec generation sourced from trusted run artifacts and metric outputs
- [ ] 20-02: Render inline charts in chat with shadcn/Recharts components and responsive layout support
- [ ] 20-03: Gate chart rendering to strong supported cases and attach short captions that explain what each chart shows and why it matters

**Details:**
- Requirements: `CHRT-01`, `CHRT-02`, `CHRT-03`
- Outcome: chat can include trustworthy visual evidence that strengthens the narrative answer

### Phase 21: Narrative Answer Polish

**Goal**: Refine the end-to-end narrative answer experience so it feels intentional across desktop and smaller viewports and leaves the trace as the technical surface.
**Depends on**: Phase 20
**Plans**: 3 plans

Plans:

- [ ] 21-01: Add final prose hierarchy, spacing, and citation/link polish to the narrative answer flow
- [ ] 21-02: Tune responsiveness and disclosure behavior so the new answer architecture works cleanly across common screen sizes
- [ ] 21-03: Align remaining chat/trace wording and navigation so trace stays the technical deep-dive rather than a competing answer reader

**Details:**
- Requirements: UX polish across all `v1.3` requirements
- Outcome: the milestone ships as a coherent narrative-first answer experience instead of a collection of incremental UI features

## Archive Notes

- Completed milestone phase directories remain in `.planning/phases/` as raw execution history.
- Use `$gsd-cleanup` later if you want to archive those phase directories under `.planning/milestones/`.

## Progress

| Milestone | Phases | Plans | Status | Shipped |
|-----------|--------|-------|--------|---------|
| v1.0 Hardening | 1-5 | 17 | Complete | 2026-04-17 |
| v1.1 Live Validation and Scale | 6-11 | 18 | Complete | 2026-04-18 |
| v1.2 Chat-First Analysis Experience | 12-16 | 15 | Complete | 2026-04-19 |
| v1.3 Narrative Answers and Visual Evidence | 17-21 | 15 | In planning | — |
