import Link from "next/link";

import type { EvidenceNavChip } from "@/lib/run-primary-view";

type Props = {
  chips: EvidenceNavChip[];
  className?: string;
};

/** Compact pill links — artifacts or deep-dive anchors (readable, low noise). */
export function EvidenceChipRow({ chips, className }: Props) {
  if (!chips.length) return null;
  return (
    <div className={className ?? "mt-2 flex flex-wrap gap-1.5"}>
      {chips.map((c) => (
        <Link
          key={`${c.label}-${c.href}`}
          href={c.href}
          className="inline-flex items-center rounded-full border border-[var(--border)] bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-[var(--foreground)] transition-colors hover:border-[var(--foreground)]/30 hover:bg-[var(--background)] dark:bg-neutral-900/60"
        >
          {c.label}
        </Link>
      ))}
    </div>
  );
}
