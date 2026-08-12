"""
Load and latency measurement for the API's read paths.

    python3 scripts/loadtest.py --base-url http://127.0.0.1:8000 --duration 20 --concurrency 16

**Scope is deliberate.** This measures the paths a visitor can hit for free: health, the public
replay tier, and authenticated run reads. It does **not** load the analysis engines. The
deterministic chain fetches from the SEC (rate-limited, and rude to hammer) and the agentic
loop costs real money per run — putting either under sustained concurrency would measure a
bill, not a bottleneck. Their latency is characterised separately, run by run, in
``docs/performance.md``.

Measurement notes, because a load test that lies is worse than none:

- Warm-up requests are issued and discarded before timing starts, so first-request import and
  connection-pool costs do not land in the percentiles.
- Failures are reported separately and excluded from latency percentiles. A 500 that returns in
  2ms would otherwise look like the fastest request in the run.
- Latency is measured with a monotonic clock around the full request/response cycle including
  reading the body, since a streamed body that arrives slowly is slow to a user.
- Concurrency is a fixed worker count issuing requests back to back — a closed-loop model. It
  reports what the server does under N concurrent clients, not what it does at a fixed arrival
  rate; a saturated server shows up as rising latency rather than a growing queue.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field

try:
    import httpx
except ImportError:  # pragma: no cover - dev dependency
    raise SystemExit("httpx is required: pip install -r requirements-dev.txt")


@dataclass
class Result:
    name: str
    latencies_ms: list[float] = field(default_factory=list)
    statuses: Counter = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)
    wall_seconds: float = 0.0
    concurrency: int = 0

    @property
    def ok_count(self) -> int:
        return sum(n for code, n in self.statuses.items() if 200 <= code < 400)

    @property
    def total(self) -> int:
        return sum(self.statuses.values()) + len(self.errors)

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return float("nan")
        ordered = sorted(self.latencies_ms)
        # Nearest-rank: for small samples this is honest about resolution, where an
        # interpolating estimator invents a value between two observations.
        rank = max(1, min(len(ordered), int(round(p / 100.0 * len(ordered)))))
        return ordered[rank - 1]

    @property
    def rps(self) -> float:
        return self.ok_count / self.wall_seconds if self.wall_seconds else 0.0


async def _worker(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
    deadline: float,
    result: Result,
) -> None:
    while time.monotonic() < deadline:
        started = time.monotonic()
        try:
            response = await client.request(method, url, headers=headers)
            await response.aread()
        except Exception as exc:  # noqa: BLE001 — a transport failure is a result, not a crash
            result.errors.append(f"{type(exc).__name__}: {exc}")
            continue
        elapsed_ms = (time.monotonic() - started) * 1000.0
        result.statuses[response.status_code] += 1
        if 200 <= response.status_code < 400:
            result.latencies_ms.append(elapsed_ms)


async def run_scenario(
    base_url: str,
    name: str,
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    duration: float,
    concurrency: int,
    warmup: int = 5,
) -> Result:
    result = Result(name=name, concurrency=concurrency)
    url = f"{base_url.rstrip('/')}{path}"
    hdrs = headers or {}

    limits = httpx.Limits(max_connections=concurrency + 4, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        for _ in range(warmup):
            try:
                r = await client.request(method, url, headers=hdrs)
                await r.aread()
            except Exception:  # noqa: BLE001
                pass

        deadline = time.monotonic() + duration
        started = time.monotonic()
        await asyncio.gather(
            *(_worker(client, method, url, hdrs, deadline, result) for _ in range(concurrency))
        )
        result.wall_seconds = time.monotonic() - started
    return result


def format_table(results: list[Result]) -> str:
    header = (
        f"{'scenario':<34}{'conc':>5}{'ok':>8}{'err':>6}{'rps':>9}"
        f"{'p50':>9}{'p90':>9}{'p95':>9}{'p99':>9}{'max':>9}"
    )
    lines = [header, "-" * len(header)]
    for r in results:
        bad = r.total - r.ok_count
        mx = max(r.latencies_ms) if r.latencies_ms else float("nan")
        lines.append(
            f"{r.name:<34}{r.concurrency:>5}{r.ok_count:>8}{bad:>6}{r.rps:>9.1f}"
            f"{r.percentile(50):>9.1f}{r.percentile(90):>9.1f}{r.percentile(95):>9.1f}"
            f"{r.percentile(99):>9.1f}{mx:>9.1f}"
        )
    lines.append("")
    lines.append("latencies in ms; rps counts successful responses only")
    for r in results:
        odd = {c: n for c, n in r.statuses.items() if not (200 <= c < 400)}
        if odd or r.errors:
            lines.append(f"  {r.name}: non-2xx={odd or '{}'} transport_errors={len(r.errors)}")
            if r.errors:
                lines.append(f"    first: {r.errors[0]}")
    return "\n".join(lines)


def to_json(results: list[Result]) -> str:
    return json.dumps(
        [
            {
                "scenario": r.name,
                "concurrency": r.concurrency,
                "ok": r.ok_count,
                "failed": r.total - r.ok_count,
                "wall_seconds": round(r.wall_seconds, 3),
                "rps": round(r.rps, 2),
                "p50_ms": round(r.percentile(50), 2),
                "p90_ms": round(r.percentile(90), 2),
                "p95_ms": round(r.percentile(95), 2),
                "p99_ms": round(r.percentile(99), 2),
                "max_ms": round(max(r.latencies_ms), 2) if r.latencies_ms else None,
                "mean_ms": round(statistics.fmean(r.latencies_ms), 2) if r.latencies_ms else None,
                "statuses": {str(k): v for k, v in sorted(r.statuses.items())},
            }
            for r in results
        ],
        indent=2,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 scripts/loadtest.py",
        description="Measure read-path latency and throughput. Does not exercise the engines.",
    )
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--duration", type=float, default=15.0, help="Seconds per scenario.")
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--demo-slug", default=None, help="Published demo slug to exercise.")
    p.add_argument("--token", default=None, help="Bearer token for authenticated scenarios.")
    p.add_argument("--json", dest="json_out", action="store_true", help="Emit JSON.")
    return p


async def main_async(args: argparse.Namespace) -> int:
    scenarios: list[tuple[str, str, dict[str, str]]] = [
        ("health", "/v1/health", {}),
    ]
    if args.demo_slug:
        scenarios += [
            ("demos: list", "/v1/demos", {}),
            ("demos: full investigation", f"/v1/demos/{args.demo_slug}", {}),
        ]
    if args.token:
        auth = {"Authorization": f"Bearer {args.token}"}
        scenarios += [("auth: projects", "/v1/projects", auth)]

    results: list[Result] = []
    for name, path, headers in scenarios:
        print(f"running {name} …", flush=True)
        results.append(
            await run_scenario(
                args.base_url,
                name,
                path,
                headers=headers,
                duration=args.duration,
                concurrency=args.concurrency,
            )
        )

    print()
    print(to_json(results) if args.json_out else format_table(results))
    # A scenario that never succeeded is a failed measurement, not a slow one.
    return 1 if any(r.ok_count == 0 for r in results) else 0


def main() -> int:
    return asyncio.run(main_async(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
