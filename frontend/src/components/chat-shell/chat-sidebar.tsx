"use client";

import Link from "next/link";

import type { ChatSessionStub } from "./types";

type Props = {
  projectId: string;
  sessions: ChatSessionStub[];
  activeSessionId: string | null;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
};

/**
 * Narrow session rail (Chatbot UI sidebar pattern), backed by local stubs for now.
 */
export function ChatSidebar({
  projectId,
  sessions,
  activeSessionId,
  onNewSession,
  onSelectSession,
}: Props) {
  const base = `/projects/${projectId}`;

  return (
    <aside className="flex w-full flex-shrink-0 flex-col border-b border-[var(--border)] bg-neutral-50 dark:border-[var(--border)] dark:bg-neutral-950 md:w-60 md:border-b-0 md:border-r">
      <div className="flex items-center gap-2 border-b border-[var(--border)] p-3">
        <button
          type="button"
          onClick={onNewSession}
          className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs font-medium text-[var(--foreground)]"
        >
          New conversation
        </button>
      </div>
      <nav className="flex max-h-48 flex-1 flex-col gap-0.5 overflow-y-auto p-2 md:max-h-none" aria-label="Conversations">
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
      <div className="mt-auto border-t border-[var(--border)] p-2 text-[10px] text-[var(--muted)]">
        <Link href={`${base}/runs`} className="block rounded px-2 py-1 underline hover:text-[var(--foreground)]">
          All runs
        </Link>
        <Link href={`${base}/runs/new`} className="mt-1 block rounded px-2 py-1 underline hover:text-[var(--foreground)]">
          Submit run
        </Link>
      </div>
    </aside>
  );
}
