import Link from "next/link";

import type { SupplementalEvidenceRow as SupplementalEvidenceRowType } from "@/lib/run-primary-view";

type Props = {
  row: SupplementalEvidenceRowType;
  className?: string;
};

export function SupplementalEvidenceRow({ row, className }: Props) {
  const jumpLabel = row.jump?.label === "Open source" ? "Source" : row.jump?.label;

  return (
    <article
      className={
        className ??
        "rounded-card border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
      }
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between md:gap-6">
        <div className="min-w-0 space-y-1">
          <p className="text-[13px] font-semibold leading-5 text-[var(--foreground)]">{row.title}</p>
          <p className="max-w-[40rem] text-[12.5px] leading-[1.8] text-[var(--muted)]">{row.reason}</p>
        </div>
        {row.jump ? (
          <Link
            href={row.jump.href}
            className="shrink-0 rounded-full border border-[var(--border)]/80 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.12em] text-[var(--muted)] transition-colors hover:border-[var(--ui-primary)]/40 hover:text-[var(--foreground)]"
          >
            {jumpLabel}
          </Link>
        ) : null}
      </div>
    </article>
  );
}
