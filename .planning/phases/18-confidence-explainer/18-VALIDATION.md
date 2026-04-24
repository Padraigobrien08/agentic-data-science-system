---
phase: 18
slug: confidence-explainer
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-24
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for inline confidence posture, grouped explainer rationale, and reduced caveat chrome in chat.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` + `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx` |
| **Full suite command** | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` |
| **Estimated runtime** | ~20 seconds quick, ~45 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the most focused backend or frontend command for the seam that changed
- **After every plan wave:** Run the quick run command above
- **Before `$gsd-verify-work`:** Full suite and frontend build must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01 | 01 | 1 | CONF-01, CONF-02, CONF-03 | backend contract | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short` | ⚠️ extend existing | ⬜ pending |
| 18-02 | 02 | 2 | CONF-01, CONF-02 | frontend view-model | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts` | ⚠️ extend existing | ⬜ pending |
| 18-03 | 03 | 3 | CONF-01, CONF-02, CONF-03 | rendering/build | `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` | ⚠️ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

---

## Wave 0 Requirements

- [x] Extend `tests/test_run_transparency_builders.py` — grouped confidence rationale and safe preview serialization
- [x] Extend `tests/test_traceability_summary.py` — backend rationale grouping and inline rider source behavior
- [x] Extend `tests/test_sprint3_transparency_api.py` — transparency API exposes explainer fields without leaking raw internals
- [x] Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` — product-facing label mapping, pill/rider derivation, and no duplicate technical status in the primary answer view
- [x] Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` and `frontend/src/components/chat-shell/chat-shell.test.tsx` — header pill rendering, grouped explainer content, and reduced inline caveat chrome

*Existing infrastructure covers all Phase 18 requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The answer header shows one compact semantic confidence pill that feels integrated with the narrative answer | CONF-01 | Requires visual review of density, spacing, and semantic color treatment | 1. Open a completed chat answer with confidence data. 2. Confirm the header shows a single `Evidence strength` pill using `Good`, `Medium`, `Bad`, or `Not rated`. 3. Confirm the old inline `critic/report` status labels are gone from the primary answer surface. |
| Opening the confidence control explains the rating without leaving chat | CONF-02 | Requires end-to-end interaction review across the real disclosure primitive | 1. Open the confidence pill in desktop and, if possible, a narrow viewport. 2. Confirm the explainer shows grouped support, weakness, and limits sections. 3. Confirm the interaction closes cleanly and does not navigate away. |
| Caveat explanation is mostly inside the explainer, with only one short inline rider when needed | CONF-03 | Requires visual confirmation that the answer remains grounded but not overloaded | 1. Trigger a run with meaningful caveats. 2. Confirm the main answer shows at most one short rider below the narrative. 3. Confirm the fuller caveat rationale appears inside the explainer rather than as a large permanent block. |

---

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers backend preview construction, API exposure, frontend label mapping, and chat rendering
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
