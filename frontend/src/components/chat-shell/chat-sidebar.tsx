"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { ChatSessionStub } from "./types";

type Props = {
  projectId: string;
  sessions: ChatSessionStub[];
  activeSessionId: string | null;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
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
 * Session list + global workspace links (Chatbot UI sidebar pattern, trimmed).
 */
export function ChatSidebar({
  projectId,
  sessions,
  activeSessionId,
  onNewSession,
  onSelectSession,
}: Props) {
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

      <div className="flex items-center gap-2 border-b border-[var(--border)] p-3">
        <button
          type="button"
          onClick={onNewSession}
          className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs font-medium text-[var(--foreground)]"
        >
          New conversation
        </button>
      </div>
      <nav className="flex max-h-40 flex-1 flex-col gap-0.5 overflow-y-auto p-2 md:max-h-none" aria-label="Conversations">
        {sessions.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelectSession(s.id)}
            className={`w-full rounded-md px-2 py-2 text-left text-xs ${
              activeSessionId === s.id
                ? "bg-neutral-200 font-medium dark:bg-neutral-800"
                : "text-[var(--muted)] hover:bg-neutral-100 dark:hover:bg-neutral-900"
            }`}
          >
            <span className="line-clamp-2">{s.title}</span>
            <span className="mt-0.5 block font-mono text-[10px] text-[var(--muted)]">{s.updatedAt}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
