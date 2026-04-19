"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { StatusBadge } from "@/components/ui/technical";
import { formatDate, shortId } from "@/lib/format";
import type { ChatRecentRun } from "./types";

type Props = {
  projectId: string;
  recentRuns: ChatRecentRun[];
};

function navClass(href: string, pathname: string | null) {
  if (!pathname) {
    return "block rounded-md px-2 py-1.5 text-xs text-[var(--muted)] hover:bg-neutral-100 hover:text-[var(--foreground)] dark:hover:bg-neutral-900";
  }
  const on =
    href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(`${href}/`);
  return on
    ? "block rounded-md bg-neutral-200 px-2 py-1.5 text-xs font-medium text-[var(--foreground)] dark:bg-neutral-800"
    : "block rounded-md px-2 py-1.5 text-xs text-[var(--muted)] hover:bg-neutral-100 hover:text-[var(--foreground)] dark:hover:bg-neutral-900";
}

/**
 * Workspace nav plus a read-only recent-runs rail.
 */
export function ChatSidebar({ projectId, recentRuns }: Props) {
  const pathname = usePathname();
  const base = `/projects/${projectId}`;

  return (
    <aside className="flex w-full flex-shrink-0 flex-col border-b border-[var(--border)] bg-neutral-50 dark:border-[var(--border)] dark:bg-neutral-950 md:w-56 md:border-b-0 md:border-r">
      <div className="border-b border-[var(--border)] p-2">
        <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Workspace
        </p>
        <nav className="flex flex-col gap-0.5" aria-label="Workspace pages">
          <Link href="/" className={navClass("/", pathname)}>
            Home
          </Link>
          <Link href={`${base}/chat`} className={navClass(`${base}/chat`, pathname)}>
            Chat
          </Link>
          <Link href={`${base}/runs`} className={navClass(`${base}/runs`, pathname)}>
            Runs
          </Link>
          <Link href={`${base}/runs/new`} className={navClass(`${base}/runs/new`, pathname)}>
            Submit run
          </Link>
        </nav>
      </div>

      <div className="border-b border-[var(--border)] p-3">
        <p className="px-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Recent runs
        </p>
      </div>
      <nav className="flex max-h-40 flex-1 flex-col gap-1 overflow-y-auto p-2 md:max-h-none" aria-label="Recent runs">
        {recentRuns.length === 0 ? (
          <p className="px-2 py-2 text-xs text-[var(--muted)]">Completed analyses will appear here.</p>
        ) : null}
        {recentRuns.map((run) => (
          <Link
            key={run.id}
            href={run.href}
            className="rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs hover:bg-neutral-100 dark:hover:bg-neutral-900"
          >
            <span className="line-clamp-2 font-medium text-[var(--foreground)]">{run.goalDisplay}</span>
            <span className="mt-2 flex flex-wrap items-center gap-2">
              <StatusBadge status={run.status} variant="friendly" />
              <span className="text-[10px] text-[var(--muted)]">{formatDate(run.createdAt)}</span>
            </span>
            <span className="mt-1 block font-mono text-[10px] text-[var(--muted)]">{shortId(run.id)}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
