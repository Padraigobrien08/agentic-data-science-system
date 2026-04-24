# Phase 18: Confidence Explainer - Research

**Researched:** 2026-04-24
**Domain:** Inline confidence posture and compact explanation over the existing run-transparency and narrative-answer seams
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Confidence label contract
- **D-01:** Keep backend storage and traceability on `high | medium | low | null`.
- **D-02:** Translate that internal scale into user-facing header labels: `Good | Medium | Bad | Not rated`.
- **D-03:** Preserve existing critic/report semantics for system logic and auditability while presenting friendlier product labels in chat.

### Header density
- **D-04:** Show one compact confidence pill only, for example `Evidence strength: Medium`, with the chevron built into that pill.
- **D-05:** Do not also expose `critic: success`, `report: success`, or similar technical status labels inline in the answer header.
- **D-06:** The confidence control should read like part of the answer surface, not like a secondary technical strip.

### Explainer content shape
- **D-07:** Drive the explainer from a new safe backend rationale contract rather than loose frontend assembly from coarse caveat fields.
- **D-08:** Group the rationale into 3 sections: `what supports the rating`, `what weakens the rating`, and `what data or coverage limits matter`.
- **D-09:** The explainer must help the user understand why the rating is what it is without leaving chat.

### Inline caveat policy
- **D-10:** Keep only one short caveat rider under the answer when needed.
- **D-11:** Move the rest of the current caveat and badge bulk into the explainer instead of keeping a separate heavy caveat block inline.
- **D-12:** The inline answer should remain grounded without being visually dominated by redundant confidence chrome.

### Claude's Discretion
- Exact safe-preview rationale field names and final grouping structure
- Exact shadcn disclosure primitive choice (`Popover`, `Dialog`, or `Sheet`) by breakpoint/accessibility need
- Exact semantic status tokens and pill styling details

### Deferred Ideas (OUT OF SCOPE)
- Supplemental evidence disclosure below the answer — Phase 19
- Deterministic inline charts in chat — Phase 20
- Final responsive narrative/confidence/evidence polish — Phase 21
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONF-01 | User can see evidence strength inline in the answer header with semantic status styling for `Good`, `Medium`, `Bad`, and `Not rated` | Add a product-facing confidence view model that maps backend `high/medium/low/null` to `Good/Medium/Bad/Not rated`, and render it as a single compact header pill in the chat answer card. |
| CONF-02 | User can open a compact explainer from that header status and understand why the evidence strength received its current rating | Extend run transparency with a safe grouped rationale contract and render it through a lightweight disclosure primitive rather than a full-page confidence block. |
| CONF-03 | User can review the main caveat drivers inside the explainer without leaving chat | Move most current caveat content into the explainer groups, leaving only a short inline rider when the answer needs immediate grounding. |
</phase_requirements>

## Summary

The repo already contains almost all of the raw ingredients for Phase 18, but they are arranged in the wrong user-facing hierarchy. The backend persists coarse confidence and caveat data through `RunTransparencySummary`, while the frontend currently renders that data in a lower-page `ConfidenceStrip` plus `CaveatBadgeGroup`. That was acceptable when chat still behaved like a structured answer card, but it no longer fits the narrative-first answer introduced in Phase 17.

The right Phase 18 move is to keep the existing brownfield seams and promote confidence from a subordinate block into a product-facing header control. The backend should continue to store and reason about `high | medium | low | null`, but the frontend should render `Good | Medium | Bad | Not rated` as the user-facing label. A new safe explainer contract should then summarize why that rating exists in 3 grouped buckets: support, weaknesses, and data/coverage limits. That explainer should be opened from the confidence pill itself, not rendered as another always-visible block competing with the answer body.

The best implementation path is incremental. Extend `backend/schemas/run_transparency.py` with an explicit confidence-explainer preview object, source it from existing critic/report/traceability fields in `backend/agents/traceability_summary.py`, teach `run-primary-view.ts` to derive a product-facing confidence view, and replace the current inline `ConfidenceStrip` + `CaveatBadgeGroup` usage in `chat-run-answer-card.tsx` with a compact header pill plus disclosure. The old strip can remain available on secondary surfaces until later cleanup, but the primary chat answer should move first.

Targeted regression anchors already exist and are enough for this phase with extensions rather than new infrastructure. Backend confidence/transparency tests already cover `critic_overall_confidence`, caveats, and narrative previews. Frontend `run-primary-view` tests already verify answer derivation, and the chat answer renderer tests are the right place to lock the new header-level confidence behavior. The missing pieces are the new grouped rationale fields, the header mapping rules, and responsive disclosure coverage.

**Primary recommendation:** Add a typed safe confidence-explainer preview to run transparency, map backend confidence labels to product-facing header labels in the frontend view builder, and render the result as a single semantic pill with a compact shadcn disclosure instead of a lower-page technical strip.

## Project Constraints (from AGENTS.md / PROJECT.md)

- Keep the existing Python + FastAPI + SQLAlchemy + Next.js architecture; Phase 18 should extend the current transparency seam, not invent a separate confidence service or chat-only endpoint.
- Preserve the deterministic analysis core in `src/`; confidence explanation belongs in the persistence/API shell and frontend renderer.
- Prefer explicit seams and incremental migration over invasive refactors; reuse `backend/schemas/run_transparency.py`, `backend/agents/traceability_summary.py`, `frontend/src/lib/run-primary-view.ts`, and the existing chat answer card.
- Keep UI data access server-side and typed; the browser should render a confidence view model, not parse raw traceability structures ad hoc.
- Do not break existing traceability semantics or backend labels relied upon by tests, prompts, and persisted history.
- Follow current repo conventions: package-root imports in Python, `@/*` aliases in TypeScript, explicit typed wire mirrors, and narrow test extensions over wholesale rewrites.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | `>=0.115.0` | Expose grouped confidence rationale through the existing run detail transparency surface | The repo already uses `response_model`-backed run detail routes for safe nested previews. |
| Pydantic 2 | `>=2.0` | Define a typed confidence-explainer preview contract | Existing safe previews already use nested `BaseModel` contracts in `run_transparency.py`. |
| Next.js App Router | `^15.1.0` | Keep run fetch and hydration on the server side | Existing chat history and run fetch logic already follows this pattern. |
| React | `^19.0.0` | Render the header pill and explainer disclosure in chat | The answer surface is already a client-rendered component tree fed by typed props. |
| shadcn/ui pattern | Local repo setup | Introduce a compact disclosure primitive in `frontend/src/components/ui` | The milestone direction explicitly wants a shadcn-style explainer surface rather than custom ad hoc modal logic. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vitest | `^2.1.9` | Frontend view-model and renderer regressions | When changing `run-primary-view`, chat answer rendering, or responsive confidence disclosure behavior. |
| pytest | `>=8.0` | Backend transparency/traceability regressions | When changing grouped rationale construction or run detail response models. |
| Existing critic/report traceability outputs | Current repo | Source safe confidence rationale fields without exposing raw prompts or payloads | Use as the backend source of support/weakness/coverage-limit cues. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending `RunTransparencySummary` | Derive the explainer entirely in the frontend from `critic_blocking_caveats` and weak signals | Faster, but too lossy and brittle for a deliberate product explainer. |
| Single compact pill + disclosure | Keep the current `ConfidenceStrip` and add a second explainer affordance | Leaves the answer header noisy and duplicates the explanation burden. |
| shadcn `Popover`/`Dialog`/`Sheet` | Keep using bespoke disclosure markup | Harder to standardize accessibility, keyboard behavior, and responsive adaptation. |

**Installation:**
```bash
# No new backend packages are recommended.
# Frontend may need new local shadcn primitive files under frontend/src/components/ui/.
```

**Version verification:** No package upgrades are required for planning this phase. The likely implementation adds local component files rather than package-level dependency churn.

## Architecture Patterns

### Recommended Project Structure
```text
backend/
├── agents/
│   └── traceability_summary.py     # Build grouped confidence rationale preview
├── schemas/
│   └── run_transparency.py         # Typed confidence explainer preview model

frontend/src/
├── lib/
│   ├── api/types.ts                # Wire mirror for confidence explainer preview
│   └── run-primary-view.ts         # Product-facing confidence mapping + rider policy
├── components/chat-shell/
│   └── chat-run-answer-card.tsx    # Header pill + inline rider + disclosure integration
├── components/structured-answer/
│   ├── confidence-strip.tsx        # Candidate secondary-surface compatibility path
│   └── caveat-badge-group.tsx      # Candidate reduced role after explainer rollout
└── components/ui/
    ├── popover.tsx | dialog.tsx    # New shadcn-style disclosure primitive if missing
    └── badge.tsx                   # Existing styling base
```

## Validation Architecture

Phase 18 should follow the same validation split as Phase 17: typed backend preview construction, API exposure, frontend view-model derivation, then chat rendering/build coverage. The main new dimension is responsive disclosure behavior, which means the frontend tests should verify both the existence of the header pill and the absence of old inline technical status clutter.

Recommended validation flow:
- backend contract tests for grouped rationale parsing and serialization
- API tests for transparency payload shape
- frontend view-model tests for backend-label-to-product-label mapping and short inline rider policy
- frontend renderer tests for single-pill header behavior, grouped explainer sections, and removal of redundant `critic/report` inline labels

## Pattern 1: Backend Confidence Semantics, Frontend Product Labels
**What:** Preserve backend `high | medium | low | null` semantics for prompts, traceability, and persistence, but map them to `Good | Medium | Bad | Not rated` in the primary answer UI.

**When to use:** Everywhere the primary chat answer exposes evidence strength to end users.

**Recommended contract:**
```python
class ConfidenceExplainerPreview(BaseModel):
    rating: Literal["high", "medium", "low"] | None = None
    supports: list[str] = Field(default_factory=list)
    weakens: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)
```
```typescript
type ProductConfidenceLabel = "Good" | "Medium" | "Bad" | "Not rated";
```

**Why:** This preserves auditability and test stability on the backend while giving the UI the friendlier vocabulary the product now wants.

## Pattern 2: Grouped Rationale from Safe Traceability, Not Frontend Guesswork
**What:** Build the explainer payload in the backend from already safe critic/report/traceability fields, rather than trying to infer grouped rationale from flat caveat lists in the browser.

**When to use:** Any time the chat answer needs to explain why the rating is what it is.

**Example approach:**
```python
supports = [...]
weakens = [...]
limits = [...]

summary.confidence_explainer = ConfidenceExplainerPreview(
    rating=critic_overall_confidence,
    supports=supports[:3],
    weakens=weakens[:4],
    limits=limits[:4],
)
```

**Why:** The backend already sees the traceability summary, critic outputs, and phase statuses in one place. That is the correct layer to create a stable explanation contract.

## Pattern 3: Single Header Pill, Minimal Inline Rider
**What:** Promote confidence into the answer header as one compact pill and leave only one short rider below the answer when the user needs immediate caution.

**When to use:** The main narrative answer surface in chat.

**Example behavior:**
```typescript
const inlineRider =
  confidence.requiresImmediateRider ? confidence.shortRider : null;
```

**Why:** This preserves grounding without recreating the current wall of confidence and caveat chrome below the answer.

## Pattern 4: Responsive Disclosure Primitive Chosen by Interaction Need
**What:** Use a compact disclosure primitive that feels inline on desktop and still works on smaller screens.

**When to use:** The confidence explainer trigger opened from the answer header.

**Recommended direction:** plan against a shadcn-style `Popover` first, but design the interface so it can fall back to `Dialog` or `Sheet` on constrained viewports if needed.

**Why:** The user wants a small modal-like explainer, not a permanent block. The repo currently lacks those primitives, so this phase needs to introduce one deliberately rather than improvising.

## Anti-Patterns to Avoid

- **Expose backend labels directly to users:** Do not show raw `high`, `low`, or `critic/report` status labels in the primary answer header.
- **Duplicate confidence explanation in two places:** Do not keep the current strip plus a new pill/explainer as co-equal surfaces.
- **Frontend-only rationale synthesis:** Do not infer support/weakness/limit buckets entirely in the browser from flat strings.
- **Phase leakage:** Do not redesign supplemental evidence disclosure or add charts in this phase.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inline confidence UX | Another bespoke mini-panel with manual open/close logic | A local shadcn-style disclosure primitive | Better accessibility, consistency, and responsive behavior. |
| Product-facing rating semantics | A new backend enum replacing current traceability labels | Frontend mapping over existing backend semantics | Lower migration risk and better compatibility with persisted data/tests. |
| Explainer data source | Client-side guessing from caveat arrays | Backend-authored grouped rationale preview | More stable, auditable, and easier to test. |

## Common Pitfalls

### Pitfall 1: The Header Still Feels Technical
**What goes wrong:** The answer header shows `Evidence strength: Medium`, but also still shows `critic: success` or `report: success` nearby.
**Why it happens:** The old `ConfidenceStrip` is adapted rather than replaced for the primary answer.
**How to avoid:** Build a dedicated header confidence view for chat and keep the older strip only on secondary surfaces if needed.

### Pitfall 2: The Explainer Just Repeats Caveats
**What goes wrong:** The explainer feels like the same old caveat list in a different container.
**Why it happens:** The backend does not provide grouped rationale, so the frontend can only reshuffle existing strings.
**How to avoid:** Add explicit support / weaken / limits buckets in the safe preview contract.

### Pitfall 3: Medium/Good/Bad Styling Drifts Across Surfaces
**What goes wrong:** Different components color the same rating differently or use different words.
**Why it happens:** No single product-facing confidence mapping exists in the view layer.
**How to avoid:** Centralize the backend-to-product label and tone mapping in the typed frontend view model.

### Pitfall 4: Mobile Disclosure Becomes Awkward
**What goes wrong:** A small popover clips or becomes unusable on narrow viewports.
**Why it happens:** The phase chooses a desktop interaction pattern without a fallback plan.
**How to avoid:** Plan the explainer API and content independent of the primitive so `Popover` can degrade to `Dialog`/`Sheet` cleanly.

## Code Examples

Verified patterns from repo and current stack:

### Current Backend Confidence Surface
```python
class RunTransparencySummary(BaseModel):
    critic_blocking_caveats: list[str] = Field(default_factory=list)
    critic_overall_confidence: str | None = None
    critic_phase_status: str | None = None
    report_phase_status: str | None = None
```
**Why this matters:** Phase 18 should extend this exact seam instead of creating a second answer-status endpoint.
**Source:** `backend/schemas/run_transparency.py`

### Current Primary Chat Answer Confidence Placement
```tsx
<ConfidenceStrip
  overallConfidence={answerCard.overallConfidence}
  criticPhaseStatus={answerCard.criticPhaseStatus}
  reportPhaseStatus={answerCard.reportPhaseStatus}
  reliabilityNote={reliabilityNote}
/>
<CaveatBadgeGroup ... />
```
**Why this matters:** This is the precise hierarchy that Phase 18 needs to replace on the primary answer surface.
**Source:** `frontend/src/components/chat-shell/chat-run-answer-card.tsx`

### Current Technical-Status Leakage
```tsx
{criticPhaseStatus ? (
  <span className="font-mono text-xs text-[var(--muted)]">critic: {criticPhaseStatus}</span>
) : null}
```
**Why this matters:** This is exactly the product-noise the user wants removed from the main answer.
**Source:** `frontend/src/components/structured-answer/confidence-strip.tsx`

## Recommended Verification Commands

```bash
python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short
cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx
cd frontend && npm run build
```

## Conclusion

Phase 18 is not a new confidence system. It is a contract-and-hierarchy cleanup over the confidence data the repo already has. The backend should keep its current semantics, but it needs to expose grouped rationale through the safe transparency seam. The frontend should then map those semantics into a single product-facing header pill with one compact explainer and a minimal inline rider. That will satisfy the milestone goal without reopening the narrative-answer work or dragging future evidence/chart phases forward.
