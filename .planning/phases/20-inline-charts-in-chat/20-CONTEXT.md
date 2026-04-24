# Phase 20: Inline Charts in Chat - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add deterministic inline visual evidence to the narrative chat answer so the system can show trustworthy trends and comparisons, not just describe them.

This phase covers:

- when a chart should appear in a chat answer
- the contract by which backend-safe chart specs are exposed to the frontend
- where charts sit within the answer hierarchy
- which chart families ship first
- how much captioning and interaction depth the first chart release should include

It does not broaden the answer into a dashboard, add exploratory chart controls, or allow frontend-side chart inference from arbitrary response payloads.

</domain>

<decisions>
## Implementation Decisions

### Chart trigger policy
- **D-01:** Charts should render only when they materially strengthen the answer.
- **D-02:** Responses should be capped at `1-2` charts.
- **D-03:** Phase 20 should treat charts as evidentiary support, not decorative content or a default answer embellishment.

### Chart spec source contract
- **D-04:** Backend should emit explicit safe chart specs derived from trusted artifacts or metric outputs.
- **D-05:** Frontend should only render those specs and should not infer chart types from raw answer content.
- **D-06:** Chart rendering must preserve the deterministic trust model already established for narrative previews, confidence, and supplemental evidence.

### Chart placement in the answer
- **D-07:** Charts should render inline beneath the prose answer and confidence header.
- **D-08:** Charts should appear above the supplemental evidence disclosure.
- **D-09:** Phase 20 should preserve the answer-first reading order: narrative answer, visual proof, deeper evidence.

### Initial chart families
- **D-10:** The initial chart set should include line charts for trends.
- **D-11:** The initial chart set should include grouped bar charts for peer comparisons.
- **D-12:** Simple marker or timeline overlays are allowed only when the underlying data is already explicit and deterministic.
- **D-13:** Phase 20 should not expand into pie, donut, or other decorative chart families.

### Caption and interaction depth
- **D-14:** Every chart should include one short caption explaining what it shows and why it matters.
- **D-15:** Interaction should stay lightweight: hover tooltips only.
- **D-16:** Phase 20 should not introduce chart filters, metric switches, or broader BI-style controls.

### the agent's Discretion
- Exact heuristic for whether a chart “materially strengthens” a given answer, as long as it stays within the 1-2 chart cap
- Exact chart card styling and responsive treatment within the centered answer column
- Exact tooltip and caption copy style

</decisions>

<specifics>
## Specific Ideas

- User wants charts to live inside the chat answer itself, not as a side surface or hidden-only deep dive.
- User wants the answer to stay central, with charts functioning as visual proof rather than replacing the prose narrative.
- User explicitly wants shadcn-based charts from the approved library direction, with deterministic data rather than improvised frontend graph generation.
- User is open to other ideas, but the current direction is deliberately narrow and trust-preserving.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — current `v1.3` milestone framing after Phase 19
- `.planning/ROADMAP.md` — Phase 20 goal and milestone sequencing
- `.planning/REQUIREMENTS.md` — `CHRT-01`, `CHRT-02`, `CHRT-03`
- `.planning/STATE.md` — project position after completing Phase 19

### Prior decisions that constrain this phase
- `.planning/phases/17-narrative-answer-contract/17-CONTEXT.md` — narrative answer is the primary reading surface
- `.planning/phases/18-confidence-explainer/18-CONTEXT.md` — confidence remains in the header and should not be displaced by chart chrome
- `.planning/phases/19-supplemental-evidence-disclosure/19-CONTEXT.md` — evidence is supplemental and collapsed beneath the answer

### Current answer and transparency seams
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — current answer composition and the insertion point for inline charts
- `frontend/src/lib/run-primary-view.ts` — current answer view-model seam that already carries narrative, confidence, and supplemental evidence data
- `backend/schemas/run_transparency.py` — current safe transparency surface that will need chart preview/spec support
- `backend/agents/traceability_summary.py` — current backend-derived narrative and confidence preview builder likely adjacent to any chart-preview builder
- `frontend/src/lib/api/types.ts` — typed frontend wire models for transparency-backed answer data

### UI and dependency constraints
- `frontend/package.json` — current dependency surface; no charting library is installed yet
- `frontend/src/components/ui/` — current local shadcn primitives available to extend
- `/Users/padraigobrien/.agents/skills/shadcn-ui/SKILL.md` — required shadcn guidance for chart-related component setup and usage

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatRunAnswerCard` already has a clean answer-first composition with a dedicated zone between the prose body and the supplemental evidence disclosure. That is the natural insertion point for inline charts.
- `run-primary-view.ts` is already the single frontend seam that derives narrative answer state, confidence explainer state, and supplemental evidence. Phase 20 should extend that seam rather than bolt chart logic directly into the renderer.
- `backend/schemas/run_transparency.py` already exposes safe narrative and confidence previews, so chart specs should follow the same typed preview pattern instead of inventing a second ad hoc answer payload path.

### Established Patterns
- Recent phases have consistently moved responsibility for answer meaning upstream: backend owns safe previews, frontend renders typed view models. Phase 20 should keep that split.
- The answer hierarchy is now stable: prose first, optional proof second, supplemental evidence third. Any chart placement that reintroduces a side rail or hides charts inside the disclosure would fight the direction already locked in Phases 17-19.
- The codebase currently has no existing answer-path chart implementation and no `recharts` dependency, so Phase 20 will introduce a fresh but narrow chart surface.

### Integration Points
- Backend likely needs a chart preview/spec contract adjacent to `narrative_answer` and `confidence_explainer`.
- Frontend likely needs a chart view type in `run-primary-view.ts` and a dedicated chat-answer chart renderer component.
- The shadcn chart setup will likely live under `frontend/src/components/ui/` or a chart-focused answer component package, but it should remain subordinate to the answer card, not become a general analytics subsystem.

</code_context>

<deferred>
## Deferred Ideas

- User-controlled chart filters, metric switches, or chart-builder behavior
- More decorative or non-core chart families beyond line, grouped bar, and narrow explicit overlays
- Persisting or pinning charts across follow-up messages
- Broader responsive and presentation polish beyond what is needed to fit charts into the current answer shell — Phase 21

</deferred>

---

*Phase: 20-inline-charts-in-chat*
*Context gathered: 2026-04-24*
