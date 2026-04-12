"use client";

import { AssistantStructuredFrame } from "./assistant-structured-frame";
import type { ChatMessage } from "./types";

type Props = {
  messages: ChatMessage[];
};

function SystemStrip({ content }: { content: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-neutral-100/60 px-3 py-2 text-center text-[11px] text-[var(--muted)] dark:bg-neutral-900/40">
      {content}
    </div>
  );
}

/**
 * Conversation strip: user text bubbles; assistant = structured frames only.
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
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center">
          <p className="text-sm font-medium text-[var(--foreground)]">No messages yet</p>
          <p className="max-w-sm text-xs text-[var(--muted)]">
            Use the composer to describe a goal. Assistant replies will appear as structured panels, not
            generic chat prose.
          </p>
        </div>
      ) : (
        messages.map((m) => {
          if (m.role === "user") {
            return (
              <article key={m.id} className="flex w-full justify-end">
                <div className="max-w-[min(100%,36rem)] rounded-2xl rounded-br-md border border-[var(--border)] bg-neutral-100 px-4 py-2.5 text-sm dark:bg-neutral-900">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                    You
                  </p>
                  <div className="mt-1 whitespace-pre-wrap text-[var(--foreground)]">{m.content}</div>
                </div>
              </article>
            );
          }
          if (m.role === "system") {
            return <SystemStrip key={m.id} content={m.content} />;
          }
          return (
            <article key={m.id} className="flex w-full justify-start">
              <AssistantStructuredFrame messageId={m.id} variant="empty" />
            </article>
          );
        })
      )}
    </div>
  );
}
