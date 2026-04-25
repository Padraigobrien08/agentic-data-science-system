import Link from "next/link";

import type { SupplementalEvidenceRow as SupplementalEvidenceRowType } from "@/lib/run-primary-view";

type Props = {
  row: SupplementalEvidenceRowType;
  className?: string;
};

export function SupplementalEvidenceRow({ row, className }: Props) {
  return (
    <article
      className={
        className ??
        "rounded-[1.15rem] border border-[var(--border)]/70 bg-white/75 px-4 py-3.5 dark:bg-neutral-950/25"
      }
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between md:gap-6">
        <div className="min-w-0 space-y-1.5">
          <p className="text-[13px] font-semibold leading-5 text-[var(--foreground)]">{row.title}</p>
          <p className="max-w-[40rem] text-[12.5px] leading-6 text-[var(--muted)]">{row.reason}</p>
        </div>
        {row.jump ? (
          <Link
            href={row.jump.href}
            className="shrink-0 text-[11px] font-medium text-[var(--muted)] underline underline-offset-4 transition-colors hover:text-[var(--ui-primary)]"
          >
            {row.jump.label}
          </Link>
        ) : null}
      </div>
    </article>
  );
}
