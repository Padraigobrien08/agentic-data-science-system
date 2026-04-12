import { EvidenceChipRow } from "@/components/structured-answer/evidence-chip-row";

import type { FindingCardsProps } from "./types";

/** Plan-alignment / structured finding rows as small cards. */
export function FindingCards({ findings, className }: FindingCardsProps) {
  if (!findings.length) return null;
  return (
    <ul className={className ?? "space-y-2"}>
      {findings.map((f, idx) => (
        <li key={`${f.code}-${idx}`} className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase text-[var(--muted)]">
            <span>{f.code}</span>
            <span className="rounded bg-neutral-200 px-1.5 py-0.5 dark:bg-neutral-800">{f.severity}</span>
          </div>
          <p className="mt-1 text-sm text-[var(--foreground)]">{f.detail}</p>
          <EvidenceChipRow chips={f.chips} />
        </li>
      ))}
    </ul>
  );
}
