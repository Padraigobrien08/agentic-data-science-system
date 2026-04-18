# Phase 10: Live/Hybrid Execution Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 10-Live/Hybrid Execution Hardening
**Areas discussed:** Evaluation launch mode, Child-run linkage shape, Case outcome mapping, Ops truthfulness surface

---

## Evaluation launch mode

| Option | Description | Selected |
|--------|-------------|----------|
| A | Start live or hybrid evaluation by enqueueing child analysis runs and return immediately | ✓ |
| B | Execute live or hybrid child runs inline inside the evaluation start request | |
| C | Keep direct evaluation-run execution for now and defer canonical run queueing | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted that live or hybrid validation should run through the existing queue and worker path instead of a separate inline executor.

---

## Child-run linkage shape

| Option | Description | Selected |
|--------|-------------|----------|
| A | Link each case to one canonical child `AnalysisRun` per execution attempt, with latest-run pointer plus bounded prior history | ✓ |
| B | Link the entire evaluation run to one shared child analysis run | |
| C | Keep only opaque execution logs or IDs without first-class child-run links | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted case-level linkage into canonical runs rather than suite-level or log-only indirection.

---

## Case outcome mapping

| Option | Description | Selected |
|--------|-------------|----------|
| A | Derive evaluation case verdicts from linked child-run terminal state plus degradation taxonomy | ✓ |
| B | Keep a separate evaluation-only runtime status model parallel to `AnalysisRunStatus` | |
| C | Let child runs exist but continue to treat evaluation runner state as the primary source of truth | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted canonical run state as the execution source of truth, with evaluation verdicts layered on top.

---

## Ops truthfulness surface

| Option | Description | Selected |
|--------|-------------|----------|
| A | Extend existing health and metrics surfaces with explicit evaluation/live-validation dependency state | ✓ |
| B | Keep SEC or storage degradation only inside evaluation case messages and result payloads | |
| C | Add a separate evaluation-only ops endpoint and leave current health or metrics untouched | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted extending the current truthful ops surfaces instead of hiding evaluation degradation in case-level messages.

---

## the agent's Discretion

- Exact field names and schema shape for child-run links and bounded prior history
- Exact metrics or health field names for evaluation-specific degraded state
- Exact queue fan-out mechanics, as long as they preserve canonical run and worker behavior

## Deferred Ideas

None.
