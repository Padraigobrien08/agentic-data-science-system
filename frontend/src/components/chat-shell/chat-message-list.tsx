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
    return message.deliveryDetail ?? "Background delivery is degraded in this chat.";
  }
  if (message.deliveryMode === "sync_only") {
    return message.deliveryDetail ?? "This chat is currently running requests synchronously.";
  }
  return message.deliveryDetail ?? null;
}

function SystemStrip({ content }: { content: string }) {
  return (
    <div className="mx-auto max-w-[40rem] rounded-full border border-[var(--border)] bg-[var(--chat-rail)] px-4 py-2 text-center text-[11px] text-[var(--muted)]">
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
      className="scrollbar-hidden flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-4 py-4 md:px-6 md:py-5 lg:px-10"
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
                    <div className="max-w-[min(100%,44rem)] rounded-[1.4rem] rounded-tr-[0.8rem] border border-[var(--border)] bg-[var(--chat-user)] px-5 py-4 text-sm">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
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
            <article
              key={m.id}
              id={m.runId ? `answer-${m.runId}` : undefined}
              className="scroll-mt-24 flex w-full justify-center"
            >
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
                  <div className="mx-auto max-w-[52rem] whitespace-pre-wrap rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface)] px-5 py-4 text-[15px] leading-7 text-[var(--foreground)]">
                    {m.content}
                  </div>
                )}
                {m.routingReason ? (
                  <div className="mx-auto mt-3 max-w-[52rem] rounded-2xl border border-[var(--border)] bg-[var(--chat-rail)] px-4 py-3 text-[12.5px] leading-6 text-[var(--muted)]">
                    {m.routingReason}
                  </div>
                ) : null}
                {m.rewriteSuggestions?.length ? (
                  <div className="mx-auto mt-3 max-w-[52rem] rounded-2xl border border-[var(--border)] bg-[var(--chat-rail)] px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
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
