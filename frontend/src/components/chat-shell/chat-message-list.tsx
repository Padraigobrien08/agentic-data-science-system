"use client";

import { AssistantStructuredFrame } from "./assistant-structured-frame";
import { ChatRunAnswerCard } from "./chat-run-answer-card";
import type { ChatMessage } from "./types";

type Props = {
  messages: ChatMessage[];
};

function deliveryNote(message: Extract<ChatMessage, { role: "assistant" }>): string | null {
  if (message.reroutedFromBackground) {
    return message.deliveryDetail ?? "Background delivery was rerouted to immediate execution.";
  }
  if (message.deliveryMode === "background_degraded") {
    return message.deliveryDetail ?? "Background delivery is degraded in this workspace.";
  }
  if (message.deliveryMode === "sync_only") {
    return message.deliveryDetail ?? "This workspace is currently running chat requests synchronously.";
  }
  return message.deliveryDetail ?? null;
}

function SystemStrip({ content }: { content: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-neutral-100/60 px-3 py-2 text-center text-[11px] text-[var(--muted)] dark:bg-neutral-900/40">
      {content}
    </div>
  );
}

/**
 * Conversation strip: user and assistant chat bubbles.
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
          const note = deliveryNote(m);
          return (
            <article key={m.id} className="flex w-full justify-start">
              <div className="w-full max-w-[min(100%,42rem)]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Assistant
                </p>
                {m.pending ? (
                  <div className="mt-2">
                    <AssistantStructuredFrame messageId={m.id} variant="pending" />
                  </div>
                ) : m.answerCard ? (
                  <div className="mt-2">
                    <ChatRunAnswerCard answerCard={m.answerCard} />
                  </div>
                ) : (
                  <div className="mt-1 max-w-[min(100%,38rem)] whitespace-pre-wrap rounded-2xl rounded-bl-md border border-[var(--border)] bg-[var(--background)] px-4 py-2.5 text-[var(--foreground)]">
                    {m.content}
                  </div>
                )}
                {m.routingReason ? (
                  <p className="mt-2 rounded-lg border border-[var(--border)] bg-neutral-50/70 px-3 py-2 text-[11px] text-[var(--muted)] dark:bg-neutral-950/30">
                    {m.routingReason}
                  </p>
                ) : null}
                {m.rewriteSuggestions?.length ? (
                  <div className="mt-2 rounded-lg border border-[var(--border)] bg-neutral-50/70 px-3 py-2 dark:bg-neutral-950/30">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                      Try one of these rewrites
                    </p>
                    <ul className="mt-2 space-y-1.5 text-[11px] text-[var(--foreground)]">
                      {m.rewriteSuggestions.map((suggestion) => (
                        <li key={suggestion} className="list-inside list-disc">
                          {suggestion}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {note ? <p className="mt-2 text-[10px] text-[var(--muted)]">{note}</p> : null}
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
