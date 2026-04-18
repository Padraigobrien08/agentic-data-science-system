---
phase: 13
slug: analyst-prompt-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 13 - Validation Strategy

> Per-phase validation contract for deterministic analyst-language routing, prompt-scoped ticker narrowing, and actionable unsupported guidance in chat.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` + `vitest` |
| **Config file** | `pytest.ini` and `frontend/vitest.config.ts` |
| **Quick run command** | `python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py tests/test_prompt_routing_api.py -q --tb=short && cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx` |
| **Full suite command** | `python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py tests/orchestration/test_phase3_orchestration.py tests/orchestration/test_prompt_scope.py tests/test_prompt_routing_api.py tests/test_intent_preferences_assistant.py -q --tb=short && cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` |
| **Estimated runtime** | ~15 seconds quick, ~35 seconds full |

## Sampling Rate

- **After every task commit:** Run the focused pytest or vitest command for the touched seam
- **After every plan wave:** Run the quick command above
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01 | 01 | 1 | PROMPT-01, PROMPT-02 | orchestration | `python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py tests/orchestration/test_prompt_scope.py -q --tb=short` | ✅ extend existing / ❌ new scope test | ⬜ pending |
| 13-02 | 02 | 2 | PROMPT-03 | backend/api | `python3 -m pytest tests/orchestration/test_planner.py tests/test_prompt_routing_api.py -q --tb=short` | ✅ extend existing / ❌ new API test | ⬜ pending |
| 13-03 | 03 | 3 | PROMPT-01, PROMPT-02, PROMPT-03 | frontend | `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` | ❌ Wave 0 closes missing action test | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [ ] `tests/orchestration/test_prompt_scope.py` — deterministic prompt-scope narrowing and out-of-scope symbol detection
- [ ] `tests/test_prompt_routing_api.py` — additive `route-preview` API contract and ownership behavior
- [ ] `frontend/src/actions/runs.test.ts` — unsupported preview path returns guidance and does not create or execute a run
- [ ] `frontend/src/components/chat-shell/chat-message-list.test.tsx` — rewrite suggestions render inline without run links

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Workspace chat gives immediate rewrite guidance for an unsupported prompt instead of creating a failed run | PROMPT-03 | Requires a live signed-in chat workspace and verification that no new failed run appears in the UI flow | 1. Open a project chat workspace with scope `AAPL, MSFT, NVDA`. 2. Submit an unsupported prompt like `Analyze TSLA margin pressure vs AAPL` without adding `TSLA` to scope. 3. Confirm chat shows rewrite suggestions and scope guidance. 4. Confirm no new failed run is created for that prompt. |

## Validation Sign-Off

- [ ] All planned tasks have automated verification commands or explicit Wave 0 gaps
- [ ] Sampling continuity: no 3 consecutive tasks without automated verification
- [ ] Wave 0 covers the missing prompt-scope, preview-API, and chat-action references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
