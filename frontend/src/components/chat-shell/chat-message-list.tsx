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
    <div className="mx-auto max-w-[40rem] rounded-full border border-[var(--border)] bg-neutral-100/60 px-4 py-2 text-center text-[11px] text-[var(--muted)] dark:bg-neutral-900/40">
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
      className="scrollbar-hidden flex min-h-0 flex-1 flex-col gap-7 overflow-y-auto px-4 py-6 md:px-6 lg:px-10"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
    >
      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center">
          <p className="text-sm font-medium text-[var(--foreground)]">No messages yet</p>
          <p className="max-w-sm text-xs text-[var(--muted)]">
            Use the composer to describe a goal. Assistant replies will appear as narrative answers with
            supporting proof beneath them.
          </p>
        </div>
      ) : (
        messages.map((m) => {
          if (m.role === "user") {
            return (
              <article key={m.id} className="flex w-full justify-center">
                <div className="w-full max-w-[76rem]">
                  <div className="flex justify-end">
                    <div className="max-w-[min(100%,44rem)] rounded-[1.6rem] rounded-tr-[1rem] border border-[var(--border)] bg-white/92 px-5 py-4 text-sm shadow-[0_12px_32px_rgba(15,23,42,0.04)] dark:bg-neutral-950/80">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                        You
                      </p>
                      <div className="mt-2 whitespace-pre-wrap text-[15px] leading-7 text-[var(--foreground)]">
                        {m.content}
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            );
          }
          if (m.role === "system") {
            return <SystemStrip key={m.id} content={m.content} />;
          }
          const note = deliveryNote(m);
          return (
            <article key={m.id} className="flex w-full justify-center">
              <div className="w-full max-w-[76rem]">
                {m.pending ? (
                  <div className="mx-auto max-w-[58rem]">
                    <AssistantStructuredFrame messageId={m.id} variant="pending" />
                  </div>
                ) : m.answerCard ? (
                  <div className="mx-auto max-w-[66rem]">
                    <ChatRunAnswerCard
                      answerCard={m.answerCard}
                      runId={m.runId}
                      runHref={m.runHref}
                      runStatus={m.runStatus}
                      runCreatedAt={m.runCreatedAt}
                      runFinishedAt={m.runFinishedAt}
                    />
                  </div>
                ) : (
                  <div className="mx-auto max-w-[52rem] whitespace-pre-wrap rounded-[1.75rem] border border-[var(--border)] bg-white/80 px-5 py-4 text-[15px] leading-7 text-[var(--foreground)] shadow-[0_12px_32px_rgba(15,23,42,0.04)] dark:bg-neutral-950/70">
                    {m.content}
                  </div>
                )}
                {m.routingReason ? (
                  <div className="mx-auto mt-3 max-w-[52rem] rounded-2xl border border-[var(--border)] bg-neutral-50/80 px-4 py-3 text-[12px] leading-6 text-[var(--muted)] dark:bg-neutral-950/30">
                    {m.routingReason}
                  </div>
                ) : null}
                {m.rewriteSuggestions?.length ? (
                  <div className="mx-auto mt-3 max-w-[52rem] rounded-2xl border border-[var(--border)] bg-neutral-50/80 px-4 py-3 dark:bg-neutral-950/30">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                      Try one of these rewrites
                    </p>
                    <ul className="mt-3 space-y-2 text-[13px] leading-6 text-[var(--foreground)]">
                      {m.rewriteSuggestions.map((suggestion) => (
                        <li key={suggestion} className="list-inside list-disc">
                          {suggestion}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {note ? (
                  <p className="mx-auto mt-3 max-w-[52rem] text-[11px] leading-5 text-[var(--muted)]">{note}</p>
                ) : null}
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
