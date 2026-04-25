"use client";

import { useCallback } from "react";

import { StatusBadge } from "@/components/ui/technical";
import { formatDate, shortId } from "@/lib/format";
import type { ChatRecentRun } from "./types";

type Props = {
  scopeTickers: string[];
  newConversationAction: (payload: FormData) => void;
  recentRuns: ChatRecentRun[];
};

/**
 * Conversation-first rail with a new-chat affordance and in-chat history.
 */
export function ChatSidebar({ scopeTickers, newConversationAction, recentRuns }: Props) {
  const scrollToAnswer = useCallback((targetId?: string) => {
    if (!targetId) return;
    const node = document.getElementById(targetId);
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  return (
    <aside className="flex w-full flex-shrink-0 flex-col border-b border-[var(--border)] bg-neutral-50 dark:border-[var(--border)] dark:bg-neutral-950 md:w-56 md:border-b-0 md:border-r">
      <div className="border-b border-[var(--border)] p-3">
        <div className="space-y-2 px-1">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Chat</p>
          <p className="text-xs leading-5 text-[var(--muted)]">
            Ask questions, keep the scope lightweight, and return to prior answers from one thread.
          </p>
        </div>
        <form action={newConversationAction} className="mt-3">
          <input type="hidden" name="tickers" value={scopeTickers.join(",")} />
          <button
            type="submit"
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs font-medium text-[var(--foreground)] shadow-sm transition hover:bg-neutral-100 disabled:opacity-50 dark:hover:bg-neutral-900"
            disabled={scopeTickers.length === 0}
          >
            New chat
          </button>
        </form>
      </div>

      <div className="border-b border-[var(--border)] p-3">
        <p className="px-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">History</p>
      </div>
      <nav
        className="scrollbar-hidden flex max-h-40 flex-1 flex-col gap-1 overflow-y-auto p-2 md:max-h-none"
        aria-label="Chat history"
      >
        {recentRuns.length === 0 ? (
          <p className="px-2 py-2 text-xs text-[var(--muted)]">Earlier answers in this chat will appear here.</p>
        ) : null}
        {recentRuns.map((run) => (
          <button
            key={run.id}
            type="button"
            onClick={() => scrollToAnswer(run.scrollTargetId)}
            className="rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs hover:bg-neutral-100 dark:hover:bg-neutral-900"
          >
            <span className="line-clamp-3 font-medium text-[var(--foreground)]">{run.title}</span>
            {run.preview ? (
              <span className="mt-1 block line-clamp-2 text-[11px] leading-5 text-[var(--muted)]">{run.preview}</span>
            ) : null}
            <span className="mt-2 flex flex-wrap items-center gap-2">
              <StatusBadge status={run.status} variant="friendly" />
              <span className="text-[10px] text-[var(--muted)]">{formatDate(run.createdAt)}</span>
            </span>
            <span className="mt-1 block font-mono text-[10px] text-[var(--muted)]">{shortId(run.id)}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
