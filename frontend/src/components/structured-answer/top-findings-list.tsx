import { EvidenceChipRow } from "@/components/structured-answer/evidence-chip-row";
import Link from "next/link";

import type { TopFindingsListProps } from "./types";

/** Takeaway lines with optional trace/report/critic chips. */
export function TopFindingsList({
  items,
  className,
  chipMode = "full",
  secondaryLinkLabel = "Open source",
}: TopFindingsListProps) {
  if (!items.length) return null;
  return (
    <ul className={className ?? "space-y-2"}>
      {items.map((row, i) => (
        <li
          key={`${i}-${row.text.slice(0, 48)}`}
          className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm leading-snug text-[var(--foreground)]"
        >
          <p>{row.text}</p>
          {chipMode === "full" ? <EvidenceChipRow chips={row.chips} /> : null}
          {chipMode === "secondary" && row.chips[0] ? (
            <Link
              href={row.chips[0].href}
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
