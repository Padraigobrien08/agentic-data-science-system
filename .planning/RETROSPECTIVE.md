# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.2 — Chat-First Analysis Experience

**Shipped:** 2026-04-19
**Phases:** 5 | **Plans:** 15 | **Sessions:** 1

### What Was Built
- A repaired sync-first chat runtime with truthful degraded-state reporting and capability-aware secure-default onboarding
- Deterministic analyst-language routing with prompt previews and actionable rewrite guidance before run creation
- A chat-native answer contract with persisted run-backed history, inline findings, confidence/caveats, compact evidence navigation, and exact-jump verification links
- A reduced standalone run page that now serves secondary inspection and verification rather than primary answer reading

### What Worked
- Local product testing produced a concrete next milestone immediately; the phases mapped directly to the real user friction instead of speculative UX work.
- Fixing runtime and routing before enriching the chat answer kept the later UI phases additive and low-risk.
- Reusing the existing run-answer derivation path for chat kept the chat and run surfaces aligned instead of creating parallel summary logic.

### What Was Inefficient
- Milestone-closeout still needed manual planning bookkeeping cleanup for stale validation metadata before the final audit pass.
- Archive curation remains manual: roadmap slimming, requirement retirement, milestone history, and retrospective updates are still hand-authored.
- Unrelated local UI exploration remained dirty through the milestone, which reinforced the need to keep archive commits narrowly scoped to planning artifacts.

### Patterns Established
- Use live product testing to define the next milestone immediately after infrastructure-heavy ships; it exposes the real product seam faster than abstract backlog grooming.
- Move the primary reading surface first, then simplify the legacy surface after the replacement is already usable.
- Keep chat delivery deterministic-first and inspectable rather than hiding routing or runtime fallback behavior behind opaque convenience.

### Key Lessons
1. Chat-first product work only stabilizes quickly when runtime truthfulness and deterministic routing are solved before the UI richness phase.
2. Reusing existing answer builders is cheaper and safer than inventing a second summary stack for a new surface.
3. Milestone audit quality improves when validation and summary metadata are closed during phase execution, not at archive time.

### Cost Observations
- Model mix: not tracked in repository metadata for this milestone
- Sessions: 1 visible GSD execution session
- Notable: 15 plans and 27 tasks shipped overnight because the milestone stayed tightly focused on one product hierarchy change

---

## Milestone: v1.0 — Hardening

**Shipped:** 2026-04-17
**Phases:** 5 | **Plans:** 17 | **Sessions:** 1

### What Was Built
- Run-scoped workspaces and explicit artifact-path contracts across CLI, MCP, backend, and report flows
- Lease-safe worker execution with heartbeats, claim fencing, durable attempt history, and truthful queue or worker status
- Secure defaults, PR-required full-stack CI, and audit-preserving retention-aware storage or ops behavior

### What Worked
- Breaking the brownfield hardening work into trust-boundary phases kept changes local, reviewable, and easy to verify.
- Each plan stayed anchored by failing regressions or explicit operator contract docs before implementation, which kept behavior changes defensible.
- Atomic task commits and per-plan summaries preserved context while moving quickly across five phases in one milestone.

### What Was Inefficient
- GitHub required-check configuration could not be fully verified from the local workflow, so Phase 4 needed a manual checkpoint after the code landed.
- The archive CLI handled the historical snapshot, but live roadmap, project, and retrospective cleanup still required manual follow-through.
- A non-blocking `runpy` warning remains in the retention CLI because `backend.maintenance.__init__` eagerly imports the module it later executes.

### Patterns Established
- Define a shared contract first, then thread it across CLI, backend, MCP, and docs before widening regression coverage.
- Prefer auditable, additive state transitions over destructive cleanup for retries, payload redaction, and artifact retention.
- Ship operator runbooks and CI coverage in the same phase as behavior changes so the documented stack stays truthful.

### Key Lessons
1. For brownfield reliability work, sequencing by trust boundary is faster and safer than broad module-by-module refactoring.
2. Explicit path, claim, and retention contracts reduce ambiguity more effectively than implicit fallback cleanup.
3. Full-stack smoke and browser gates catch documentation drift that unit tests alone will miss.

### Cost Observations
- Model mix: not tracked in repository metadata for this milestone
- Sessions: 1 visible GSD execution session
- Notable: 17 plans and 29 tasks shipped in roughly 3 days because each phase carried its own verification gate and concise operator-facing docs

---

## Milestone: v1.1 — Live Validation and Scale

**Shipped:** 2026-04-18
**Phases:** 6 | **Plans:** 18 | **Sessions:** 1

### What Was Built
- Explicit live-validation policy boundaries, freshness-aware degradation classes, and guarded operator entrypoints
- One S3-compatible remote artifact backend with app-owned delivery, reconciliation-aware deletes, and retention-safe behavior
- Summary-first large-trace inspection with bounded collections, SSR navigation, and item-scoped raw expansion
- A persisted evaluation control plane with suite cataloging, case review, canonical child-run execution, and truthful SEC or storage ops reporting
- A final audit-traceability cleanup phase that restored clean milestone archival metadata

### What Worked
- Carrying the hardening baseline into scale work let each phase build on a stable contract rather than reopening earlier trust boundaries.
- The summary, validation, verification, and audit files made the cleanup phase fast because the required evidence already existed in structured form.
- Keeping artifact, trace, evaluation, and ops work in separate phases prevented the milestone from collapsing into one opaque “platform” change set.

### What Was Inefficient
- The archive and phase-complete helpers still regressed `STATE.md` milestone fields, so live state repair was needed more than once.
- The default milestone archive helper produced a raw snapshot, not the final curated archive shape, so the archive docs still needed manual interpretation and cleanup.
- Milestone-closeout documentation remains more manual than execution and verification, especially around roadmap slimming and retrospective curation.

### Patterns Established
- Treat validation policy, storage topology, trace browsing, and evaluation control-plane surfaces as separate product contracts with their own verification loops.
- Use summary-frontmatter and validation metadata as archive-time machine inputs, not just as human-readable documentation.
- Close milestone audit debt immediately with a small explicit cleanup phase instead of carrying bookkeeping ambiguity into the next milestone.

### Key Lessons
1. When planning artifacts are treated as product-grade interfaces, milestone audit cleanup becomes a narrow repair instead of a broad archaeology task.
2. Summary-first UX work is safer after artifact-delivery and auth boundaries are already stable.
3. Live-validation scale work benefits from keeping policy, storage, UI, control-plane, and ops truthfulness in distinct phases even when shipped in one day.

### Cost Observations
- Model mix: not tracked in repository metadata for this milestone
- Sessions: 1 visible GSD execution session
- Notable: 18 plans and 33 tasks shipped in a single day because each phase remained contract-driven and verification-heavy

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 5 | Introduced trust-boundary phases, archived planning artifacts, and regression-first execution |
| v1.1 | 1 | 6 | Extended the hardened base into live-validation scale features and added an explicit archive-traceability cleanup phase |
| v1.2 | 1 | 5 | Re-centered the product around chat-first answer delivery and demoted the run page to secondary inspection |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 57 prior-phase regression tests green at milestone closeout plus 13/13 Phase 5 must-haves | Broad backend, worker, browser, and Compose workflow gating | 0 |
| v1.1 | 66 backend audit-slice tests plus 8 frontend trace tests green at milestone closeout | Validation policy, remote storage, large traces, evaluation control plane, child-run reconciliation, and ops truthfulness | 0 |
| v1.2 | 84 backend audit-slice tests plus 12 frontend chat/run-page tests green at milestone closeout | Runtime reliability, deterministic routing, chat-native answers, inline evidence navigation, and secondary run inspection | 0 |

### Top Lessons (Verified Across Milestones)

1. Contract-driven milestones stay executable at speed when each phase owns one trust boundary or operator surface.
2. Archive helpers still need manual curation; treat milestone completion as a documentation pass, not just a file move.
