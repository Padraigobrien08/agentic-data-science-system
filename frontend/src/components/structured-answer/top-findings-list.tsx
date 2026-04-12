import type { TopFindingsListProps } from "./types";

/** Bulleted takeaway lines (compact cards). */
export function TopFindingsList({ items, className }: TopFindingsListProps) {
  if (!items.length) return null;
  return (
    <ul className={className ?? "space-y-2"}>
      {items.map((t) => (
        <li
          key={t}
          className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm leading-snug text-[var(--foreground)]"
        >
          {t}
        </li>
      ))}
    </ul>
  );
}
