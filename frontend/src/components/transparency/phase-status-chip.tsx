type Props = { status: string | undefined };

export function PhaseStatusChip({ status }: Props) {
  if (!status) return <span className="text-[var(--muted)]">—</span>;
  const muted =
    status === "skipped"
      ? "bg-neutral-200 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200"
      : status === "failed"
        ? "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200"
        : status === "degraded"
          ? "bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-100"
          : "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200";
  return (
    <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-medium ${muted}`}>
      {status}
    </span>
  );
}
