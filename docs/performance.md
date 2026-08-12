# Performance

Measured, not estimated. Reproduce with
[`scripts/loadtest.py`](../scripts/loadtest.py).

**Environment.** Apple M4, 10 cores, 24 GB. Docker 29.6.2, the standard
[`docker-compose.yml`](../docker-compose.yml) stack: Postgres 16, one uvicorn process, one
worker. Load generated on the same host, so client and server compete for CPU — real
throughput on a dedicated box would be higher, and these numbers are the pessimistic end.

**What is deliberately not load-tested.** The two analysis engines. The deterministic chain
fetches from the SEC, which is rate-limited and rude to hammer; the agentic loop costs real
money per run, so sustained concurrency against it would measure a bill rather than a
bottleneck. Both are characterised individually below instead.

---

## What one visitor feels

Single client, no contention — the latency an actual reader of the demo experiences.

| endpoint | p50 | p90 | p99 | max |
|---|---|---|---|---|
| `GET /v1/projects` (authenticated) | **2.8 ms** | 3.7 | 6.4 | 12.9 |
| `GET /v1/health` | **3.8 ms** | 4.7 | 8.0 | 27.1 |
| `GET /v1/demos` (public listing) | **4.8 ms** | 6.3 | 10.6 | 74.0 |
| `GET /v1/demos/{slug}` (full investigation) | **7.4 ms** | 8.5 | 17.0 | 52.4 |

The heaviest public read — an entire investigation with its hypotheses, evidence, experiments,
decisions, critiques, conclusion and timeline — returns in **7.4 ms**. Every read path is far
below the ~100 ms threshold where interaction stops feeling immediate.

## Under concurrency

Closed-loop: N workers issuing requests back to back for 15 s.

| endpoint | conc | rps | p50 | p95 | p99 | errors |
|---|---:|---:|---:|---:|---:|---:|
| `/v1/health` | 16 | 360 | 41 ms | 75 | 110 | 0 |
| | 64 | 312 | 184 ms | 376 | 509 | 0 |
| `/v1/demos` | 16 | 205 | 62 ms | 169 | 263 | 0 |
| | 64 | 253 | 241 ms | 427 | 557 | 0 |
| `/v1/demos/{slug}` | 16 | 172 | 86 ms | 152 | 195 | 0 |
| | 64 | 158 | 382 ms | 688 | 971 | 0 |
| `/v1/projects` | 16 | 460 | 31 ms | 64 | 100 | 0 |

**Throughput plateaus between roughly 150 and 460 rps** depending on the path, and past that
point latency rises about linearly with concurrency. That is the signature of a saturated
single-process server: work queues rather than failing.

**Zero errors at every level.** No 5xx, no dropped connections, no timeouts across ~40,000
requests. The stack degrades by getting slower, which is the correct failure mode for a demo —
a visitor waits rather than sees a stack trace.

For context on what the hosted demo actually needs: 158 rps on the *heaviest* public endpoint
is roughly 13 million requests a day. The demo is not going to be throughput-bound.

## The engines

### The loop's own machinery is not the cost

A complete investigation over the 96-row operational dataset, using the deterministic fixture
policy so no model is called:

```
fixture-policy investigation, n=5 — min 39 ms · median 42 ms · max 124 ms
```

That is goal interpretation, hypothesis generation, planning, six experiments, evidence
updates, critique, termination, conclusion synthesis, artifact ingestion and persistence —
**42 ms end to end**.

The same investigation with a real model takes **~8 seconds**. So better than 99% of the wall
clock in a live run is model latency, and essentially none of it is the loop, the experiment
registry, or persistence. Two consequences worth stating plainly:

- **Optimising the loop would be pointless.** The only lever on investigation latency is model
  choice, parallel experiments, or fewer calls.
- **The offline paths are genuinely fast.** The agency benchmark and fixture demo run at
  full speed because they are not waiting on anything.

### Live runs, measured from the recorded demos

| | EDGAR (live SEC) | tabular CSV |
|---|---|---|
| loop wall clock | 13.0 s | ~8 s |
| model calls | 11 | 14 |
| experiments | 7 | 6 |
| spend | $0.0101 | $0.0121 |

Per-component latency separates cleanly on the
[agent-loop dashboard](observability.md): the four model-backed components sit at ~2 s, the six
deterministic ones at ~5 ms.

---

## Findings

**1. `/v1/health` costs about twice what `/v1/ready` does.** Health runs worker-queue and
evaluation-dependency aggregates on every call; ready is a single `SELECT 1`. Measured
back to back:

| | p50 @1 | rps @1 | p50 @16 | rps @16 |
|---|---|---|---|---|
| `/v1/health` | 2.9 ms | 315 | 35 ms | 420 |
| `/v1/ready` | **1.6 ms** | **578** | **14 ms** | **656** |

Harmless at a 30-second uptime-monitor cadence, which is health's only real caller — and its
extra work is the point, since it reports LLM and dependency posture. But point load balancers
and container orchestrators at `/ready`.

Note the run-to-run spread: health measured 3.8 ms p50 in the first sweep and 2.9 ms here.
Differences under about 1 ms on this setup are noise, and nothing in this document should be
read to finer resolution than that.

**2. The public replay tier is the right thing to have load-tested.** It is the only
unauthenticated surface and the one a reviewer hits first. It holds 158–253 rps with no errors
and sub-second p99 even at 64 concurrent clients.

**3. Nothing here needs optimising.** Every read path is single-digit milliseconds unloaded,
and the saturation ceiling is three to four orders of magnitude above expected demo traffic.
Recording this is the point — a number nobody measured is not a fact.

## Reproducing

```bash
docker compose up -d --build
# seed a published demo (fixture policy = free, no network):
#   register → POST /v1/investigations → publish_demo publish <id> --slug <slug>
python3 scripts/loadtest.py \
  --base-url http://127.0.0.1:8000 \
  --demo-slug <slug> --duration 15 --concurrency 16
```

`--json` emits machine-readable output. The harness discards warm-up requests, excludes
failures from latency percentiles (a fast 500 would otherwise look like the best response in
the run), and reports non-2xx status counts separately.
