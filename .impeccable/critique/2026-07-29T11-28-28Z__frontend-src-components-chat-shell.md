---
target: frontend/src/components/chat-shell
total_score: 35
p0_count: 0
p1_count: 0
timestamp: 2026-07-29T11-28-28Z
slug: frontend-src-components-chat-shell
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Live per-phase pipeline progress (spinner→check→fail). Still excellent. |
| 2 | Match System / Real World | 4 | "Technical status" relabeled to "Run details"; the last jargon label on the plain-language surface is gone. Disclosed value is still a raw status string. |
| 3 | User Control and Freedom | 4 | Stop now leaves an honest system notice ("may still finish in the background and appear in history") instead of a silent drop. The true backend limit (no mid-run abort) is now surfaced, not hidden. |
| 4 | Consistency and Standards | 4 | Focus outlines uniform across every hand-rolled control; eyebrow grammar resolved; radius fully on-scale (stray `rounded-bl-md` removed). |
| 5 | Error Prevention | 4 | Inline two-step delete confirm; new-chat disabled without tickers; scope validated. |
| 6 | Recognition Rather Than Recall | 3 | Starter prompts, scope chips, labeled icons, durable history. No new recognition aids this pass. |
| 7 | Flexibility and Efficiency | 3 | Enter / Shift+Enter / Escape / prefill. Still no command palette or new-chat keyboard shortcut. |
| 8 | Aesthetic and Minimalist Design | 4 | Delivery banner degraded-only; eyebrow labels resolved surface-wide; calm heading type. |
| 9 | Error Recovery | 3 | Clear error thesis + "open trace, retry narrower"; inline send errors; error text clears AA on dark. |
| 10 | Help and Documentation | 2 | Empty state + starter prompts teach; no contextual help beyond that. Thin for a no-account demo. Unchanged. |
| **Total** | | **35/40** | **Good (top of band) — remaining gains are feature-level, not polish** |

## Anti-Patterns Verdict

**LLM assessment:** Does not read as AI-generated. The uppercase-tracked eyebrow tell that anchored the earlier reviews is now fully resolved: tracked-caps survives only in its two reserved disclosure-toggle roles plus a single "Scope" field prefix. The zinc/Geist product register is deliberate, the trust-first content model is specific to the product, and every absolute ban is clear (no gradient text, side-stripes, decorative glass, hero-metric template, identical card grid).

**Deterministic scan:** `detect.mjs` over `frontend/src/components/chat-shell` returned `[]` — zero findings (exit 0).

**Visual overlays:** Not available — no dev server with real chat state is running and the local-file browser path did not render under the sandbox CSP. The verdict rests on source review + the clean scan; color findings were verified numerically (status inks composited against their real grounds clear 4.5:1, most 7:1+).

## What's Working

1. **Honest control surface.** Stop no longer pretends to cancel — it halts the wait and tells the user the run may still land in history. That candor is exactly the product's "never imply more than the evidence/state supports" principle applied to control flow.
2. **One consistent system.** Color (inverting `--status-*` tokens), radius (`pill/card/control/chip`), and focus (uniform accent outline) now read as a single vocabulary across chat, answer, and app-skin surfaces.
3. **Live phase progress + honesty architecture, intact.** Per-step progress and the supports/weakens/limits confidence model survived the whole restyle unchanged.

## Priority Issues

**[P2] Help & Documentation is the standout gap (score 2).** For a no-account demo, there is no contextual help at decision points — no "what is scope", no explanation of the confidence read, no guidance beyond the empty state's starter prompts. This is now the single lowest heuristic and the clearest lever left. Fix: inline, dismissible hints at first-run decision points (scope, confidence pill, evidence disclosure). → `/impeccable onboard`

**[P2] Accelerator layer is thin (Flexibility, score 3).** Enter / Shift+Enter / Escape exist, but there is no command palette, no new-chat shortcut, no keyboard path to switch threads. Power users (Alex) hit a ceiling fast. Fix: a new-chat shortcut and a minimal command palette (⌘K) over threads + starter prompts. → no direct impeccable command; treat as a feature task.

**[P3] The "Run details" value is still raw.** The label is now plain language, but the disclosed body is still the raw `orchestrationStatus` string. Humanize the value (map status enums to a sentence) so the disclosure reads like the rest of the surface. → `/impeccable clarify`

**[P3] Recognition aids could go inline (score 3).** History lives in the sidebar; recent runs and their outcomes aren't surfaced in the conversation flow. A lightweight inline "recent runs" affordance would cut recall load. → `/impeccable layout` / feature task.

## Persona Red Flags

- **Alex (power user):** Enter/Escape/delete-confirm are solid, but no command palette and no new-chat shortcut. The accelerator ceiling is the main remaining friction.
- **Sam (a11y):** Strong now — status color clears AA on dark, every interactive control has a visible accent focus outline, the Stop notice announces via the `role="log"` live region. Remaining nicety: verify the disclosed "Run details" value reads sensibly to a screen reader.
- **Riley (stress tester):** empty/partial/error/no-data handled; Stop now gives an honest "still running in the background" cue instead of a silent vanish. The edge that remains is backend-level (the run genuinely can't be aborted mid-flight), which the UI now states plainly.

## Minor Observations

- `foreground/95` and `/80` opacity modifiers still stand in for a dedicated de-emphasis token on the narrative body.
- Help/Documentation (2) and Flexibility (3) are the two heuristics gating a move into the "Excellent" band; both need feature work (contextual help, keyboard accelerators), not another polish pass.
