---
phase: 17-narrative-answer-contract
verified: 2026-04-19T22:43:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 17: Narrative Answer Contract Verification Report

**Phase Goal:** Replace the short summary-card contract with a fuller narrative analyst answer that can still fail gracefully when support is limited.
**Verified:** 2026-04-19T22:43:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | The backend now exposes a safe typed narrative preview through run transparency instead of forcing the frontend to assemble long-form prose from summary fragments. | ✓ VERIFIED | `backend/agents/output_schemas.py`, `backend/agents/phase_outputs.py`, `backend/agents/traceability_summary.py`, `backend/schemas/run_transparency.py`, `frontend/src/lib/api/types.ts`, `tests/test_phase_outputs.py`, `tests/test_traceability_summary.py`, `tests/test_run_transparency_builders.py`, `tests/test_sprint3_transparency_api.py` |
| 2 | Live chat replies and hydrated chat history now consume the same narrative-first answer contract, with explicit `full`, `partial`, and `legacy` modes for compatibility. | ✓ VERIFIED | `frontend/src/lib/run-primary-view.ts`, `frontend/src/actions/runs.ts`, `frontend/src/lib/chat-run-history.ts`, `frontend/src/lib/__tests__/run-primary-view.test.ts`, `frontend/src/actions/runs.test.ts`, `frontend/src/lib/chat-run-history.test.ts` |
| 3 | The assistant answer now renders as a centered narrative reply with explicit partial and error behavior, and the old right-rail summary-card layout is gone from the primary answer path. | ✓ VERIFIED | `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, `frontend/src/components/chat-shell/chat-message-list.test.tsx`, `frontend/src/components/chat-shell/chat-shell.test.tsx` |

**Score:** 3/3 truths verified

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Backend narrative/transparency gate | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_phase_outputs.py tests/test_traceability_summary.py tests/test_traceable_pipeline.py tests/test_llm_output_quality_regression.py tests/test_sprint3_transparency_api.py -q --tb=short` | `31 passed in 5.16s` | ✓ PASS |
| Frontend narrative contract + renderer gate | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` | `17 passed`; build passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `ANSR-01` | `17-01`, `17-02`, `17-03` | User can read a multi-paragraph analyst answer in chat that explains the thesis, supporting evidence, and watchouts instead of a one-line summary card | ✓ SATISFIED | Backend-authored preview in `backend/schemas/run_transparency.py`, narrative-first derivation in `frontend/src/lib/run-primary-view.ts`, and centered answer rendering in `frontend/src/components/chat-shell/chat-run-answer-card.tsx` |
| `ANSR-02` | `17-01`, `17-02`, `17-03` | User can receive a stable non-boilerplate fallback answer when evidence is limited, so successful runs never collapse into vague placeholder text | ✓ SATISFIED | Partial preview modes in `backend/agents/traceability_summary.py`, legacy fallback behavior in `frontend/src/lib/run-primary-view.ts`, and explicit partial/error shell copy in `frontend/src/components/chat-shell/chat-run-answer-card.tsx` |

### Gaps Summary

No blocking gaps remain for Phase 17. The next work is Phase 18: move evidence strength into the answer header with a compact explainer so trust posture is visible without reintroducing a dominant support panel.

---

_Verified: 2026-04-19T22:43:00Z_
_Verifier: Codex_
