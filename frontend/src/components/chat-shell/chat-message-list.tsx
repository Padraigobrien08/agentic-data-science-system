"use client";

import type { ChatMessage } from "./types";

type Props = {
  messages: ChatMessage[];
};

/**
 * Scrollable message column (Chatbot UI–style conversation strip).
 * Assistant rows are reserved for future structured components.
 */
export function ChatMessageList({ messages }: Props) {
  return (
    <div
      className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-3 py-4 md:px-6"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
    >
      {messages.length === 0 ? (
        <p className="text-center text-sm text-[var(--muted)]">No messages yet.</p>
      ) : (
        messages.map((m) => (
          <article
            key={m.id}
            className={`flex w-full ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={
                m.role === "user"
                  ? "max-w-[min(100%,36rem)] rounded-2xl rounded-br-md border border-[var(--border)] bg-neutral-100 px-4 py-2.5 text-sm dark:bg-neutral-900"
                  : "max-w-[min(100%,42rem)] rounded-2xl rounded-bl-md border border-[var(--border)] bg-[var(--background)] px-4 py-2.5 text-sm shadow-sm"
              }
            >
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                {m.role === "user" ? "You" : m.role === "system" ? "System" : "Assistant"}
              </p>
              <div className="mt-1 whitespace-pre-wrap text-[var(--foreground)]">{m.content}</div>
            </div>
          </article>
        ))
      )}
    </div>
  );
}
