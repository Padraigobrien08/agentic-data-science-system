# Agentic Data Science System

![CI](https://github.com/Padraigobrien08/agentic-data-science-system/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

An agent that investigates a dataset adaptively, and can show you every step of its reasoning
back to the number it came from.

Two halves. Adaptive reasoning is common; **auditable** adaptive reasoning is the part that took
the work. SEC EDGAR is the flagship dataset, but EDGAR is an adapter, not the architecture.

---

## One investigation, followed all the way down

This is a real run against live SEC filings for AAPL, MSFT and NVDA.

> **Goal:** Has margin quality deteriorated at these companies over recent periods, or is
> revenue growth the explanation?

The loop raised both explanations as separate, falsifiable claims and measured each on its own
metric. Its own evidence went against both:

| Hypothesis | Outcome | Confidence |
|---|---|---|
| Net margin has deteriorated over recent periods | **rejected** | 0.05 |
| Revenue growth is the explanation for the observed deterioration | **rejected** | 0.05 |

**It rejected the premise the question assumed, and then the explanation offered for it.**
Asked to choose between two accounts of a decline, it found the decline itself unsupported —
so neither account had anything to explain. Seven experiments, seven evidence records, and the
answer is that the question was built on something that is not there.

That outcome is reported as `refuted`, not as "inconclusive". A run that disproved its own
hypotheses has settled the matter; describing that as a failure to conclude gets the strongest
thing an investigation can do exactly backwards.

### It catches itself holding two claims that cannot both be true

A second SEC run asks whether NVDA's margin advantage is durable profitability **or** faster
revenue growth. Both reached `supported` independently — each scored honestly against its own
evidence, because nothing in the loop compares claims to each other. So the goal's own phrasing
does: a question shaped "is it X, or is it Y?" marks its two claims mutually exclusive before
either is scored, and when both stood the loop recorded the conflict itself:

> The goal asked which of these holds, and both are currently supported […] They cannot both
> be the explanation.

Deterministic code then weakened **both** — the conflict establishes that one of them is wrong,
not which — and the run reports `contradicted` at 0.5 rather than a confident answer at 0.95.
This used to depend on a model noticing the clash at critique time, and
[a published run got through without it](tests/agentic/test_mutual_exclusivity.py): both
branches of an either/or affirmed at 0.95, rendered as the most confident card in the showcase.

Each claim traces down without a gap: conclusion → evidence → the experiment that produced it →
its typed tool envelope → the artifact → the rows. That chain is
[asserted by tests](tests/agentic/test_evidence_provenance_link.py) over a real run and
[again over the read model](tests/test_investigation_evidence_link_readmodel.py), because it is
the product's central claim and it was once quietly false in the published data. The model calls
are audited on the same footing — prompt, response, tokens, cost and latency per phase, at
`GET /v1/runs/{id}/llm-usage`.

> **The LLM plans and interprets. Deterministic code computes.**
> No number in that trace was produced by a language model.

### The same loop, on data that has nothing to do with finance

Four of the runs below analyse an operational delivery dataset — regions, months, delivery
times, order volume. Same loop, same evidence model, same trace surfaces.

That dataset is **generated**, deliberately and with a genuine confound (service times degrade
while volume climbs over the same window). The table says so in the `Data` column rather than
leaving you to guess, and the two EDGAR runs are marked `live` because they are real filings.
A showcase about reporting what you can and cannot support does not get to be vague about its
own inputs.

One of those four is worth its own line. Asked **"which region has the strongest customer
loyalty?"** over a dataset that measures delivery days, order volume, on-time rate and staff
count, the loop stops before running anything:

> This dataset cannot answer the question as asked: the data holds no measure of customer
> loyalty.

Zero experiments, zero claims, `unanswerable_premise`. That is a different answer from "the
evidence was inconclusive", and the distinction is the useful part: one says run more analysis,
the other says bring different data. It used to rank regions by *average delivery days* under a
claim about loyalty and then hedge — the right outcome for the wrong reason, and only because
that proxy happened to be weak.

A run that stops at "I cannot separate these", or at "this is not in here", is a *correct*
outcome. Nearly every AI product on the market will confidently answer a question it cannot
answer.

### Every published run, as recorded

Generated from the committed export by [`scripts/sync-readme-facts.py`](scripts/sync-readme-facts.py)
and checked in CI, because the figures in this file used to be typed by hand and had drifted
from the runs they described.

<!-- BEGIN GENERATED: published-runs -->

| Run | Outcome | Stopped because | Experiments | Evidence | Artifacts | Model calls | Cost | Data |
|---|---|---|---|---|---|---|---|---|
| [`csv-delivery-delays`](frontend/src/lib/demo-static/csv-delivery-delays.json) | **mixed** — one claim stood, one did not | `sufficient_evidence` | 3 | 9 | 5 | 9 | $0.0122 | synthetic |
| [`csv-staffing-vs-service`](frontend/src/lib/demo-static/csv-staffing-vs-service.json) | **contradicted** — two claims could not both be true | `insufficient_evidence` | 1 | 12 | 2 | 4 | $0.0061 | synthetic |
| [`csv-distribution-honesty`](frontend/src/lib/demo-static/csv-distribution-honesty.json) | **declined** — no claim survived the evidence | `insufficient_evidence` | 3 | 6 | 6 | 6 | $0.0078 | synthetic |
| [`edgar-peer-separation`](frontend/src/lib/demo-static/edgar-peer-separation.json) | **contradicted** — two claims could not both be true | `insufficient_evidence` | 3 | 73 | 6 | 8 | $0.0111 | live |
| [`csv-unanswerable-moat`](frontend/src/lib/demo-static/csv-unanswerable-moat.json) | **unanswerable** — the data cannot answer this | `unanswerable_premise` | 0 | 0 | 0 | 2 | $0.0035 | synthetic |
| [`edgar-margin-vs-growth`](frontend/src/lib/demo-static/edgar-margin-vs-growth.json) | **refuted** — the run disproved its own claims | `insufficient_evidence` | 7 | 7 | 10 | 10 | $0.0112 | live |

6 runs, $0.0519 of model spend, 107 of 107 evidence records linked to the experiment that produced them.
1,438 backend tests · 236 frontend tests.

<!-- END GENERATED: published-runs -->

Browse any of them at `/demos`, or read the raw export directly — it is
[the same bytes the API serves](docs/decisions/2026-08-14-static-replay-showcase.md).

---

## Try it

**Hosted showcase:** _URL pending first deploy._ Every run above is browsable at
`/demos` — the real persisted runs, rendered by the same components an authenticated user
sees, served from a committed export with **no backend**. Live runs, guest sessions and the
`/v1` + MCP endpoints need the full stack; see [docs/deploy.md](docs/deploy.md) for both
topologies.

Locally, the whole stack is one command:

```bash
cp .env.example .env   # set JWT_SECRET, OPS_API_TOKEN, BOOTSTRAP_ADMIN_TOKEN
docker compose up --build
```

Web on [:3000](http://127.0.0.1:3000), API health on
[:8000/v1/health](http://127.0.0.1:8000/v1/health). Bootstrap an admin, then ask a question in
the chat. Full runbook: [docs/local-stack.md](docs/local-stack.md).

**No API key? The deterministic core runs offline:**

```bash
PYTHONPATH=. python3 -m edgar_project.cli demo --fixtures   # numerical pipeline on fixtures
PYTHONPATH=. python3 -m edgar_project.cli evaluate          # offline regression suite
PYTHONPATH=. python3 -m agentic.evaluation                  # agency benchmark
```

`evaluate` defaults to the **offline fixture suite**, which is why it is the normal
**developer fallback** and regression path — it touches no network and is safe to run in a
loop. Pin one explicitly with `--suite-id suite_fixtures_v1`.

Validation against **live SEC data stays operator-only** and requires an explicit opt-in, so
no default command and no CI job can reach the network by accident:

```bash
PYTHONPATH=. python3 -m edgar_project.cli evaluate --suite-id suite_smoke --allow-live
```

To reproduce a recorded investigation yourself, see
[`scripts/record_demo.py`](scripts/record_demo.py) — it publishes to the replay tier that serves
the runs above.

---

## How it works

```mermaid
flowchart LR
    U["User in chat UI"] --> W["Next.js web app"]
    AG["External agent"] --> PMCP["Platform MCP server"]
    W --> API["FastAPI /v1"]
    PMCP --> API
    API --> WORK["Background worker"]
    API --> LOOP["Investigation loop"]
    WORK --> LOOP
    LOOP --> REG["Deterministic experiment registry"]
    REG --> PIPE["EDGAR pipeline (src/)"]
    LOOP --> OBS["Traces · metrics · logs"]
    PIPE --> ART["Artifacts"]
    ART --> API
    API --> DB["Postgres: runs, investigations, evidence"]
    DB --> API
    API --> W
```

The loop ([`agentic/`](agentic/)) interprets a goal, proposes hypotheses, chooses experiments
from what it has learned so far, revises claims when evidence contradicts them, critiques its
strongest claim, refuses to conclude while two of its own claims disagree, and stops for an
explicit typed reason. Ten components, each small and deterministic, consuming typed policy
decisions.

| | |
|---|---|
| **Bounded** | Budgets on experiments, iterations, wall time and estimated spend, with deterministic safety caps above them. A public deployment adds per-account and global monthly ceilings ([`spend_guard.py`](backend/services/spend_guard.py)). |
| **Reproducible** | Deterministic IDs and per-iteration checkpoints; a resumed run reaches the same state as an uninterrupted one. |
| **Comparable** | [Replay](docs/agent/replay-and-diff.md) a persisted investigation under a different model, prompt or budget and diff it — did the *answer* change, or only the route to it? |
| **Measured** | [`suite_agency_v1`](docs/agent/agency-evaluation.md) scores reasoning quality: does it conclude when evidence supports it, revise when contradicted, decline when it cannot? On the hard tier the deterministic baseline scores 0% and `gpt-5.4-mini` 60%, stable across five trials — [scoreboard](docs/agent/agency-scoreboard.md). |
| **Self-checking** | Each hypothesis is scored against its own evidence, so a claim and its negation can both reach `supported` — one recorded run did exactly that, at 0.95 each. The critic is the only component that sees the supported set together, so it reports the conflict; deterministic code weakens both sides rather than picking one, and the run reports `insufficient_evidence` unless a further experiment settles it. A published demo shows this happening: [`csv-staffing-vs-service`](frontend/src/lib/demo-static/csv-staffing-vs-service.json). |
| **Observable** | Every decision emits an OTel span (`agent.investigation → agent.iteration.N → agent.component.{name}`), a structured log, and Prometheus metrics. → [docs](docs/observability.md) |

`agentic/` depends on nothing in `backend/`. It imports no structlog, no OpenTelemetry, no
Prometheus — instrumentation goes through an [observer seam](agentic/agent/observer.py), and
`agentic/domain` has no SQLAlchemy. The package runs offline, standalone, and is the reason the
same loop works over EDGAR panels and CSV uploads without special-casing either.

### Observability

![Agent loop dashboard](docs/screenshots/agent-loop-dashboard.png)

A **seeded local run** — 210 investigations over 30 minutes, $0.80 of tracked spend — not
production traffic. Reproduce it with
[`scripts/seed-agent-activity.py`](scripts/seed-agent-activity.py).

The panels answer whether the loop is *working*: median iterations 1.4 (it iterates rather than
one-shotting), seven distinct tools with the mix shifting by goal (it adapts), and hypothesis
transitions including `→ rejected` (its own evidence overturns its claims). `Component errors`
reads "No data" because nothing failed across those 210 runs — left as-is rather than
manufactured.

The Grafana/Prometheus/Jaeger stack is **local-only**
(`docker-compose.observability.yml`); the hosted demo does not run it.

### Product surfaces

| Narrative answer | Inline chart evidence | Deep-dive trace |
|---|---|---|
| ![Narrative answer](docs/screenshots/chat-answer.png) | ![Inline chart](docs/screenshots/chat-chart.png) | ![Run trace](docs/screenshots/run-trace.png) |

### Integration

Everything goes through `/v1` — there is no privileged back door, which is why the MCP server
can be hosted safely.

- **HTTP API** — committed OpenAPI contract at [`docs/api/openapi.json`](docs/api/openapi.json),
  enforced in CI → [contract docs](docs/api/README.md)
- **Platform MCP server** — commission investigations and read hypotheses, evidence and
  artifacts as MCP tools, with conclusions and artifacts also exposed as MCP *resources*;
  stdio or hosted streamable-HTTP with per-caller bearer auth
  → [docs](docs/mcp-platform-server.md)
- **EDGAR MCP server** — the deterministic computation tools
  → [`edgar_project/mcp/`](edgar_project/mcp/)
- **Extending it** — add an input adapter, experiment tool, or decision policy
  → [guide](docs/extending.md)

---

## Known limits

Stated plainly, because a system that reports uncertainty honestly should do the same about
itself.

- **Declining an unanswerable question is still a model judgement.** `answerable: false` is
  reported by the goal interpreter, and everything after it is deterministic — the loop stops,
  claims nothing, runs nothing. But a premise the model does not notice is broken is not
  caught, and the failure is quiet: the loop measures a proxy and reports it honestly, which
  looks identical to an answer. Both directions cost something. Over-declining a question the
  data *can* address is equally bad, and it happened during development — an EDGAR panel has
  no `dimension` columns, so a goal comparing three tickers looked unanswerable until the
  interpreter was shown the entity column it had never been given.
- **Two of the loop's four model-backed decisions are covered by the agency suite.** A fair case
  for `select_experiment` is not constructible, because `expected_information_gain` is fixed by
  the planner's tool ordering —
  [documented here](docs/agent/agency-evaluation.md#what-the-tier-does-not-cover).
- **Mutual exclusivity is detected from the goal's phrasing, not from meaning.** A question
  shaped "is it X, or is it Y?" marks its claims as rivals deterministically, before either is
  scored — so the common case no longer depends on a model noticing. Two claims that are
  genuinely incompatible but *not* posed as alternatives still fall to the critic, which is
  best-effort: it catches the obvious cases, not all of them. The detector is deliberately
  conservative, because inventing a conflict would suppress a legitimate "both are true".
- **The narrative check trades readability for safety, and the trade is real.** Prose stating a
  figure the run did not record is discarded whole, and a figure with nothing naming what it
  counts is treated as unrecorded. Tightening it too far discarded four of six real narratives
  during development; the corpus of every narrative this loop has written is now a test, in
  both directions.
- **The agentic engine is off by default** (`EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED`); the
  deterministic EDGAR chain is the default execution path. The hosted demo enables it for
  invite-code accounts only, because the loop costs real money per question.
- **The hosted MCP handshake/tool-listing is unauthenticated** (tool *invocation* is not,
  and every tool call is rate-limited per caller —
  [`rate_limit.py`](backend/mcp/rate_limit.py)). The handshake exposes schema only, which is
  normal for MCP; bind it to loopback behind a reverse proxy to close it.
- **No backup/restore runbook.** A [deliberate scope decision](docs/decisions/2026-08-11-showcase-direction.md)
  for a demo with no user data worth recovering, not an oversight. It reopens first if this ever
  takes real users.
- **Single replica.** Auth rate limiting is in-process
  ([`rate_limit.py`](backend/api/rate_limit.py)); a second API replica would enforce it
  independently.

---

## Repository map

| | |
|---|---|
| [`agentic/`](agentic/) | the investigation loop, domain model, adapters, experiment registry |
| [`src/`](src/) | deterministic EDGAR computation — no LLM touches this path |
| [`backend/`](backend/) | FastAPI `/v1`, worker, auth, persistence, artifact delivery, platform MCP |
| [`edgar_project/`](edgar_project/) | orchestration, EDGAR MCP tools, evaluation, CLI |
| [`frontend/`](frontend/) | Next.js web app |
| [`ops/`](ops/) | Grafana dashboard, Prometheus alert rules, Caddy config |
| [`tests/`](tests/) | backend, orchestration, agency, regression, boundary and contract suites — counts in the table above |

**Docs:** [local stack](docs/local-stack.md) · [deploy](docs/deploy.md) ·
[performance](docs/performance.md) ·
[architecture](docs/architecture/) · [the loop](docs/agent/investigation-loop.md) ·
[observability](docs/observability.md) · [auth](docs/auth-api.md) ·
[artifact delivery](docs/artifact-delivery.md) · [extending](docs/extending.md)

**Direction:** [docs/decisions/2026-08-11-showcase-direction.md](docs/decisions/2026-08-11-showcase-direction.md)
records what this is being built as, and what that rules out.

## Contributing · Security · License

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) ·
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · MIT ([LICENSE](LICENSE))
