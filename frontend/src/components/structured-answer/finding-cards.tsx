import { EvidenceChipRow } from "@/components/structured-answer/evidence-chip-row";
import Link from "next/link";

import type { FindingCardsProps } from "./types";

/** Plan-alignment / structured finding rows as small cards. */
export function FindingCards({
  findings,
  className,
  chipMode = "full",
  secondaryLinkLabel = "Open source",
}: FindingCardsProps) {
  if (!findings.length) return null;
  return (
    <ul className={className ?? "space-y-2"}>
      {findings.map((f, idx) => (
        <li key={`${f.code}-${idx}`} className="rounded-control border border-[var(--border)] px-3 py-2 text-sm">
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase text-[var(--muted)]">
            <span>{f.code}</span>
            <span className="rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5">{f.severity}</span>
          </div>
          <p className="mt-1 text-sm text-[var(--foreground)]">{f.detail}</p>
          {chipMode === "full" ? <EvidenceChipRow chips={f.chips} /> : null}
          {chipMode === "secondary" && f.chips[0] ? (
            <Link
              href={f.chips[0].href}
              className="mt-2 inline-flex text-[11px] font-medium text-[var(--muted)] underline underline-offset-4 hover:text-[var(--foreground)]"
            >
              {secondaryLinkLabel}
            </Link>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
