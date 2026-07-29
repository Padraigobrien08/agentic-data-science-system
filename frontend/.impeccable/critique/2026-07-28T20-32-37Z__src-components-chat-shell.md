---
target: the chat
total_score: 33
p0_count: 0
p1_count: 0
timestamp: 2026-07-28T20-32-37Z
slug: src-components-chat-shell
---
# Critique — the chat (src/components/chat-shell)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Live pipeline progress from real committed run state — excellent |
| 2 | Match System / Real World | 3 | Raw system fields leak (net_margin, overall_confidence: low, "Evidence strength: Bad") |
| 3 | User Control and Freedom | 3 | No way to cancel a run in progress (30s–2min, composer disabled) |
| 4 | Consistency and Standards | 3 | Visual system breaks at "View trace →" (warm shell) |
| 5 | Error Prevention | 3 | Composer disabled while running; scope validated. Solid |
| 6 | Recognition Rather Than Recall | 4 | Starter prompts, visible scope, history |
| 7 | Flexibility and Efficiency | 3 | No keyboard accelerators (⌘K, new chat, focus composer) |
| 8 | Aesthetic and Minimalist Design | 4 | Clean zinc/Geist, on-brand; chart still rough |
| 9 | Error Recovery | 3 | Error shell + trace link present; raw error text could be softer |
| 10 | Help and Documentation | 3 | Empty state teaches; no deeper help (fine for demo) |
| **Total** | | **33/40** | **Excellent band** |

## Anti-Patterns Verdict
- Deterministic scan: clean (`[]`, exit 0) across chat-shell + structured-answer. No slop patterns.
- LLM: does NOT read as AI-generated. Earned-familiar (Vercel/Linear-adjacent), clean zinc, Geist, no gradient text, no glassmorphism, no eyebrow-per-section, no hero-metric template. Passes the product slop test.
- Residual tell: raw snake_case fields (net_margin, debt_to_assets, overall_confidence) surface in mono — the tool showing its database columns.

## What's Working
1. Live pipeline progress driven by real polled run state — visibility done right, far above a spinner.
2. Honest answer surface — confidence read + "what weakens the claim" + traceable evidence; matches show-your-work.
3. Frictionless entry — guest demo + one-click starter prompts; a real analysis with no login.

## Priority Issues
- [P2] Raw system fields leak into the answer (net_margin, "overall_confidence: low", "Evidence strength: Bad"). Undermines the precise/trustworthy voice. Fix: humanize field names + confidence wording. → /impeccable clarify
- [P2] No cancel control for an in-progress run. User is stuck behind a disabled composer for up to ~2min. Backend supports cancel. → /impeccable harden
- [P2] Inline chart rough — "Strong shift" markers clip the top edge, axis/gridlines under-tuned for dark. → /impeccable polish
- [P3] Visual system breaks at the chat boundary ("View trace →" → warm shell). → /impeccable polish
- [P3] No keyboard accelerators for power users. → /impeccable harden

## Persona Red Flags
- The Analyst (power user): no keyboard shortcuts; no cancel-run; can't compare two runs side by side. Density serves them well.
- The Demo Visitor (first-timer): raw fields (net_margin, debt_to_assets) + "Evidence strength: Bad" are jarring for a non-analyst; the 5 nav chips (Report/Evidence/Artifacts/Critic/Trace) are unexplained jargon; leaving to trace breaks the polish.

## Minor Observations
- Empty state floats a touch high in the vertical space.
- Sidebar top is bare icons (no wordmark).
- Composer width (48rem) narrower than the answer column (58rem).

## Questions to Consider
- What if the confidence read led the answer instead of sitting as a pill?
- Does a demo visitor need 5 raw nav chips, or would progressive "See the evidence" serve better?
- What would a version that never shows a raw database field name look like?
