"""
Generate the non-EDGAR dataset for the public replay tier.

Deterministic (fixed seed) and committed, so the recorded investigation over it is
reproducible and the demo does not depend on a network fetch or a licensed source.

The data is deliberately *confounded*. Delivery times in the ``north`` region degrade over the
final eight months — but order volume in that region grows sharply over the same window while
staffing stays flat. So "did service quality degrade?" has genuine evidence on both sides:
the outcome metric worsened, and there is a competing explanation for why. That is what gives
the loop's critic something real to challenge instead of a single obvious signal to confirm.

    python3 scripts/build_demo_dataset.py

Writes ``demo/datasets/operational_delivery.csv``. See
``docs/decisions/2026-08-11-showcase-direction.md`` (D5, S1).
"""

from __future__ import annotations

import csv
import random
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "demo" / "datasets" / "operational_delivery.csv"

SEED = 20260811
REGIONS = ("north", "south", "east", "west")
MONTHS = 24
#: Degradation and the volume surge start here, in the same month, on purpose.
INFLECTION = 16

FIELDS = (
    "month",
    "region",
    "avg_delivery_days",
    "order_volume",
    "on_time_rate",
    "staff_count",
)

_BASE_DELIVERY = {"north": 2.8, "south": 3.1, "east": 2.6, "west": 3.4}
_BASE_VOLUME = {"north": 4200, "south": 3100, "east": 5200, "west": 2400}
_BASE_STAFF = {"north": 34, "south": 28, "east": 41, "west": 22}


def _month_label(index: int) -> str:
    year = 2024 + (index // 12)
    month = (index % 12) + 1
    return date(year, month, 1).isoformat()


def build_rows(seed: int = SEED) -> list[dict[str, object]]:
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []

    for i in range(MONTHS):
        for region in REGIONS:
            past_inflection = i >= INFLECTION
            months_in = max(0, i - INFLECTION)

            delivery = _BASE_DELIVERY[region] + rng.gauss(0, 0.08)
            volume = _BASE_VOLUME[region] * (1 + 0.004 * i) + rng.gauss(0, 60)
            staff = _BASE_STAFF[region] + (i // 8)

            if region == "north" and past_inflection:
                # The signal: delivery slows, and volume climbs steeply over the same window
                # while staffing does not follow. Neither explanation is free.
                delivery += 0.16 * months_in
                volume *= 1 + 0.055 * months_in

            # On-time rate falls out of delivery time rather than being an independent knob,
            # so the two outcome metrics agree with each other, as they would in real data.
            on_time = max(0.55, min(0.99, 1.06 - 0.13 * delivery + rng.gauss(0, 0.012)))

            rows.append(
                {
                    "month": _month_label(i),
                    "region": region,
                    "avg_delivery_days": round(delivery, 2),
                    "order_volume": int(round(volume)),
                    "on_time_rate": round(on_time, 3),
                    "staff_count": int(staff),
                }
            )
    return rows


def main() -> int:
    rows = build_rows()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(FIELDS))
        writer.writeheader()
        writer.writerows(rows)

    north_early = [r for r in rows if r["region"] == "north"][:INFLECTION]
    north_late = [r for r in rows if r["region"] == "north"][INFLECTION:]
    early = sum(float(r["avg_delivery_days"]) for r in north_early) / len(north_early)
    late = sum(float(r["avg_delivery_days"]) for r in north_late) / len(north_late)
    vol_early = sum(int(r["order_volume"]) for r in north_early) / len(north_early)
    vol_late = sum(int(r["order_volume"]) for r in north_late) / len(north_late)

    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    print(f"  north avg_delivery_days: {early:.2f} -> {late:.2f}")
    print(f"  north order_volume:      {vol_early:.0f} -> {vol_late:.0f}")
    print("  (both move together — the confound is the point)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
