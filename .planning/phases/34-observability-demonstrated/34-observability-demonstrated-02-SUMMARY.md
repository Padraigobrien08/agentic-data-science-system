---
phase: 34-observability-demonstrated
plan: 02
status: completed
completed: 2026-08-08
requirements:
  - OBS-02
  - OBS-03
---

# Summary 34-02: The dashboard, captured and placed

## What shipped

- `docs/screenshots/agent-loop-dashboard.png` — full-kiosk capture, 3000×2720 at 2×, all 13
  panels populated
- README **Product Screens** gains an "Agent loop observability" section with the explicit
  framing agreed for the open decision
- `docs/observability.md` embeds the same capture beside its reading-order section

## The measured run

210 investigations over 30 minutes against `gpt-5.4-mini`, **$0.80** tracked spend.

All three health checks visibly pass, which is the point of the capture:

| Check | Result |
|---|---|
| Is it iterating? | median **1.4** iterations |
| Is it adapting? | **7 tools**, mix shifting by goal |
| Is it challenged? | transitions include `→ rejected` |

Decision latency separates the four model-backed components (~2s, `critic` peaking at 7.25s)
from the six deterministic ones (4.75ms) — a ~500× split. That panel is the concrete reason the
run was worth paying for: under the free fixture policy all ten components sit at ~5ms and the
distinction `docs/observability.md` describes is invisible.

## Caption framing

Option A (explicit) was chosen while the plan still assumed a free fixture-policy seed. The
run that actually happened was model-backed and cost money, so applying A's *principle* meant
describing that rather than repeating the plan's "zero spend" wording. The caption states the
seed, the count, the model, the spend, and that it is not production traffic.

`Component errors` and `Experiment failure rate by tool` read "No data" because nothing failed
across 210 runs. Called out in the caption rather than hidden or manufactured.

## Deviations from plan

**Captured with headless Chrome, not the browser tool.** The in-app browser rendered the
dashboard fine but became unresponsive during capture, and it returns images to the agent rather
than to disk. `Google Chrome --headless --screenshot` with `--force-device-scale-factor=2`
produced a better asset anyway: full kiosk (no nav sidebar), 2× resolution, nothing clipped.

**Three wrong time ranges before a correct one.** The seed aged out of the default 2-hour window
while the render bug was being fixed, and two hand-converted epoch ranges missed the activity.
Fixed by querying Prometheus for the exact ramp boundaries (15:14:50 → 15:38:50) instead of
converting by hand, then verifying every panel family returned values *before* asking for
another look.

## Verification

- `1066 passed, 10 skipped`; `ruff` clean; `agentic.evaluation` core green
- Prometheus confirms the captured window: 210 investigations, $0.80, tool rates 0.019–0.033/s
- The three pre-existing screenshots and every unrelated README section are untouched
  (`git diff --stat README.md` → 18 insertions, no headings changed)

## Phase 34 complete

Backlog item 1 of the standing goal is done — and it found that the documented observability
stack could not produce a dashboard at all. Four defects, all fixed and guarded, recorded in
34-VERIFICATION.md.
