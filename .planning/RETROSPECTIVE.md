# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 5 | Introduced trust-boundary phases, archived planning artifacts, and regression-first execution |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 57 prior-phase regression tests green at milestone closeout plus 13/13 Phase 5 must-haves | Broad backend, worker, browser, and Compose workflow gating | 0 |

### Top Lessons (Verified Across Milestones)

1. Initial milestone establishes the baseline; no cross-milestone lesson is verified yet.
2. Keep archived requirements and milestone summaries lean so the live planning docs stay small.
