# Project Milestones: Agentic Data Science System

## v1.4 Conversation-First Information Architecture (Shipped: 2026-04-25)

**Delivered:** A conversation-first EDGAR product shell with in-chat history, lightweight scope context, tighter answer spacing, and secondary trace/artifact surfaces that now clearly sit beneath chat.

**Phases completed:** 5 phases, 15 plans

**Key accomplishments:**

- Reframed the primary shell and entry surfaces around chat instead of workspace chrome.
- Added a new-chat affordance from the shell while preserving the backend project model.
- Turned the left rail into answer-forward history with in-chat continuity.
- Quieted scope into inline conversation context and normalized chat/scope wording.
- Tightened answer spacing and cleaned up the remaining secondary-surface language.

**What's next:** Define the next milestone around richer cross-chat history, comparison workflows, or higher-level analyst memory built on the new conversation-first model.

---

## v1.3 Narrative Answers and Visual Evidence (Shipped: 2026-04-25)

**Delivered:** A narrative-first EDGAR answer experience with backend-authored analyst prose, inline evidence strength, on-demand supporting proof, deterministic inline charts, and a trace surface clearly framed as the technical deep dive.

**Phases completed:** 5 phases, 15 plans, 27 tasks

**Key accomplishments:**

- Replaced summary-card answers with substantive centered narrative replies authored through safe backend previews.
- Moved evidence strength into a compact semantic header pill with an in-chat explainer.
- Collapsed supporting proof into an on-demand disclosure with slim exact-jump evidence rows and quiet secondary navigation.
- Added deterministic inline charts from trusted backend-authored previews instead of frontend inference.
- Finished the answer stack with calmer editorial spacing, responsive cleanup, and explicit chat-versus-trace product framing.

**Stats:**

- 107 files created or modified
- 13,040 insertions and 322 deletions across backend, frontend, tests, and planning artifacts
- 5 phases, 15 plans, 27 tasks, 65 commits
- 6 calendar days from 2026-04-19 to 2026-04-25

**Git range:** `7f1d98f` → `7904171`

**What's next:** Define the next milestone around multi-run conversation workflows, reusable evidence bundles, or analyst memory and comparison features that build on the shipped narrative-first answer surface.

---

## v1.2 Chat-First Analysis Experience (Shipped: 2026-04-19)

**Delivered:** A chat-first EDGAR analysis experience with dependable local runtime delivery, deterministic analyst-language routing, inline answer and evidence reading in workspace chat, and a simplified secondary run inspection surface.

**Phases completed:** 5 phases, 15 plans, 27 tasks

**Key accomplishments:**

- Repaired the documented stack so chat-triggered runs, worker startup, degraded-state disclosure, and secure-default onboarding no longer block first-run usage.
- Broadened deterministic prompt routing so normal analyst phrasing works and unsupported prompts return rewrite guidance before failed run creation.
- Moved completed run answers into workspace chat with persisted run-backed history and one compact run strip instead of link-sprawl footers.
- Added inline findings, confidence/caveats, compact evidence navigation, and exact-jump verification links directly to the chat answer.
- Reduced the standalone run page to a verification-first inspection surface and aligned adjacent run/trace copy to the chat-first model.

**Stats:**

- 130 files created or modified
- 9,854 insertions and 422 deletions across frontend, backend, orchestration, tests, and planning artifacts
- 5 phases, 15 plans, 27 tasks, 62 commits
- Overnight ship from 2026-04-18 to 2026-04-19 (21:25 -> 11:43 local milestone range)

**Git range:** `a50a29c` → `85833e5`

**What's next:** Define the next milestone around multi-run conversation flows, grouped evidence bundles, and richer analyst memory or comparison workflows inside the workspace.

---

## v1.1 Live Validation and Scale (Shipped: 2026-04-18)

**Delivered:** A scale-ready EDGAR analysis platform with policy-gated live validation, S3-compatible artifact storage, summary-first trace inspection, a persisted evaluation control plane, canonical child-run execution, and clean archival traceability.

**Phases completed:** 6 phases, 18 plans, 33 tasks

**Key accomplishments:**

- Validation now has explicit degradation taxonomy and guarded live or hybrid entrypoints instead of ambiguous live usage.
- Artifact storage now supports one S3-compatible backend without exposing bucket or object details in product surfaces.
- Large trace inspection now opens summary-first with bounded collections and per-item raw expansion.
- Supported evaluation workflows are now first-class persisted project-scoped records with case review and CLI compatibility.
- Live and hybrid evaluation now executes through canonical child runs, and SEC or storage degradation is truthful on ops surfaces.
- Phase 11 closed the last audit traceability debt so `v1.1` archived cleanly.

**Stats:**

- 168 files created or modified
- 17,534 insertions and 477 deletions across backend, frontend, evaluation, storage, and planning artifacts
- 6 phases, 18 plans, 33 tasks, 72 commits
- Same-day ship on 2026-04-18 (09:45 -> 20:05 local milestone range)

**Git range:** `73c2c4f` → `495de6c`

**What's next:** Define the next milestone around scheduled live canaries, fixture promotion, brokered large-artifact delivery, and cross-run evidence coverage.

---

## v1.0 Hardening (Shipped: 2026-04-17)

**Delivered:** A production-harder EDGAR analysis platform with isolated runs, resilient workers, secure defaults, full-stack CI gates, and retention-aware storage or ops behavior.

**Phases completed:** 5 phases, 17 plans, 29 tasks

**Key accomplishments:**

- Run-scoped workspaces and explicit artifact provenance removed repo-global output collisions across CLI, backend, and MCP flows.
- Worker claims now use heartbeats, fencing tokens, and durable attempt history so retries and stale reclaims stay auditable on one run identity.
- Startup, registration, telemetry, and raw payload access now fail closed by default unless an operator explicitly opts in.
- Pull requests now gate the documented Compose stack, seeded browser workflows, and focused Postgres or concurrency regressions.
- Storage and operations now report degraded dependency state truthfully, stream artifact ingest, and preserve auditability through explicit retention workflows.

**Stats:**

- 181 files created or modified
- 15,864 insertions and 613 deletions across code, docs, migrations, and CI config
- 5 phases, 17 plans, 29 tasks, 102 commits
- 3 calendar days from start to ship (2026-04-15 -> 2026-04-17)

**Git range:** `9063eb9` → `717a4e9`

**What's next:** Define the next milestone around live validation workflows, remote object storage, and large trace or transparency scalability.

---
