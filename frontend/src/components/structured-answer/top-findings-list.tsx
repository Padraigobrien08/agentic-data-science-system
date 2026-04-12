import { EvidenceChipRow } from "@/components/structured-answer/evidence-chip-row";

import type { TopFindingsListProps } from "./types";

/** Takeaway lines with optional trace/report/critic chips. */
export function TopFindingsList({ items, className }: TopFindingsListProps) {
  if (!items.length) return null;
  return (
    <ul className={className ?? "space-y-2"}>
      {items.map((row, i) => (
        <li
          key={`${i}-${row.text.slice(0, 48)}`}
          className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm leading-snug text-[var(--foreground)]"
        >
          <p>{row.text}</p>
          <EvidenceChipRow chips={row.chips} />
        </li>
      ))}
    </ul>
  );
}
