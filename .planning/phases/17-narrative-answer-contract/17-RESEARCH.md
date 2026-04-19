# Phase 17: Narrative Answer Contract - Research

**Researched:** 2026-04-19
**Domain:** Backend-authored narrative answer previews over the existing FastAPI/Pydantic/Next.js run-transparency seam
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Narrative answer structure
- **D-01:** The default answer should start with one lead thesis sentence, then continue as 2-3 short prose sections: `What’s happening`, `Why we think that`, and `What weakens the claim`.
- **D-02:** Phase 17 should replace the current summary-card feel with a real read-through answer body rather than a headline plus stacked findings cards.

### Narrative answer source contract
- **D-03:** The backend should expose a safe narrative preview contract for chat instead of forcing the frontend to synthesize long-form prose from takeaways and caveats.
- **D-04:** The narrative answer should remain auditable and bounded by existing safe-preview patterns rather than requiring raw payload access in chat.

### Fallback answer behavior
- **D-05:** If the run cannot support a full narrative answer, the system should still return a partial-answer paragraph that says what can be stated confidently and what evidence is missing or weak.
- **D-06:** Phase 17 should avoid generic success copy, mirrored takeaway cards, or blank-looking answers as fallback behavior.

### Answer tone and voice
- **D-07:** The prose should use an analyst-memo voice: direct, cautious, concrete, and free of “assistant” framing.
- **D-08:** The answer should avoid marketing tone or generic chatbot phrasing even when the evidence is thin.

### Default answer length
- **D-09:** The default narrative answer should target roughly 120-220 words.
- **D-10:** The answer should feel substantive enough to read as the main reply, while leaving later phases room for supplemental evidence and charts below it.

### Claude's Discretion
- Exact field names and shape of the backend-safe narrative preview contract, as long as it clearly separates thesis, support, and watchouts/fallback context.
- Exact paragraph rendering pattern in chat, as long as it preserves the lead thesis plus short narrative-section structure.
- Exact heuristic for when an answer can support the full narrative contract versus when it should fall back to a partial-answer paragraph.

### Deferred Ideas (OUT OF SCOPE)
- Inline evidence-strength badge in the answer header with a click-to-explain rating surface — Phase 18
- Supplemental evidence disclosure beneath the narrative answer, with long slim evidence cards and the five secondary pills below it — Phase 19
- Deterministic inline charts in chat using shadcn/Recharts components — Phase 20
- Further narrative-layout polish and width/spacing refinement across screen sizes — Phase 21
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANSR-01 | User can read a multi-paragraph analyst answer in chat that explains the thesis, supporting evidence, and watchouts instead of a one-line summary card | Use a backend-authored `narrative_answer` preview on `RunTransparencySummary`, source successful narratives from the report-agent contract, and render thesis + short sections in the chat answer card. |
| ANSR-02 | User can receive a stable non-boilerplate fallback answer when evidence is limited, so successful runs never collapse into vague placeholder text | Add explicit `mode` (`full` or `partial`) plus coarse fallback reason on the backend, and keep a legacy compatibility path for older runs that do not have the new preview yet. |
</phase_requirements>

## Summary

The current repo already has the two critical ingredients for Phase 17, but they are split across the wrong boundary. The backend persists a full report narrative in `output_payload_json.user_facing_report.markdown`, and it already persists a safe chat-facing transparency slice in `meta_json.ai_agents.traceability`, but the chat UI still derives its primary answer from `summaryLine`, `takeawayRows`, and caveat badges in `frontend/src/lib/run-primary-view.ts`. That is why the current answer still reads like a summary card even though a fuller narrative exists elsewhere.

The right Phase 17 move is to keep the existing brownfield surfaces and promote a typed safe preview contract through them. Successful runs should author the narrative on the backend, expose a bounded `narrative_answer` object through `RunTransparencySummary`, and let the frontend render that object directly. Limited-support runs should not fall back to generic orchestration text; they should expose an explicit `partial` narrative mode that states the strongest supportable claim and then names the missing or weak evidence. Existing history hydration should remain run-backed, and older runs without the new preview should continue to render through a legacy compatibility path.

Targeted regression anchors already exist and currently pass on this checkout: `tests/test_run_transparency_builders.py` + `tests/test_sprint3_transparency_api.py` passed (`12 passed`), and the frontend answer/history/action/message-list tests passed (`11 passed`). The gap is not missing infrastructure; it is missing Phase 17-specific cases in those existing anchors.

**Primary recommendation:** Add a typed backend-authored `narrative_answer` preview to run transparency, source full narratives from the report-agent contract, and make chat consume that contract first with explicit `partial` fallback mode.

## Project Constraints (from CLAUDE.md)

- Keep the existing Python + FastAPI + SQLAlchemy + Next.js + Postgres architecture; Phase 17 should extend current seams, not add a new answer service or client-only data path.
- Preserve the deterministic analysis core in `src/`; narrative-contract work belongs in the backend persistence/API shell and frontend rendering layer.
- Prefer explicit seams and incremental migration over invasive refactors; reuse `backend/schemas/run_transparency.py`, `backend/api/routes/runs.py`, `frontend/src/lib/run-primary-view.ts`, and the existing chat hydration path.
- Avoid breaking existing run APIs, artifact access patterns, or chat history hydration without a compatibility path for older persisted runs.
- Keep UI data access server-side in `frontend/src/lib/api/*.ts`, `frontend/src/actions/*.ts`, and route handlers; the browser card remains a renderer of typed props, not a raw FastAPI client.
- Keep backend service/API boundaries intact: persistence and domain shaping in backend services/schemas, HTTP response-model wiring in routes, and safe parsing on the frontend.
- Follow existing import and type conventions: package-root imports in Python, `@/*` aliases in TypeScript, explicit typed wire mirrors in `frontend/src/lib/api/types.ts`.
- Validate through existing test infrastructure: backend `pytest`, frontend `vitest`, plus frontend lint/build on the established Next.js stack.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | `>=0.115.0` | Expose the narrative preview on `GET /v1/runs/{id}?include_transparency=true` | The repo already uses `response_model`-backed run detail routes, and FastAPI documents that `response_model` filters and serializes returned data. |
| Pydantic 2 | `>=2.0` | Define nested typed `narrative_answer` wire models | The repo already models safe preview contracts with `BaseModel`, and Pydantic explicitly supports nested models and `model_dump()` serialization. |
| `pydantic-settings` | `>=2.0.0` | Keep prompt/version/config wiring in the existing settings layer | Prompt/versioned backend behavior already routes through current settings and model-call persistence. |
| Next.js App Router | `^15.1.0` | Keep run fetch/hydration on the server side and pass typed props into chat UI | The repo already uses App Router server-side data access; Next.js documents that pages/layouts are Server Components by default and client components should be reserved for interactivity. |
| React | `^19.0.0` | Render the narrative-first chat card as a client component fed by typed props | Existing chat rendering is already a client component boundary; Phase 17 only changes the view model and layout contract. |
| Existing report-agent prompt + prompt versioning | Current prompt is `backend/agents/prompts/report/1.1.0.md`; Phase 17 should bump it | This is already where the repo authors user-facing prose, stores prompt versions, and persists model-call metadata for auditability. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vitest | `^2.1.9` | Frontend view-model and renderer regressions | When changing `run-primary-view`, chat hydration, actions, or chat rendering. |
| pytest | `>=8.0` | Backend transparency-contract and API regressions | When changing `traceability_summary`, `run_transparency`, or run-detail API responses. |
| `react-markdown` | `^10.1.0` | Render the full report artifact surface | Keep this on the full report artifact path, not the primary chat answer contract. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending `RunTransparencySummary` | Read `output_payload_json.user_facing_report` directly in chat | Breaks the existing safe-preview boundary and history reload path, and pulls chat back toward raw payload access. |
| Structured `narrative_answer` fields | Render a markdown preview directly in chat | Faster to wire, but weaker section guarantees, harder fallback testing, and more frontend parsing. |
| Reusing `buildPrimaryAnswerView` as the migration seam | Build a separate chat-only answer builder | Duplicates compatibility logic already shared by server actions and persisted history. |

**Installation:**
```bash
# No additional packages are recommended for Phase 17.
```

**Version verification:** No package additions or upgrades are required for this phase. Use the repo-declared versions in `requirements*.txt` and `frontend/package.json`.

## Architecture Patterns

### Recommended Project Structure
```text
backend/
├── agents/
│   ├── output_schemas.py          # Extend report-agent output with narrative preview fields
│   ├── prompts/report/            # Bump prompt version for thesis/section/fallback voice
│   ├── traceability_summary.py    # Persist safe narrative preview + partial fallback mode
│   └── traceable_analysis_pipeline.py
├── schemas/
│   ├── run_transparency.py        # Typed narrative preview on run transparency
│   └── api_phase_a.py             # Existing detail response wrapper
└── api/routes/runs.py             # Existing include_transparency route surface

frontend/src/
├── lib/
│   ├── api/types.ts               # Mirror backend narrative preview wire
│   ├── run-primary-view.ts        # Prefer narrative preview, legacy fallback second
│   └── chat-run-history.ts        # Persisted history compatibility
├── actions/runs.ts                # New run reply content uses narrative preview
└── components/chat-shell/
    ├── chat-run-answer-card.tsx   # Narrative-first renderer
    └── chat-message-list.tsx      # Existing transcript host
```

### Pattern 1: Backend-Authored Narrative Preview
**What:** Successful runs should author the narrative on the backend and persist a bounded `narrative_answer` preview in the existing transparency/traceability seam. The preview should be typed and explicit, not inferred from `summaryLine` or improvised in the browser.

**When to use:** Every chat answer read path, including newly executed runs and persisted history hydration.

**Recommended contract:**
```python
# Source pattern: backend/schemas/run_transparency.py + backend/agents/output_schemas.py
from typing import Literal
from pydantic import BaseModel, Field


class NarrativeSection(BaseModel):
    heading: Literal["What's happening", "Why we think that", "What weakens the claim"]
    body: str


class NarrativeAnswerPreview(BaseModel):
    mode: Literal["full", "partial"]
    thesis: str
    sections: list[NarrativeSection] = Field(default_factory=list)
    fallback_reason: str | None = None
```
**Source:** `backend/schemas/run_transparency.py`, `backend/agents/output_schemas.py`, https://pydantic.dev/docs/validation/latest/concepts/models/

### Pattern 2: Successful Narratives from the Report Contract, Partial Fallback from Traceability
**What:** The prose itself should be authored by the report-agent contract, but the fallback semantics should remain enforceable at the backend traceability layer. That means the report prompt/schema should emit the intended thesis/section structure for successful cases, while `traceability_summary.py` should still be able to construct a safe `partial` preview when the report is skipped, degraded, or undersupported.

**When to use:** Whenever the report phase succeeds but needs chat-first structure, or whenever the report phase cannot safely provide a full narrative.

**Example:**
```python
# Source pattern: backend/agents/traceability_summary.py
if report_phase_succeeded and report_preview_is_usable:
    narrative_answer = report_preview
else:
    narrative_answer = NarrativeAnswerPreview(
        mode="partial",
        thesis=best_supported_claim,
        sections=[],
        fallback_reason="limited_evidence",
    )
```
**Source:** `backend/agents/traceability_summary.py`, `backend/agents/prompts/report/1.1.0.md`

### Pattern 3: Narrative-First View Model with Legacy Compatibility
**What:** The frontend should prefer the new narrative preview, but it must keep a legacy path for older runs that only have `summaryLine`, takeaways, and caveats. Compatibility belongs in the view builder, not in the chat component tree.

**When to use:** `createAnalysisRunFromChat`, `buildProjectChatHistory`, and any future run-backed transcript hydration.

**Example:**
```typescript
// Source pattern: frontend/src/lib/run-primary-view.ts
const narrative = run.transparency?.narrative_answer;

if (narrative?.mode === "full" || narrative?.mode === "partial") {
  return buildNarrativeAnswerView(narrative, legacySupportData);
}

return buildLegacySummaryFallback(run, legacySupportData);
```
**Source:** `frontend/src/lib/run-primary-view.ts`, `frontend/src/actions/runs.ts`, `frontend/src/lib/chat-run-history.ts`

### Anti-Patterns to Avoid
- **Browser-side prose synthesis:** Do not build long-form prose from `takeawayRows`, `blockingCaveats`, and `summaryLine` in `run-primary-view.ts`.
- **Raw payload dependency in chat:** Do not require `include_payloads=true`, `output_payload_json`, or raw `meta_json` access for the chat answer.
- **Markdown parsing in the client:** Do not parse `user_facing_report.markdown` in the browser to recover the answer structure.
- **Phase leakage:** Do not move confidence-explainer chrome, evidence disclosure behavior, or inline charts into this phase.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chat narrative prose | Client-side string concatenation from takeaways/caveats | Backend-authored `narrative_answer` preview | The backend already owns report authorship, prompt versioning, and auditability. |
| Safe answer transport | New chat-only endpoint or payload bypass | Existing `GET /v1/runs/{id}?include_transparency=true` surface | Reuses the current trust boundary and history hydration path. |
| Narrative structure recovery | Browser markdown parser for headings/sections | Typed preview fields on transparency | Stronger contracts, smaller UI logic, clearer regressions. |
| History migration | New persisted chat-thread schema | Existing run-backed chat hydration | Phase 14 already established runs as the reload-safe backbone. |

**Key insight:** This phase is not a new data-source problem. It is a contract problem at the existing transparency seam.

## Common Pitfalls

### Pitfall 1: Generic Success Copy Leaks into the Thesis
**What goes wrong:** The answer opens with “Orchestration completed successfully” or similar process text.
**Why it happens:** Current code still treats `final_summary` as a candidate thesis and only filters a narrow generic-success pattern.
**How to avoid:** Make the backend emit an explicit thesis for `narrative_answer` and reject process-status text at preview-build time.
**Warning signs:** UI snapshots still show orchestration/process language as the first line of the answer.

### Pitfall 2: Older Persisted Runs Render Blank Bodies
**What goes wrong:** History hydration shows empty chat cards for runs created before Phase 17.
**Why it happens:** The frontend assumes `narrative_answer` exists on all runs.
**How to avoid:** Keep a `legacy` compatibility branch in `run-primary-view.ts` and cover it in history/action tests.
**Warning signs:** `buildProjectChatHistory()` produces cards with neither thesis nor partial paragraph for older fixtures.

### Pitfall 3: Prompt/Schema Drift Breaks the Safe Preview
**What goes wrong:** The report prompt changes shape, but `output_schemas.py`, `traceability_summary.py`, or tests are not updated together.
**Why it happens:** The repo version-controls prompt text and output schemas separately.
**How to avoid:** Bump the report prompt version in the same change as the schema/traceability update, and assert prompt-version propagation in backend tests.
**Warning signs:** Report-phase model calls show a new prompt version, but `narrative_answer` is missing or invalid.

### Pitfall 4: The UI Still Reads Like a Summary Card
**What goes wrong:** The answer card gets more text, but findings grids and side panels still dominate the reading order.
**Why it happens:** Layout changes stop at adding prose above the existing card structure.
**How to avoid:** Treat the thesis + short prose sections as the primary answer body and demote findings/caveats chrome in the renderer.
**Warning signs:** Screenshot review still reads “headline plus stacked cards” rather than “analyst reply plus supporting detail.”

## Code Examples

Verified patterns from repo and official sources:

### Expose the Safe Preview Through the Existing Run Detail Route
```python
# Source: backend/api/routes/runs.py + backend/schemas/api_phase_a.py
@router.get("/{run_id}", response_model=AnalysisRunDetailResponse)
def get_run(..., include_transparency: bool = Query(False)) -> AnalysisRunDetailResponse:
    ...
    return analysis_run_to_detail(
        row,
        include_payloads=include_payloads,
        transparency=trans,
        progress=progress,
    )
```
**Why this matters:** FastAPI's `response_model` already gives the repo a typed filtering seam for adding nested narrative preview fields without inventing a new endpoint.
**Source:** `backend/api/routes/runs.py`, `backend/schemas/api_phase_a.py`, https://fastapi.tiangolo.com/tutorial/response-model/

### Keep Server Fetching and Client Rendering Split
```typescript
// Source: frontend/src/actions/runs.ts
const hydratedRun = await getRun(run.id, { includeTransparency: true });
const answerView = buildPrimaryAnswerView(
  hydratedRun,
  artifacts,
  orch,
  userReport,
  ai,
  hydratedRun.transparency,
  nav,
);
```
**Why this matters:** The data fetch and shaping stay on the server side, while the client chat card only renders typed props. That matches the current App Router architecture and avoids pushing safe-preview logic into the browser.
**Source:** `frontend/src/actions/runs.ts`, https://nextjs.org/docs/app/getting-started/server-and-client-components

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `summaryLine` plus findings/confidence cards as the primary chat answer | Typed `narrative_answer` preview with `full` / `partial` modes and narrative-first rendering | Recommended for Phase 17 planning on 2026-04-19 | Makes chat the real reading surface instead of a compressed summary artifact. |
| Frontend derives the primary answer from `final_summary`, takeaways, and caveats | Backend authors and bounds the answer contract, frontend renders it | Recommended for Phase 17 planning on 2026-04-19 | Improves auditability, fallback stability, and history compatibility. |
| Generic success/no-structured-findings empty-state text | Explicit partial-answer paragraph with coarse backend reason codes | Recommended for Phase 17 planning on 2026-04-19 | Prevents successful runs from collapsing into vague placeholder copy. |

**Deprecated/outdated:**
- Treating `summaryLine` as the main answer contract in chat.
- Requiring the browser to infer long-form prose from safe-preview fragments.
- Using raw payload access as the path to a richer answer.

## Open Questions

1. **Should the report-agent schema emit the structured preview directly, or should traceability derive it from markdown?**
   - What we know: the current report prompt (`1.1.0`) authors `user_report_markdown` and `key_takeaways`, but it does not enforce the Phase 17 section contract.
   - What's unclear: whether a markdown-derived preview would stay robust enough as prompt text evolves.
   - Recommendation: plan for a prompt-version bump plus a structured preview field on the report-agent output; only fall back to markdown-derived preview generation if implementation proves that schema expansion is disproportionate.

2. **What coarse fallback reasons should the UI understand?**
   - What we know: current code already distinguishes `no_data`, empty panel, zero anomalies, report missing, and empty evidence-map states.
   - What's unclear: how many of those should surface as stable UI-facing reason codes versus staying internal implementation detail.
   - Recommendation: keep the chat-facing reason taxonomy coarse (`limited_evidence`, `report_unavailable`, `no_data`, `legacy`) and avoid exposing raw agent failure classes or orchestration internals in the answer body.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend tests and schema work | ✓ | `3.11.0` | CI and Docker already use Python `3.12`; use those as authoritative if local-version issues appear. |
| Node.js | Frontend tests and Next.js build | ✓ | `v24.9.0` | CI already covers Node `20`; repo docs target Node `22+`. |
| npm | Frontend scripts | ✓ | `11.6.0` | None needed. |
| pytest | Backend validation | ✓ | `8.4.2` | Run through `python3 -m pytest` instead of relying on a shell alias. |
| Vitest | Frontend validation | ✓ | `2.1.9` | Available via local `frontend/node_modules`; use `npx vitest run`. |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- Local Python is below the repo's documented `3.12+` target; backend validation still ran here, but final authority should remain CI/Docker on Python `3.12`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 8.4.2` (backend) + `Vitest 2.1.9` (frontend) |
| Config file | `pytest.ini`, `frontend/vitest.config.ts` |
| Quick run command | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q` and `cd frontend && npx vitest run src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/actions/runs.test.ts` |
| Full suite command | `python3 -m pytest tests/ -q --tb=short` and `cd frontend && npm run lint && npm run build && npx vitest run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANSR-01 | Narrative answer preview is returned from the backend and rendered in chat as thesis + support/watchouts prose | backend unit/API + frontend unit/component | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q` and `cd frontend && npx vitest run src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/actions/runs.test.ts` | ✅ |
| ANSR-02 | Limited-support runs return stable partial-answer prose and persisted history still hydrates non-boilerplate content | backend unit/API + frontend unit/history | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q` and `cd frontend && npx vitest run src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/actions/runs.test.ts` | ✅ |

### Sampling Rate
- **Per task commit:** Run the focused backend transparency tests and focused frontend answer/history tests.
- **Per wave merge:** Run backend full `pytest`, frontend `lint`, frontend `build`, and frontend `vitest`.
- **Phase gate:** Full suite green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_run_transparency_builders.py` — add `narrative_answer` full/partial/legacy contract cases for ANSR-01 and ANSR-02.
- [ ] `tests/test_sprint3_transparency_api.py` — assert run detail exposes the new narrative preview without mutating payload behavior.
- [ ] `frontend/src/lib/__tests__/run-primary-view.test.ts` — cover narrative-first derivation, partial fallback, and older-run legacy compatibility.
- [ ] `frontend/src/lib/chat-run-history.test.ts` — cover persisted history hydration with the new narrative contract and with pre-Phase-17 runs.
- [ ] `frontend/src/components/chat-shell/chat-message-list.test.tsx` — assert thesis/section rendering and partial-paragraph rendering in the transcript.
- [ ] `frontend/src/actions/runs.test.ts` — assert server-action reply content and `answerCard` use the narrative contract instead of `summaryLine`.

## Sources

### Primary (HIGH confidence)
- Repo context and requirements:
  - `.planning/phases/17-narrative-answer-contract/17-CONTEXT.md`
  - `.planning/PROJECT.md`
  - `.planning/ROADMAP.md`
  - `.planning/REQUIREMENTS.md`
- Repo implementation seams:
  - `backend/agents/output_schemas.py`
  - `backend/agents/prompts/report/1.1.0.md`
  - `backend/agents/traceability_summary.py`
  - `backend/agents/traceable_analysis_pipeline.py`
  - `backend/schemas/run_transparency.py`
  - `backend/api/routes/runs.py`
  - `frontend/src/lib/api/types.ts`
  - `frontend/src/lib/run-primary-view.ts`
  - `frontend/src/actions/runs.ts`
  - `frontend/src/lib/chat-run-history.ts`
  - `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
- Repo regression anchors:
  - `tests/test_run_transparency_builders.py`
  - `tests/test_sprint3_transparency_api.py`
  - `tests/test_traceable_pipeline.py`
  - `frontend/src/lib/__tests__/run-primary-view.test.ts`
  - `frontend/src/lib/chat-run-history.test.ts`
  - `frontend/src/components/chat-shell/chat-message-list.test.tsx`
  - `frontend/src/actions/runs.test.ts`
- Official docs:
  - Pydantic Models: https://pydantic.dev/docs/validation/latest/concepts/models/
  - FastAPI Response Model: https://fastapi.tiangolo.com/tutorial/response-model/
  - Next.js Server and Client Components: https://nextjs.org/docs/app/getting-started/server-and-client-components

### Secondary (MEDIUM confidence)
- None.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Phase 17 can stay on the repo's existing FastAPI/Pydantic/Next.js stack with no new dependencies, and the relevant framework behavior is confirmed by official docs.
- Architecture: MEDIUM - The correct seam is clear, but the exact choice between prompt-schema expansion and markdown-derived preview generation still needs implementation-time confirmation.
- Pitfalls: HIGH - The current code and passing regression anchors make the main failure modes concrete and testable.

**Research date:** 2026-04-19
**Valid until:** 2026-05-19
