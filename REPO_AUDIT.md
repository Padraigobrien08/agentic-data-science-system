# Repository Audit — README Promise vs Actual User Experience

**Auditor:** independent, evidence-driven review
**Date:** 2026-08-26
**Commit audited:** `d75bb78` (main, clean tree)
**Method:** README-only expectation contract frozen before any code inspection; then repository
inspection; then live execution of every advertised journey the environment permitted.

**Environment notes.** Docker was not available on the audit host, so the Compose stack was
validated statically (`docker compose config` exit 0) rather than run. The repository root
contained the owner's real `.env` including a live OpenAI key; I overrode it with explicit
environment variables to simulate a clean clone, and deliberately made **no live model calls**
so as not to spend the owner's money. Every claim depending on a live model provider is marked
**NOT VERIFIED** below with the reason. No repository file was modified; two files touched
incidentally by advertised commands (`data/evaluation/*.json`, `frontend/next-env.d.ts`) were
restored, and the tree was confirmed clean at the end.

---

## 1. Executive verdict

```
README quality:              6.5 / 10
README → reality alignment:  6.0 / 10
Actual system quality:       8.5 / 10
Developer onboarding:        4.5 / 10
Agentic-system credibility:  7.0 / 10
Portfolio effectiveness:     6.0 / 10
```

**This is a substantially better repository than its README makes it look, and the README is
simultaneously more confident than the product it fronts.** Those two failures point in
opposite directions, which is why the scores do not cluster. The engineering underneath —
particularly `agentic/agent/narrative.py`, `agentic/agent/alternatives.py`, the deterministic
`TerminationPolicy`, the replay/diff endpoint, and the agency evaluation suite — is genuinely
strong, unusually self-critical, and mostly invisible from the front page. Meanwhile the
README's headline framing ("An agent that investigates a dataset adaptively") describes a
capability level the *default* product path does not have and the *opt-in* path only partly has.

The verification results are mostly good. The full backend suite passes clean (1,444 passed, 10
skipped, 1,454 collected, 93s); `ruff` passes; 236 frontend tests pass, matching the README's
number exactly; the six published runs in the README table are byte-accurate against the
committed export, and `scripts/sync-readme-facts.py --check` confirms CI enforces it. Every one
of the 107 evidence records carries a non-null `experiment_result_id` — the product's central
provenance claim holds at the data level, and the two tests the README names for it both pass.
The static export is *key-identical* to the API's `InvestigationDetail` schema, so "the same
bytes the API serves" is literally true. Both MCP servers complete a real stdio handshake and
list exactly the tools and resource templates the README describes. The offline CLI commands all
run with no network and no key. The `/demos` replay tier works with no backend at all, and its
trace page is the best thing in the repository.

The gap is onboarding and positioning. **A developer who follows the README exactly cannot
reach the advertised experience.** I ran it: `cp .env.example .env` with the three named
secrets, migrate, bootstrap an admin — and `POST /v1/investigations` returns
`409 The agentic investigation engine is disabled`. The agentic engine requires three
independent conditions (`backend/services/agentic_investigation_execution_service.py:135-162`):
the `EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED` flag, a per-run `engine: agentic` opt-in, and the
`adaptive` access tier. The README discloses the first as a "Known limit" at line 276 and never
mentions the other two. Worse, none of that is the real blocker: with the flag on but no API key,
the loop falls back to `FixtureAgentPolicy`, whose own docstring says *"Deterministic fixture
policy for tests"* and which emits exactly one placeholder hypothesis. I ran a real investigation
through it against a rival-explanations goal and got `"delivery_days has a describable
distribution"` → `declined`, no narrative. **Every behaviour the README is about — competing
hypotheses, mutual exclusivity, `refuted`, `unanswerable_premise` — requires an OpenAI API key,
and the README never says so.** The one place it addresses the question, "No API key? The
deterministic core runs offline," points at three CLI commands and implies the gap is smaller
than it is.

Positioning is the second problem. The README's quickstart ends "Bootstrap an admin, then ask a
question in the chat." I did that. The chat surface says *"Deterministic SEC analysis with
traceable evidence"* and routes to `edgar_project/orchestration/` — a 3,890-line rule-based
planner that selects among **four hardcoded plan templates** (`plan_templates.py:32-135`). It is
a good system, but it is not the loop the README spent 200 lines describing, and the README's
architecture diagram does not contain it at all. The three "Product surfaces" screenshots are of
*that* path, are branded "EDGAR Analysis" (the app is now "auditable-loop"), date from April 25 —
four months stale — and one of them has a Next.js dev-error badge reading "1 Issue" visible in
the corner. The far superior agentic trace page I browsed at `/demos/{slug}/trace` — full
decision timeline, claim→evidence→experiment→artifact drill-down, and every model call with its
prompt, response, tokens, latency and cost — is not screenshotted anywhere.

Two concrete defects found by execution. First, a **user-visible bug on the first interactive
step of the advertised local journey**: creating a chat renders a red `NEXT_REDIRECT` error while
silently succeeding, because `frontend/src/actions/projects.ts:45` calls Next's `redirect()`
inside a `try` whose `catch` swallows the control-flow exception. Second, the README's
"Measured" row cites `suite_agency_v1`, but the shipped suite is `suite_agency_v2` and the
scoreboard doc says so — stale in the one row that carries the project's headline benchmark. I
verified the deterministic-baseline half of that benchmark directly (hard tier: 0/5, exactly as
claimed); the `gpt-5.4-mini` 60% row is **NOT VERIFIED** for want of a key.

On agency: the README implies Level 3–4. The main user-facing path is **Level 2**. The opt-in
agentic path is a **weak Level 3** — and I can be precise about why, because the evidence is in
the repository's own published runs. `expected_information_gain` is a fixed function of planner
position (`0.85 - 0.1 * prio`, `components.py:377`), candidates are drained once run, and across
all six published runs the loop executed *every* candidate tool for its intent in the planner's
declared order. The LLM selector does make real choices — it picked index 2 or 3 rather than 0 on
three occasions — but it is choosing the *order* of a fixed set, not the set. The flagship
`edgar-margin-vs-growth` run terminated via `finalize_no_candidates`, i.e. it ran out of things to
do; the README narrates that as "a run that disproved its own hypotheses has settled the matter."
To the repository's credit, its own Known Limits section concedes the `expected_information_gain`
point — but frames it as a gap in *evaluation coverage* rather than as a limit on adaptivity.

---

## 2. What I thought this repo was after reading the README

A reader finishing the README forms this model:

A **general, dataset-agnostic adaptive investigation agent** with a rigorously enforced split —
the LLM plans and interprets, deterministic code computes every number — where SEC EDGAR is
merely the flagship adapter. The agent takes a plain-language goal, proposes competing
hypotheses, **chooses each next experiment from what it has learned so far**, revises claims when
evidence contradicts them, critiques its strongest claim, refuses to conclude while two of its
own claims disagree, and halts for an explicit typed reason. Ten small deterministic components.

Auditing is the differentiator: every claim traces down without a gap, conclusion → evidence →
experiment → typed tool envelope → artifact → rows, and the model calls are audited on the same
footing at `GET /v1/runs/{id}/llm-usage`.

Operationally it reads as production-shaped: budgets on experiments/iterations/wall-time/spend,
deterministic IDs and per-iteration checkpoints so a resumed run reaches the same state, a
replay-and-diff facility, an agency benchmark with published numbers, OTel spans, Prometheus
metrics, a Grafana dashboard, two MCP servers, a committed OpenAPI contract enforced in CI, and
~1,438 backend + 236 frontend tests.

Getting there reads as trivial: `cp .env.example .env` with three secrets, `docker compose up
--build`, bootstrap an admin, ask a question in the chat. If you have no API key, "the
deterministic core runs offline" via three CLI commands.

The Known Limits section is candid enough that it *increases* trust — which makes its omissions
land harder. A careful reader notes the engine is off by default and that "the hosted demo
enables it for invite-code accounts only," but reads that as a hosting/cost decision, not as a
statement that their local clone will not do the thing either.

**What the reader does not learn from the README at all:** that an OpenAI key is required for
every advertised behaviour; that a second, larger, rule-based orchestration system is the default
and is what the chat actually uses; that there are three access tiers; that there is a
one-click no-account guest path; that there is a designed marketing landing page; or that the
`/demos/{slug}/trace` page is the strongest artifact in the project.

---

## 3. What the repo actually is

**Two analysis systems and one showcase tier, sharing auth, persistence, artifacts and a frontend.**

**Reusable / general core — `agentic/` (5,916 LOC).** Standalone, offline-safe, and genuinely
decoupled: I confirmed it imports nothing from `backend/` and no structlog/OTel/Prometheus
(instrumentation crosses the `AgentObserver` seam at `agentic/agent/observer.py`). Ten components
in `agentic/agent/components.py` (1,336 LOC) wired by `InvestigationLoop`
(`agentic/agent/loop.py`). A four-method `AgentPolicy` protocol is the only LLM seam;
`FixtureAgentPolicy` is the deterministic stand-in. Domain models in `agentic/domain/` carry no
SQLAlchemy. Adapters in `agentic/adapters/` cover generic tabular and EDGAR.

**EDGAR-specific — `src/` (deterministic computation) + `edgar_project/`.** `src/` is reachable
only through `edgar_project/mcp/adapters.py`; the boundary is enforced by AST-parsing tests
(`tests/agentic/test_domain_boundary.py`, `tests/test_backend_boundaries.py`) which I ran and
which pass.

**The deterministic path (the default, and what chat uses) — `edgar_project/orchestration/`
(3,890 LOC).** A pure rule-based planner maps a goal to one of four plan templates
(`anomaly_unusual_changes`, `trend_deterioration`, `peer_comparison`,
`mixed_trend_and_anomaly`), an executor drives MCP tools, and LLM agents handle critique and
report writing only. Entered via `backend/services/edgar_pipeline_execution_service.py`.
**This path is entirely absent from the README's architecture diagram.**

**The agentic path (opt-in) — `backend/services/agentic_investigation_execution_service.py`.**
The single wiring point between `backend/` and `agentic/`. Gated by flag + per-run opt-in +
`adaptive` tier. Checkpoints each iteration into `SqlAlchemyInvestigationStore`.

**Backend — `backend/` (214 files).** FastAPI `/v1` with 50 paths, worker with lease-based queue
reclaim, JWT auth with three access tiers (`guest`/`standard`/`adaptive`), spend guard with
per-account and global ceilings, artifact storage (local or S3), retention maintenance,
alembic migrations that apply on both SQLite and Postgres.

**MCP — two real servers, both verified live over stdio.** `backend/mcp/` exposes the platform
as 9 tools + 2 resource templates (`artifact://{id}`, `investigation://{id}/conclusion`) and is a
pure HTTP client of `/v1` — it may not import `backend/repositories|models|db|services`, enforced
by test. `edgar_project/mcp/` exposes 7 deterministic computation tools.

**Frontend — `frontend/` (25,769 LOC TS/TSX, 230 files).** Next.js App Router, server-side-only
API access, 23 routes. Three distinct surfaces: a designed marketing landing page at `/`, the
authenticated chat/investigation product, and the `/demos` replay tier.

**Persistence & showcase.** Postgres (SQLite for dev), plus a committed static export in
`frontend/src/lib/demo-static/` — six runs with full detail and full model-call captures. When
`NODE_ENV=production` and no `API_URL` is set, the frontend serves those directly, so `/demos`
works with zero backend. I built and ran it; it does.

**Evaluation — two suites.** `edgar_project/evaluation` (5 fixture benchmark cases, offline) and
`agentic/evaluation` (`suite_agency_v2`: 13 core + 5 hard cases, 9 properties, verdicts derived
from persisted typed state rather than a model judging a model).

**Observability.** `BackendAgentObserver` emits `agent.investigation → agent.iteration.N →
agent.component.{name}` spans plus structured logs and Prometheus metrics; a 13-panel Grafana
dashboard and alert rules live in `ops/`, behind an optional Compose overlay.

### Where the project is more interesting than the README makes apparent

1. **`agentic/agent/narrative.py`** (339 lines, ~55 of them a design essay). A role-aware
   numeric verifier that checks every figure in LLM prose against the run's recorded values *in
   the semantic role the prose puts it in* — so "7" is admissible as an experiment count only in
   a clause about experiments, and refused next to "% revenue". It documents its own failed
   first version (a flat set of numbers that let `"Revenue grew 7% while margin fell 3%"` pass),
   holds digits to a stricter standard than number-words with a stated reason, and refuses
   multiplicative relations. This is the mechanism that actually *enforces* the README's headline
   invariant, and the README mentions it only as a Known-Limits bullet.
2. **The `/demos/{slug}/trace` page.** Decision-by-iteration timeline, per-claim evidence with
   strength/reliability/coverage, per-experiment artifacts with byte sizes, open questions "left
   open on purpose", and every model call expandable to its system prompt, request and response.
   Not screenshotted in the README.
3. **`agentic/agent/alternatives.py`.** 64 lines that decide, with no model, whether a goal poses
   two rival explanations — by requiring an auxiliary/copula/pronoun after "or" so "compare
   revenue or margin" is excluded but "does staffing explain it, or is volume the driver" is not.
4. **`TerminationPolicy` / `finalize_no_candidates`** (`components.py:917-993`). The comments
   record two real bugs fixed — firing sufficiency on the first supported claim stranded others
   at `proposed`; running out of candidates once reported `sufficient_evidence` with a rival
   explanation untested.
5. **`docs/agent/agency-scoreboard.md`.** A benchmark that reports its own failures in detail,
   explains that a case was previously "dropped as unwinnable" because of a planner limitation
   since removed, and retains previous measurements.
6. **The replay/diff endpoint**, which I ran live: `identical: same conclusion, termination, and
   experiment sequence`, with per-hypothesis deltas and tool set/order comparison.
7. **`select_run_engine`'s fail-closed design.** A run whose user cannot be resolved falls back to
   the cheap engine, with the comment "the failure mode of this function must never be 'grants
   the engine that costs money'."

---

## 4. Expectation Contract results

Verdict key: **Met** · **Exceeded** · **Partially met** · **Misleading** · **Not implemented** ·
**Not verifiable**.

| # | Claim / expectation | Verdict | Evidence | Severity if mismatched |
|---|---|---|---|---|
| E1 | Dataset-agnostic adaptive agent | Met | `agentic/adapters/tabular.py` + `edgar.py`; ran a live CSV investigation through `/v1/investigations` | — |
| E2 | EDGAR is an adapter, not the architecture | Met | `tests/agentic/test_domain_boundary.py` passes; grep confirms `agentic/` imports no `backend/` | — |
| E3 | Trace every step back to the number | Met | `/demos/{slug}/trace` shows conclusion→claim→evidence→experiment→artifact; artifact bytes downloadable | — |
| E4 | Flagship run: 7 experiments, both hypotheses rejected, `refuted` | Met | `edgar-margin-vs-growth.json`: 7 experiments, 7 evidence, both `rejected` at 0.05, `kind: refuted` | — |
| E5 | "Real run against live SEC filings" | Met | `origin: live`, `content_hash: sha256:7aeb4e…`, 49 rows; independently fetched live artifacts show CIK 320193/789019 | — |
| E6 | Mutual exclusivity detected deterministically pre-scoring | Met | `alternatives.py:49` (pure regex, no model); applied at `components.py:204-207` before any scoring | — |
| E7 | Deterministic code weakens both, reports `contradicted` at 0.5 | Met | `_record_exclusive_conflict` (`components.py:1266`); `csv-staffing-vs-service.json` shows both `weakened` at 0.5, `contradiction_found: true` | — |
| E8 | Provenance asserted by named tests | Met | `test_evidence_provenance_link.py`, `test_investigation_evidence_link_readmodel.py`, `test_mutual_exclusivity.py` — 30 passed | — |
| E9 | `GET /v1/runs/{id}/llm-usage` with prompt/response/tokens/cost/latency per phase | Met | Route present in OpenAPI; called live (returned totals + phases); capture files carry `request_payload_json` / `response_payload_json` per call | — |
| E10 | "No number in that trace was produced by a language model" | Met | `narrative.py` enforces it on prose; live deterministic run produced 19 artifacts with `call_count: 0`; every evidence `claim` derives from a computed statistic | — |
| E11 | Same loop on non-financial data, no special-casing | Met | Only divergence is `EDGAR_INTENT_TOOLS` prepended when `is_edgar_manifest` (`components.py:307`) | — |
| E12 | `Data` column labels synthetic vs live honestly | Met | `_dataset_origin` defaults to `unknown` rather than assuming real (`agentic_investigation_execution_service.py:102`) | — |
| E13 | `unanswerable_premise`: 0 experiments, 0 claims | Met | `csv-unanswerable-moat.json`: `experiments: 0, hypotheses: 0, evidence: 0`, `kind: unanswerable` | — |
| E14 | Published-runs table generated and CI-checked | **Partially met** | `sync-readme-facts.py --check` passes and is a CI job — but `--check` compares **table rows only**; the trailing test counts are excluded by design (`sync-readme-facts.py:158,164`) | Low |
| E15 | "1,438 backend tests · 236 frontend tests" | **Partially met** | Frontend exact (236). Backend actual **1,454 collected** — README is 16 stale, and CI cannot catch it per E14 | Low (ironic given the script's own docstring about drift) |
| E16 | `/demos` browsable, no backend | Met | Built and ran `next start` with no `API_URL`; `/demos` and `/demos/{slug}/trace` fully functional (`demos.ts:23-28`) | — |
| E17 | "The same bytes the API serves" | **Exceeded** | Static export key set is **identical** to the OpenAPI `InvestigationDetail` schema — verified programmatically | — |
| E18 | Hosted URL "pending first deploy" | Met | Honest; no dead link | — |
| E19 | `cp .env.example .env` + `docker compose up --build` = whole stack | **Partially met / Not verifiable** | `docker compose config` exits 0; the three README-named vars are exactly the three `${VAR:?}` requireds. Containers not run (no Docker on host) | Medium |
| E20 | "Bootstrap an admin, then ask a question in the chat" | **Misleading** | Bootstrap works and grants `adaptive` (`auth.py:137`). But the chat routes to the **deterministic** chain, and with the README's config the answer degrades to *"the evidence is too limited to support a full narrative answer / llm_provider_unavailable"* — observed live | **High** |
| E21 | `edgar_project.cli demo --fixtures` runs offline | Met | Ran: 5/5 cases passed, 0.457s CPU, no network | — |
| E22 | `edgar_project.cli evaluate` = offline regression suite | Met | Ran: 5 passed, 0 failed. (Side effect: rewrites two **tracked** files under `data/evaluation/`) | Low |
| E23 | `python3 -m agentic.evaluation` = agency benchmark | Met | Ran offline: `suite_agency_v2: 14/14 core cases passed (100%)`, all 9 properties 100% | — |
| E24 | Live SEC validation operator-only behind `--allow-live` | Met | Flag present; default suite is `suite_fixtures_v1` and touches no network | — |
| E25 | `scripts/record_demo.py` reproduces a recorded investigation | **Not verifiable** | Script present and documented; requires a model provider to produce a comparable run | Low |
| E26 | Architecture diagram matches reality | **Misleading** | Diagram shows only the agentic path. The **default** path (`edgar_project/orchestration/`, 3,890 LOC, 4 plan templates) is absent, and it is what the chat uses | **High** |
| E27 | MCP goes through `/v1`; no back door | Met | `backend/mcp/client.py` is an HTTP client; import restriction enforced by `tests/test_backend_boundaries.py` | — |
| E28 | Loop chooses experiments from what it has learned; ten components | **Partially met** | Ten components confirmed (`loop.py:117-127`). But `expected_information_gain = 0.85 - 0.1*prio` is positional (`components.py:377`), candidates drain once run, and all six published runs executed the full intent tool set in declared order. Only critique-driven falsification is state-dependent | **High** |
| E29 | Budgets + deterministic caps + spend guard | Met | `LoopBudget`/`SafetyLimits` (`budget.py`); `spend_guard.py` per-account and global ceilings, wired at `settings.py:283+` | — |
| E30 | Deterministic IDs; resumed run == uninterrupted | Met | `_stamp_run_scoped_ids` (`loop.py:80`), `DeterministicIds`; 82 tests pass under `-k "replay or resume or checkpoint or diff"` | — |
| E31 | Replay under a different model/prompt/budget, and diff | Met | Called `POST /v1/investigations/{id}/replay` live → `verdict: identical` with tool sets, order flag, and per-hypothesis deltas. Cross-*model* replay **Not verified** (no key) | — |
| E32 | `suite_agency_v1`; baseline 0%, `gpt-5.4-mini` 60% on hard, 5 trials | **Partially met / obsolete** | Shipped suite is **`suite_agency_v2`**; the scoreboard doc says so and the README does not. Baseline hard tier **verified 0/5**. Model row **NOT VERIFIED** (no key); raw JSON is committed | Medium |
| E33 | OTel spans `agent.investigation → agent.iteration.N → agent.component.{name}` | Met | `backend/observability/agent_observer.py:127,197` emit exactly those names | — |
| E34 | `agentic/` imports no `backend/`, no structlog/OTel/Prometheus; `agentic/domain` no SQLAlchemy | Met | Grep confirms zero matches outside a docstring; boundary tests pass | — |
| E35 | Dashboard = seeded local run, reproducible | Met | `scripts/seed-agent-activity.py` exists, is documented as offline-by-construction, and warns that a machine with a provider configured *will* spend money | — |
| E36 | Screenshots represent current runtime | **Misleading / obsolete** | All three product screenshots dated **2026-04-25**; branded "EDGAR Analysis" (app is now "auditable-loop"); light theme (product surface is dark); `run-trace.png` shows a Next.js dev-error badge reading **"1 Issue"**; all three show the *deterministic* path, not the agentic one | **High** |
| E37 | Committed OpenAPI enforced in CI | Met | `export-openapi.py` regenerated → zero diff; CI job "API contract (OpenAPI)" runs `--check` | — |
| E38 | Platform MCP: tools + resources, bearer auth | Met | Live stdio handshake: 9 tools, resource templates `artifact://{artifact_id}` and `investigation://{investigation_id}/conclusion` | — |
| E39 | EDGAR MCP exposes deterministic computation tools | Met | Live handshake: 7 tools (`resolve_company` … `run_pipeline`) | — |
| E40 | Extending guide accurate | Met (spot-check) | `docs/extending.md` (147 lines) matches the adapter/registry/policy seams found in code | — |
| E41 | Agentic engine off by default; deterministic chain is default | Met (understated) | `settings.py:266` default `False`. But **three** conditions gate it, not one (`select_run_engine`) — README names only the flag | Medium |
| E42 | Hosted MCP handshake unauthenticated, invocation authed + rate-limited | Met | `backend/mcp/auth.py`, `rate_limit.py` present and wired via `_guarded` | — |
| E43 | Single replica; in-process auth rate limiting | Met | `backend/api/rate_limit.py` is in-process, as stated | — |
| E44 | Only 2 of 4 model-backed decisions covered by agency suite | Met | Scoreboard confirms; `select_experiment` uncovered for the stated reason | — |
| E45 | Narrative check discards prose with unrecorded figures; corpus is a test | **Exceeded** | `narrative.py` — role-aware, far more sophisticated than the bullet suggests | — |
| E46 | Repository map accurate | Met | All seven directories exist as described | — |
| E47 | A user can ask a novel question and get an investigation like the published ones | **Misleading** | Requires flag + `engine: agentic` + `adaptive` tier **+ an OpenAI key**. Without a key, `FixtureAgentPolicy` (docstring: *"for tests"*) yields one placeholder hypothesis. Observed live: rival-explanations goal → `"delivery_days has a describable distribution"` → `declined` | **Critical** |
| E48 | Reasonable ticker coverage | Met | Live SEC fetch for AAPL/MSFT succeeded with real CIKs | — |
| E49 | Production-shaped | Met | Real auth tiers, spend guard, lease-based queue, retention, S3 option, migrations, 6 CI workflows | — |
| E50 | Ten small deterministic components consuming typed policy decisions | Met | Ten components; `AgentPolicy` is the sole LLM seam; all decisions typed | — |

**Correspondence score: 6.0 / 10.** The core system exists and most specific, checkable claims
are true — often exactly true. Meaningful expectations about *reachability* (E47, E20), *what the
diagram depicts* (E26), *what the screenshots show* (E36) and *how adaptive the loop is* (E28)
are overstated or require undocumented knowledge.

---

## 5. User-journey audit

**1. Discover repo.** Name "Agentic Data Science System"; app brands itself "auditable-loop";
`PRODUCT.md` register is "product". Three names for one thing. *Friction: low, but it costs
recall.*

**2. Read README.** Strong opening. The worked example is genuinely gripping — a run that
rejected the question's own premise is the right thing to lead with. *Friction: the reader
finishes believing they can reproduce this locally in one command.*

**3. Clone.** Fine. 604 commits, clean tree, MIT, CI badge, CONTRIBUTING/SECURITY/CODE_OF_CONDUCT.

**4. Configure.** `.env.example` is 8,871 bytes and excellent — it documents the LLM provider,
per-phase model overrides, pricing JSON, budgets, and the agentic flag with a clear comment. The
README asks for three of those variables and does not mention that the rest matter. *Friction:
high, and invisible — nothing tells you you're under-configured.*

**5. Start.** `docker compose config` validates; the three README secrets are exactly the three
hard-required vars. Manual path (`uvicorn` + SQLite) worked first try after `alembic upgrade
head`. *Friction: low.*

**6. Sign in.** `POST /v1/auth/bootstrap` works as documented in `docs/local-stack.md:218` and
grants `adaptive`. The README says "Bootstrap an admin" without linking the four lines that show
how — you have to open the runbook. Also undocumented in the README: `POST /v1/auth/guest`
returns a working token and project in one call, no account. *Friction: medium; a genuinely nice
feature is hidden.*

**7. Ask first question.** Two separate walls.
   - Through the **chat** (what the README tells you to do): I created a chat and hit a red
     `NEXT_REDIRECT` error while the chat was in fact created — a real bug at the first click.
     Then asked the README-equivalent peer-comparison question. It ran, fetched live SEC data,
     produced 19 artifacts and a chart — and answered *"The run completed, but the evidence is too
     limited to support a full narrative answer. What weakens the claim: llm_provider_unavailable."*
   - Through **`/v1/investigations`** (the agentic loop): `409 The agentic investigation engine is
     disabled` — accurate and actionable, but not anticipated by the README.

   *Friction: the highest in the journey. Time from `docker compose up` to a meaningful analysis
   is not five minutes; without an API key it is unbounded, because it never arrives.*

**8. Receive answer.** When it does work, the answer format is good and the system's honesty is
its best feature — it degrades to a stated limitation rather than inventing prose. That is
exactly what the README promises, arriving in a context the README did not prepare you for.

**9. Inspect evidence.** Excellent, once found. `/demos/{slug}/trace` is the payoff. Artifacts
download as real CSV with full statistical provenance per row. The one small gap: a hypothesis's
`mutually_exclusive_with` is not exposed in the read model, so a reader sees the *consequence* of
the rivalry (the critique message) but not the recorded fact.

**10. Reproduce / verify.** Strong. `sync-readme-facts.py --check` passes; OpenAPI regenerates to
zero diff; the replay endpoint returns `identical`; every offline command runs. Caveat: running
the advertised `evaluate` command dirties two *tracked* files under `data/evaluation/`, so a
developer following the README ends with a non-clean `git status`.

---

## 6. Agentic architecture verdict

```
README-implied agentic level: 3.5 / 4
Main product path level:      2   / 4
Maximum implemented level:    3   / 4   (weak 3)
```

**Why the discrepancy.**

The README's loop description — "chooses experiments from what it has learned so far, revises
claims when evidence contradicts them, critiques its strongest claim, refuses to conclude while
two of its own claims disagree, and stops for an explicit typed reason" — reads as Level 3
verging on 4. Four of those five are true. The first is the weak one.

**Main path (Level 2).** `edgar_project/orchestration/planner.py` is explicitly "Deterministic,
rule-based planner (no LLM)". `select_plan_template` maps preferences + coarse intent to one of
four `PlanTemplateId`s. The LLM writes the critique and the report. That is a routed workflow.

**Agentic path (weak Level 3).** Real Level-3 properties are present: the goal interpreter
(LLM) chooses intent, metric and grouping, which changes the candidate tool set; hypothesis
status transitions feed back into termination; a critique can inject a high-priority
falsification candidate at gain 0.95. But the exhaustiveness is the ceiling:

- `expected_information_gain = round(max(0.3, 0.85 - 0.1 * prio), 4)` (`components.py:377`) —
  purely positional, carrying no information about results so far.
- `INTENT_TOOLS` is a static 2–3 tool list per intent (`components.py:58-77`).
- Candidates are keyed `(tool, metric)` and drained once executed.

The consequence is checkable, and I checked it across all six published runs. Each executed
exactly its intent's tool list in the declared order:
`csv-distribution-honesty` → `[summarize_distribution, profile_dataset, detect_outliers]` =
`INTENT_TOOLS[distribution]` verbatim; `edgar-margin-vs-growth` → `EDGAR_INTENT_TOOLS[trend] +
INTENT_TOOLS[trend]`, once per metric group. Parsing the committed model-call captures, the LLM
selector chose index 0 in 14 of 17 calls and 2 or 3 in the other three — so it is genuinely
choosing, but choosing the *order* of a predetermined set. **The set of experiments a run
performs is a function of the goal interpretation, not of anything the run learns.**

Critique-driven falsification is the one place intermediate results change *what* runs — and it
fired in only 3 of 6 published runs (2, 1 and 1 critiques; the flagship EDGAR run has **zero**).

### End-to-end execution trace (real code, flagship run `edgar-margin-vs-growth`)

| Step | Code | Det./LLM | Crosses | Persisted | Hallucination risk |
|---|---|---|---|---|---|
| Prompt | `POST /v1/investigations` → `investigation_create_service.py:198` (flag check) | Det. | HTTP | `AnalysisRun.input_payload_json` | none |
| Engine routing | `select_run_engine` (`agentic_..._service.py:135`) — 3 conditions, fails closed | Det. | — | — | none |
| Dataset resolve | `EDGARAdapter` → `DeterministicEdgarPanelMaterializer` → `DatasetManifest` (49 rows, `sha256:7aeb4e…`) | Det. | SEC HTTP | `DatasetReference` w/ `content_hash`, `row_count` | none |
| Goal interpretation | `GoalInterpreter` → `AgentPolicy.interpret_goal` | **LLM** | model API | `ModelCall` #0 (1,881→62 tok, $0.0017) | intent/metric only — a wrong metric mis-frames the run (README's own Known Limit) |
| Hypotheses | `HypothesisGenerator` (`components.py:169`); metric refs **dropped if not in manifest** (:184) | **LLM** | model API | `ModelCall` #1, 2 `Hypothesis` rows | statements only, no figures |
| Rivalry marking | `poses_alternatives` (`alternatives.py:49`) | **Det.** | — | `mutually_exclusive_with` | none |
| Candidate planning | `InvestigationPlanner.candidates` (:300) — `INTENT_TOOLS` + registry `validate()` | Det. | — | `ExperimentRequest` w/ `reproducibility.id` | none |
| Selection ×7 | `ExperimentSelector.select` (:403) | **LLM** | model API | `ModelCall` #2–8, `AgentDecision(select_experiment)` | index only; out-of-range → `None` (:419) |
| Execution | `ExperimentExecutor` → registry → `src/` via `edgar_project/mcp/adapters.py` | **Det.** | MCP boundary | `ExperimentResultRow` + 10 artifacts | **none — this is the invariant** |
| Evidence | `EvidenceUpdater` — computes strength/reliability/coverage from returned statistics | **Det.** | — | 7 `Evidence`, each with `experiment_result_id` | none |
| Hypothesis update | `HypothesisUpdater` → both `rejected` at 0.05 | **Det.** | — | `AgentDecision(revise_confidence)` ×6 | none |
| Critique | `Critic` — **not invoked here** (0 critiques) | — | — | — | — |
| Termination | `finalize_no_candidates` (:974) → `insufficient_evidence` (candidates exhausted) | **Det.** | — | `termination.reason` | none |
| Conclusion | `ConclusionSynthesizer` → disposition `refuted` from claim statuses | **Det.** | — | `Conclusion` | none |
| Narrative | LLM writes prose (`ModelCall` #9), then **`verify_narrative`** checks every figure by role | LLM + **Det. gate** | model API | `conclusions.narrative` | **closed by the gate**; failure falls back to the deterministic statement |
| API | `GET /v1/investigations/{id}` → `InvestigationDetail` | Det. | HTTP | — | none |
| Frontend | `/demos/{slug}` + `/trace` | Det. | — | — | none |

**Failure behaviour:** a policy exception is counted before the call (`_invoke_policy`,
`components.py:90`) so a raising policy still charges budget; a detached user row falls back to
the cheap engine; an out-of-range selector index returns `None` and the loop terminates via
`finalize_no_candidates`. **Replay:** verified live — deterministic IDs plus per-iteration
checkpoints produced `verdict: identical`.

---

## 7. Strongest aspects of the repository

1. **`narrative.py`'s role-aware numeric verifier.** The industry-standard approach is "check the
   number appears somewhere in the output." This checks the number against the *semantic role the
   prose assigns it*, documents why the naive version failed with the exact false-negative that
   defeated it, and deliberately holds digits stricter than number-words. It is the only reason
   the headline invariant survives contact with LLM-written prose.
2. **Deterministic rivalry detection before scoring.** Moving mutual exclusivity from
   "hope the critic notices at critique time" to "decide from the question's grammar before any
   claim is scored" converts a best-effort check into a guarantee for the common case — and the
   module documents the published run that got through without it.
3. **Two enforced architectural boundaries with AST-parsing tests.** `test_domain_boundary.py`
   and `test_backend_boundaries.py` parse imports and fail on violation, with an explicit
   allowlist for the two EDGAR bridge modules. `CLAUDE.md` records the reason: "the one rule that
   had no test is the one that was broken."
4. **An evaluation suite with a stated admission rule.** Hard cases are admitted *only if they
   defeat the deterministic baseline*. I verified the baseline scores 0/5 on the hard tier and
   14/14 on core. The suite caught a real prompt-contract defect (a null `message` tripping the
   loop's fail-safe) — evaluation that found a bug, not evaluation that decorates a README.
5. **`select_run_engine`'s fail-closed triple gate**, with the failure mode named in a comment.
   Combined with `spend_guard`'s two independent control families (USD ceilings *and* run counts,
   because "an unpriced deployment estimates every call at $0.00, so a cost-only guard would
   silently never fire"), this is money-handling code written by someone who has thought about
   how it gets bypassed.
6. **The static replay tier being schema-identical to the live API.** Verified programmatically:
   the export's key set equals the OpenAPI `InvestigationDetail` schema exactly. The showcase
   cannot drift into a prettier fiction than the product.
7. **Replay-and-diff as a first-class endpoint**, admin-gated with a stated reason (a replay
   spends money the spend guard cannot see, because the candidate is deliberately not persisted).
8. **Model-call auditing down to system-prompt text**, with prompt IDs and versions
   (`agentic.policy @ 1.0.5`) and per-phase cost — and the frontend renders it.
9. **The `AgentObserver` seam.** A cleanly inverted instrumentation dependency that keeps
   `agentic/` genuinely runnable standalone; verified by grep and by boundary test.
10. **Comment discipline throughout.** Comments explain *why*, and repeatedly name the specific
    bug the code exists to prevent ("a goal asking for the weakest entity was answered with the
    strongest one until this was plumbed — not a weaker answer, the opposite one"). This is the
    single clearest signal of engineering maturity in the repository.

---

## 8. Weakest aspects

### Product / repository problems

**Critical**

- **The advertised experience is unreachable without an OpenAI API key, and the fallback is a
  test fixture.** `FixtureAgentPolicy`'s own docstring reads "Deterministic fixture policy for
  tests." It emits exactly one hypothesis, ever (`fixture_policy.py:72-100`), so the two-rival-
  claims behaviour the entire showcase is built on is structurally impossible without a model.
  Observed live: the rival-explanations goal yielded `"delivery_days has a describable
  distribution"` → `declined`. `.env.example:139-140`'s "the loop still runs deterministically
  (fixture policy)" is technically true and practically misleading.

**High**

- **`NEXT_REDIRECT` rendered as a user-facing error** — `frontend/src/actions/projects.ts:45`
  calls `redirect()` inside a `try` whose `catch` returns `{ error: e.message }`. Next's
  `redirect()` signals via a thrown control-flow exception and must not be caught. The chat is
  created but the user sees a red error and no navigation. **This is the first click of the
  advertised local journey.** (`deleteChatAction` in the same file returns `redirect()` from
  inside `catch`, which is also worth a look.)
- **Two overlapping analysis architectures with no map.** `edgar_project/orchestration/` (3,890
  LOC, 4 templates) and `agentic/` (5,916 LOC) both answer analytical goals. Nothing in the
  README explains which is which. `docs/architecture/current-system.md:178` already flags
  top-level `orchestration/agent.py` as "Deprecate / consolidate", and it is still present.
- **The loop is less adaptive than its own vocabulary.** See §6. Naming a positional constant
  `expected_information_gain` is the specific thing audit rule 5 warns about.

**Medium**

- **`suite_agency_v1` vs `suite_agency_v2`.** The README cites the frozen v1 in the row carrying
  the project's headline benchmark; the shipped and documented suite is v2.
- **Three access tiers, one gate documented.** `guest`/`standard`/`adaptive` and the triple
  condition in `select_run_engine` are explained in `PRODUCT.md` and code, not the README.
- **Advertised commands dirty tracked files.** `edgar_project.cli evaluate` rewrites
  `data/evaluation/suite_fixtures_v1_{results,summary}.json`, both tracked.

**Low**

- 8 ESLint warnings (`react-hooks/set-state-in-effect`), non-blocking.
- `mutually_exclusive_with` is not exposed in the investigation read model.
- Light/dark theme inconsistency between `/login` and the chat/demo surfaces.
- Three product names in circulation: "Agentic Data Science System", "auditable-loop", "EDGAR Analysis".

### Documentation / README problems

**Critical**

- **No statement that an OpenAI API key is required.** The one section that addresses the
  question — "No API key? The deterministic core runs offline" — points at three CLI commands and
  leaves the reader believing the gap is small. It is total.

**High**

- **The architecture diagram omits the default execution path**, and therefore does not describe
  the system a `docker compose up` user actually gets.
- **The three product screenshots are four months stale**, wrongly branded, in the wrong theme,
  show the *deterministic* product, and one contains a visible dev-error badge.
- **The strongest artifact in the repository is not shown.** `/demos/{slug}/trace` gets one
  hyperlink ("Browse any of them at `/demos`") and no image.
- **"Bootstrap an admin, then ask a question in the chat"** describes a journey that, followed
  literally, ends in a degraded answer — with no warning.

**Medium**

- Reachability is under-specified: three gates, one disclosed.
- The `refuted` framing ("has settled the matter") is stronger than the run's own record, which
  terminated `insufficient_evidence` via candidate exhaustion and whose narrative says
  "It stopped because of insufficient evidence, not because the question was fully settled."
- The landing page, guest tier and structured-answer format are undocumented.
- `docs/local-stack.md` is 237 lines of good runbook the README compresses to one sentence.

**Low**

- 1,438 vs 1,454 backend tests, in a file whose generator docstring is about numeric drift.
- No one-line elevator pitch above the fold — the opening is two abstract sentences.

---

## 9. README scorecard

| Dimension | Score /10 | Reason |
|---|---|---|
| Positioning | 6 | Excellent on *what makes it interesting* ("auditable adaptive reasoning is the part that took the work"; "EDGAR is an adapter, not the architecture" is clear and true). Fails on *what you get*: never distinguishes the default deterministic product from the opt-in agentic loop, never says who it is for, and gives no one-sentence proposition above the fold. |
| Conceptual clarity | 7 | Genuinely explains the LLM/deterministic split, evidence, typed termination and MCP's purpose — well above the "list of technologies" failure mode. Loses points because "chooses experiments from what it has learned so far" is not what the code does, and MCP's two servers are explained by role but not by *why a hosted MCP server needs the no-back-door property* (the one sentence that does it is easy to miss). |
| Demonstration | 7 | Very strong on *outcomes*: six real runs, CI-checked figures, honest synthetic/live labels, and a lead example whose result is genuinely counterintuitive. Weak on *proof of process*: no plan, no tool call, no evidence record, no artifact row, no execution trace inline. The images prove least where proof matters most. |
| Getting started | 3 | The three-line quickstart is accurate and insufficient. Missing prerequisite (API key) is total, not partial. Bootstrap is named but not shown. The advertised journey terminates in a degraded answer. Two of the four offline commands leave the working tree dirty. |
| Feature honesty | 7 | The Known Limits section is better than most projects manage and is why this is not a 4 — it volunteers real failures, including one that shipped. But it discloses one of three gates, buries the adaptivity limit as an evaluation caveat, and omits the API-key dependency entirely. |
| Information architecture | 6 | Good instincts: worked example first, table for figures, limits before repo map. Undermined by density — long paragraphs of continuous argument where a technical visitor scans — and by burying the most load-bearing facts (offline reality, default path) inside prose rather than surfacing them. |
| Technical credibility | 7 | "Deterministic", "reproducible" and "traceable" are earned and, unusually, *defined by demonstration*. "Agentic" is used at a level above what the code does. The landing page's "production-grade" sits awkwardly beside Known Limits' "no backup/restore, single replica" — the README is honest, the product page is not. |
| Portfolio effectiveness | 5 | The heaviest cost. `narrative.py`, the trace UI, the agency suite's admission rule, the boundary tests, the fail-closed engine gate and the spend guard are the work that would impress a reviewer, and a reviewer must reverse-engineer the repository to find any of them. The README instead spends its best real estate on stale screenshots of the weaker product. |

**Overall: 6.0 / 10** (mean 6.0; unweighted).

---

## 10. Claims that should be rewritten

| # | Claim (quoted or identified) | Classification | Suggested replacement |
|---|---|---|---|
| 1 | "**No API key? The deterministic core runs offline**" + three commands | **Misleading by omission** | "**An OpenAI API key is required for every investigation on this page.** Without one the loop falls back to a rule-based test policy that proposes a single placeholder hypothesis — it will not reproduce the behaviour shown above. What *does* run offline with no key: the fixture benchmark suite, the EDGAR numerical pipeline, and the full agency benchmark against the deterministic baseline (`--tier hard` → 0/5, which is the point of the tier)." |
| 2 | "Bootstrap an admin, **then ask a question in the chat**." | **Ambiguous / misleading** | "Bootstrap an admin (`docs/local-stack.md#bootstrap`). The **chat** runs the deterministic EDGAR chain — rule-based planning over four analysis templates, with the LLM writing the critique and report. To run the **adaptive loop** shown above you additionally need `EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true` on api *and* worker, an `adaptive`-tier account (bootstrap grants this), an OpenAI key, and `POST /v1/investigations`." |
| 3 | "chooses experiments **from what it has learned so far**" | **Overstated** | "chooses which experiment to run next from the candidates its goal interpretation admits — the tool *set* follows from the interpreted intent and the claims under test; intermediate results reorder that set and can add a falsification experiment when the critic names one, but do not currently expand it. See [Known limits](#known-limits)." |
| 4 | The Mermaid diagram | **Obsolete / incomplete** | Add the default path as a peer branch: `API → Plan template router (edgar_project/orchestration) → EDGAR MCP tools → src/`, with the agentic loop drawn as the flag-gated alternative it is. Label which branch is default. |
| 5 | "[`suite_agency_v1`](docs/agent/agency-evaluation.md) scores reasoning quality" | **Obsolete** | "[`suite_agency_v2`](docs/agent/agency-evaluation.md) — 13 core + 5 hard cases, 9 properties. `suite_agency_v1` is the frozen 13-case core the published measurement used." |
| 6 | "**The agentic engine is off by default**" | **Accurate but incomplete** | "The agentic engine needs three independent conditions: the flag, a per-run `engine: agentic` opt-in, and an `adaptive`-tier account. Any one missing falls back to the deterministic chain — deliberately, because the loop costs real money per question (`select_run_engine`)." |
| 7 | The three "Product surfaces" screenshots | **Obsolete** | Reshoot from the current build; add the `/demos/{slug}/trace` page as the *first* image. Remove `run-trace.png` (stale brand, wrong theme, visible dev-error badge) or replace it with the agentic trace. |
| 8 | "A run that disproved its own hypotheses **has settled the matter**" | **Overstated** | "…rejected both claims outright. The run still reports `insufficient_evidence` as its stop reason, because it exhausted its candidate experiments rather than reaching a positive finding — `refuted` describes the disposition, `insufficient_evidence` describes why it stopped, and the trace shows both." |
| 9 | "**Reproducible** — a resumed run reaches the same state as an uninterrupted one" | **Accurate but undersold** | Add the runnable proof: "`POST /v1/investigations/{id}/replay` re-runs it and diffs — `identical`, `same_conclusion`, or `diverged`, with per-hypothesis deltas and tool-order comparison." |
| 10 | "The narrative check trades readability for safety" (Known Limits) | **Accurate but badly undersold** | Promote out of Known Limits into the main argument: "The model writes the answer; it may not state a figure. Every number in generated prose is checked against the run's recorded values **in the role the sentence puts it in** — `7` passes as an experiment count in a clause about experiments and is refused beside `% revenue`. One bad figure discards the whole narrative and falls back to the deterministic statement." |
| 11 | "1,438 backend tests · 236 frontend tests" | **Obsolete (minor)** | 1,454. Either extend `--check` to cover the counts or drop them. |
| 12 | Landing page: "A **production-grade** agentic loop" | **Overstated** (product, not README) | "A production-*shaped* agentic loop — budgets, spend ceilings, migrations, tiered auth, OTel. Not production-*operated*: single replica, no backup/restore ([why](#known-limits))." |

---

## 11. Missing things the README should show

Prioritised.

1. **P0 — A requirements box, above the fold.** Runtime prerequisites (Docker/Python 3.12/Node
   22), and unambiguously: *an OpenAI API key is required to run an investigation; here is
   exactly what works without one*. This is the single highest-value addition.
2. **P0 — The platform/application distinction, in two sentences.** "`agentic/` is the reusable
   loop; `edgar_project/` + `src/` are the EDGAR application; the chat runs the deterministic
   EDGAR chain; the adaptive loop is opt-in." Currently only in `PRODUCT.md`.
3. **P0 — One complete worked example inline.** Goal → interpreted intent JSON → two hypotheses →
   candidate list with gains → selected experiment → the tool envelope → three evidence rows with
   strength/reliability/coverage → conclusion → the outcome. All of it already exists in
   `edgar-margin-vs-growth.capture.json`; none of it is on the page. This is what converts
   "traceable" from an adjective into a demonstrated property.
4. **P1 — A screenshot of `/demos/{slug}/trace`.** The best asset in the repository, currently
   invisible. It should be the first image.
5. **P1 — An honest agency statement.** A short "how adaptive is it, exactly" paragraph:
   goal interpretation selects the tool set; intermediate results reorder it and can add a
   falsification experiment; the set does not currently expand. Stating this *raises* credibility
   — a reviewer who discovers it themselves discounts everything else.
6. **P1 — Supported question types and coverage.** Nine analysis intents, thirteen-ish tools, four
   EDGAR templates, what a goal must look like to be understood. Nothing on the page tells a
   reader what they can ask.
7. **P1 — Evaluation methodology in three lines.** The admission rule ("a hard case is admitted
   only if it defeats the deterministic baseline") is the most persuasive sentence in
   `docs/agent/`. It belongs in the README.
8. **P2 — An accurate architecture diagram** with both execution paths and the default marked.
9. **P2 — Why MCP exists**, in one sentence: everything goes through `/v1`, so the MCP server
   inherits auth and owner scoping and can be hosted without a privileged back door.
10. **P2 — The guest tier.** `POST /v1/auth/guest` gives a working token and project in one call.
    Free demo value, currently undocumented.
11. **P3 — A status/maturity table.** implemented / experimental / fixture-only / offline / live,
    per component. Known Limits is prose doing a table's job.
12. **P3 — Time-to-first-answer**, honestly stated for each path.

---

## 12. Proposed README architecture

Optimised for a technical visitor whose first 60 seconds decide everything.

| § | Section | Purpose | Should communicate | Evidence / example |
|---|---|---|---|---|
| 1 | **One-line proposition + badges** | Answer "what is this" before scrolling | One sentence naming the artifact and the differentiator: *"An adaptive investigation loop over tabular data where every number in the answer traces to the deterministic computation that produced it — and none of them came from the model."* | CI, Python, License |
| 2 | **The 30-second proof** | Make the differentiator visible, not asserted | A single annotated trace excerpt: goal → 2 rival claims → 7 experiments → both rejected → `refuted`, with a caption that a model wrote none of the figures | Screenshot of `/demos/edgar-margin-vs-growth/trace` + 8 lines of the real decision log |
| 3 | **What you can run right now** | Remove every ambiguity about reachability | Three rows: **Replay** (`/demos`, no account, no key, no backend) · **Deterministic chain** (guest tier, one click, key needed for narrative) · **Adaptive loop** (flag + `adaptive` tier + **OpenAI key**) | Exact commands per row |
| 4 | **Requirements** | Kill the onboarding failure | Docker / Python 3.12 / Node 22; the three secrets; **the API key and what it gates**; what genuinely runs offline | The four offline commands with expected output |
| 5 | **How it works** | The conceptual core | Two execution paths, which is default; the ten components; the LLM/deterministic boundary; where hallucinated numbers *could* enter and what stops them | Corrected diagram + the `narrative.py` role-check example |
| 6 | **How adaptive it actually is** | Pre-empt the reviewer's own audit | The honest Level-3 statement from §5 above | The published runs' tool sequences — the same evidence I used |
| 7 | **One worked example, end to end** | Convert adjectives into artifacts | Interpretation JSON → hypotheses → candidates+gains → selection → envelope → evidence rows → conclusion → outcome | Verbatim from `edgar-margin-vs-growth.capture.json` |
| 8 | **Every published run, as recorded** | Breadth + honest labelling | Keep as-is (generated block); it works | Existing table |
| 9 | **How it's measured** | Evaluation credibility | The admission rule; core vs hard; baseline 0% / model 60%; the two failures named | Scoreboard link + the `unanswerable_premise` failure |
| 10 | **Integration** | Reusability | Two MCP servers with tool lists; the "no back door" sentence; OpenAPI in CI | Live `tools/list` output |
| 11 | **Operations** | Production-shaped, not production-operated | Budgets, spend guard, replay/diff, observability | Dashboard screenshot (keep the honest caption) |
| 12 | **Known limits** | The trust anchor | Keep, plus: the API-key dependency, all three engine gates, and the adaptivity ceiling | Existing bullets |
| 13 | **Repository map · Docs · License** | Navigation | Keep | — |

Rationale for the reordering: sections 3 and 4 are currently absent and are the cause of every
onboarding failure I hit. Section 6 costs one paragraph and buys back the credibility that an
adversarial reviewer would otherwise take. Section 2 replaces three stale screenshots with the
one image that proves the thesis.

---

## 13. Top 10 recommended changes

| # | Change | Impact | Effort | Target | Status |
|---|---|---|---|---|---|
| 1 | **State the OpenAI API key requirement explicitly**, and describe what the no-key fallback actually produces | High | Low | README | ✅ Done |
| 2 | **Fix the `NEXT_REDIRECT` bug** — move `redirect()` out of the `try` in `frontend/src/actions/projects.ts:45` (and review `deleteChatAction`) | High | Low | Product | ✅ Done |
| 3 | **Add the "what you can run right now" tier table** (replay / deterministic / adaptive) with exact commands | High | Low | README | ✅ Done |
| 4 | **Replace the three stale screenshots with `/demos/{slug}/trace`** from the current build | High | Low | README | ✅ Done |
| 5 | **Rewrite the quickstart to be honest about the chat path**, and name all three engine gates | High | Low | README | ✅ Done |
| 6 | **Add the inline worked example** (§11.3) — the data already exists in the committed capture | High | Medium | README | ✅ Done |
| 7 | **Add the honest agency paragraph** (§11.5) — pre-empt the reviewer's own finding | High | Low | README | ✅ Done |
| 8 | **Correct the architecture diagram** to show both paths and mark the default | Medium | Low | README | ✅ Done |
| 9 | **Fix `suite_agency_v1` → `v2`**, and either extend `sync-readme-facts.py --check` to cover the test counts or drop them | Medium | Low | Both | ✅ Done |
| 10 | **Promote `narrative.py` out of Known Limits into the main argument**, and stop `edgar_project.cli evaluate` writing tracked files | Medium | Low | Both | ⚠️ Partial |

### Follow-up status — branch `docs/audit-followups`

| Commit | Covers |
|---|---|
| `fix(chat): stop reporting a created chat as a NEXT_REDIRECT failure` | #2. `redirect()` moved out of the `try`; verified in the browser (form now navigates into the new chat). Three regression tests added, with the `redirect` mock made to throw the way the real one does — the reason the existing tests could not catch it. `deleteChatAction` reviewed: its `redirect()` calls sit in the `catch` handler, not the `try`, so they propagate correctly. |
| `fix(readme-facts): check the backend test count…` | #9 (tooling half). `--check` now fails on backend-count drift; confirmed it fires on the stale 1,438 before regenerating to 1,454. Frontend count stays refresh-on-demand — that CI job has no Node. |
| `chore(data): stop tracking benchmark output…` | #10 (code half), **partially**. `.gitignore` now covers `data/evaluation/*_results.json`, `*_summary.json` and `suite_*/`, keeping `agency/scoreboard-*.json`. |
| `docs(readme): say what a reader can actually run…` | #1, #3, #4, #5, #6, #7, #8, #9 (doc half), #10 (doc half). |

**Outstanding — needs one command from a human.** Ignoring paths does not untrack files that are
already committed, and the bulk `git rm --cached` was blocked by the tool sandbox. From the repo
root:

```bash
git ls-files data/evaluation/ | grep -v '^data/evaluation/agency/' | xargs git rm --cached
```

That untracks 47 files (keeping the three published scoreboards) and leaves them on disk. Until
it runs, `edgar_project.cli evaluate` still dirties the working tree.

**Also verified after the changes:** `ruff` clean · 1,444 backend tests passing ·
239 frontend tests passing · `npm run build` green · `sync-readme-facts.py --check` OK ·
`export-openapi.py --check` OK · the new Mermaid diagram renders (checked against mermaid 11).

**Not addressed** (out of scope for a documentation pass, listed in §8): the two overlapping
analysis architectures and the still-present `orchestration/agent.py` shim that
`docs/architecture/current-system.md` already flags for consolidation; the 8 ESLint warnings;
`mutually_exclusive_with` missing from the investigation read model; and the three product names
in circulation.

Nine of ten are documentation or one-line fixes. **Not one requires new product capability** —
which is the finding, stated as a work plan: the engineering is ahead of its own description, and
the highest-leverage work available is telling the truth about what already exists, in both
directions.

---

## Final question

> **If an experienced data scientist / AI engineer spent two minutes on this GitHub repository,
> would they correctly understand how sophisticated the project actually is?**

**No — and they would get it wrong in both directions at once.**

In two minutes they read a confident claim of adaptive agency, see three stale screenshots of a
different and weaker product branded with a different name, and form a reasonable impression:
*competent LLM-orchestration project, probably over-claiming on "agentic", as they all do.* They
would be right about the over-claim and badly wrong about everything else. They would not learn
that a role-aware numeric verifier stands between the model and every figure in the prose; that
two architectural boundaries are enforced by AST-parsing tests; that the evaluation suite admits
a hard case only if it defeats the deterministic baseline; that a replay endpoint re-runs a
persisted investigation and diffs it conclusion-first; or that the static showcase is
schema-identical to the live API so it cannot drift into fiction. They would also not learn that
nothing on the page is reachable without an API key.

The most credible reading of this repository is that its README was written by someone arguing
*for* the work, when the work's own strongest quality — the thing every good comment in the
codebase demonstrates — is arguing *against* it and reporting what survives.

**The single highest-impact change:** replace the three stale product screenshots with one image
of `/demos/{slug}/trace`, captioned with what it proves — *conclusion → claim → evidence →
experiment → artifact → rows, and every model call with its prompt, response, tokens and cost,
none of which produced a number on this page.*

That image is already in the repository, already rendered by shipped components, already backed
by committed data, and already passing tests. It proves in one glance what 200 lines of prose are
currently asking the reader to take on trust — and it shows the reviewer the *best* system in the
repository instead of the second-best one.

---

### Appendix — commands executed

| Command | Result |
|---|---|
| `python -m pytest tests/ -q` | **1,444 passed, 10 skipped**, 93.74s (1,454 collected) |
| `python -m ruff check .` | All checks passed |
| `npm --prefix frontend test` | **236 passed** (39 files) |
| `npm --prefix frontend run lint` | 0 errors, 8 warnings |
| `npm --prefix frontend run build` | Success, 23 routes |
| `python3 scripts/sync-readme-facts.py --check` | OK: matches committed export |
| `python3 scripts/export-openapi.py` | Zero diff against committed |
| `PYTHONPATH=. python3 -m edgar_project.cli demo --fixtures` | 5/5 passed, offline |
| `PYTHONPATH=. python3 -m edgar_project.cli evaluate` | 5/5 passed (dirties 2 tracked files) |
| `PYTHONPATH=. python3 -m agentic.evaluation` | `suite_agency_v2` 14/14 core (100%) |
| `PYTHONPATH=. python3 -m agentic.evaluation --tier hard` | **0/5** — baseline headroom confirmed |
| `pytest` on the 6 README-cited test files | 30 passed |
| `pytest -k "replay or resume or checkpoint or diff"` | 82 passed, 1 skipped |
| `docker compose -f docker-compose.yml config` | Exit 0; 3 required vars = 3 README-named vars |
| `alembic upgrade head` (SQLite) | Full chain applied |
| `POST /v1/auth/bootstrap` → `/login` → `/projects` | Worked; tier `adaptive` |
| `POST /v1/investigations` (README-literal config) | **409 engine disabled** |
| `POST /v1/investigations` (flag on, no LLM) | 201, `exhausted` — 1 placeholder hypothesis, `declined` |
| `POST /v1/investigations/{id}/replay` | 200, `verdict: identical` |
| `POST /v1/auth/guest` | 201 with token + project |
| `GET /v1/runs/{id}/llm-usage` | 200, `call_count: 0` on the deterministic run |
| `GET /v1/artifacts/{id}/content` | Real CSV, live SEC CIKs 320193 / 789019 |
| MCP stdio `tools/list` — `edgar_project.mcp server` | 7 tools |
| MCP stdio `tools/list` + `resources/templates/list` — `backend.mcp` | 9 tools, 2 resource templates |
| Browser: `/demos`, `/demos/{slug}`, `/demos/{slug}/trace` (no backend) | All functional |
| Browser: `/login` → chat → README-equivalent question | `NEXT_REDIRECT` bug; degraded answer (`llm_provider_unavailable`) |

**No live model calls were made. No repository file was modified; the tree was verified clean at
the end of the audit.**
