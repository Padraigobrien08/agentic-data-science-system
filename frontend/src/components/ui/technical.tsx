import type { AnalysisRunStatus } from "@/lib/api/types";

type SectionProps = {
  id?: string;
  title: string;
  description?: string;
  children: React.ReactNode;
  /** Extra classes on the outer `<section>` (e.g. scroll margin, density). */
  className?: string;
  /** Classes on the inner content wrapper (default `p-3`). */
  bodyClassName?: string;
  /** Classes on the section header strip. */
  headerClassName?: string;
};

export function Section({
  id,
  title,
  description,
  children,
  className,
  bodyClassName,
  headerClassName,
}: SectionProps) {
  const outer = className?.trim()
    ? `border border-[var(--border)] rounded ${className}`
    : "border border-[var(--border)] rounded";
  const body = bodyClassName?.trim() ? bodyClassName : "p-3";
  const head = headerClassName?.trim()
    ? `border-b border-[var(--border)] bg-neutral-50 px-3 py-2 dark:bg-neutral-900/50 ${headerClassName}`
    : "border-b border-[var(--border)] bg-neutral-50 px-3 py-2 dark:bg-neutral-900/50";
  return (
    <section id={id} className={outer}>
      <header className={head}>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--foreground)]">
          {title}
        </h2>
        {description ? (
          <p className="mt-0.5 text-xs text-[var(--muted)]">{description}</p>
        ) : null}
      </header>
      <div className={body}>{children}</div>
    </section>
  );
}

const STATUS_STYLES: Partial<Record<AnalysisRunStatus, string>> = {
  success: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  error: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
  cancelled: "bg-neutral-200 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200",
  running: "bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-100",
  queued: "bg-sky-100 text-sky-950 dark:bg-sky-950 dark:text-sky-100",
  pending: "bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200",
  partial_success:
    "bg-orange-100 text-orange-950 dark:bg-orange-950 dark:text-orange-100",
  no_data: "bg-violet-100 text-violet-950 dark:bg-violet-950 dark:text-violet-100",
};

export function StatusBadge({ status }: { status: AnalysisRunStatus }) {
  const cls = STATUS_STYLES[status] ?? "bg-neutral-100 text-neutral-800";
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 font-mono text-xs font-medium ${cls}`}
    >
      {status}
    </span>
  );
}

type MetaRowProps = { label: string; children: React.ReactNode };

export function MetaRow({ label, children }: MetaRowProps) {
  return (
    <div className="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1 border-b border-[var(--border)] py-1.5 text-sm last:border-0 sm:grid-cols-[10rem_1fr]">
      <div className="font-medium text-[var(--muted)]">{label}</div>
      <div className="min-w-0 break-all font-mono text-xs">{children}</div>
    </div>
  );
}

export function JsonPanel({ value, title }: { value: unknown; title?: string }) {
  return (
    <div>
      {title ? (
        <p className="mb-1 text-xs font-medium text-[var(--muted)]">{title}</p>
      ) : null}
      <pre className="max-h-[28rem] overflow-auto rounded border border-[var(--border)] bg-neutral-50 p-2 text-xs leading-relaxed dark:bg-neutral-950">
        {value === null || value === undefined
          ? "null"
          : JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}
