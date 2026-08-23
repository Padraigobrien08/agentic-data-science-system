"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

import { ANALYSIS_EXAMPLES } from "@/lib/analysis-examples";
import { ChatRecordedAnswer } from "./chat-recorded-answer";
import { ChatRunAnswerCard } from "./chat-run-answer-card";
import { ChatRunProgress } from "./chat-run-progress";
import type { ChatMessage } from "./types";

const FIRST_RUN_HELP_KEY = "edgar-chat-firstrun-help-dismissed";

/**
 * One-time, dismissable explainer of the ask → confidence → verify loop. Shown
 * only on first visit (persisted per-browser), so it teaches without nagging.
 */
function FirstRunHint() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      setShow(window.localStorage.getItem(FIRST_RUN_HELP_KEY) !== "1");
    } catch {
      setShow(true);
    }
  }, []);

  if (!show) return null;

  const dismiss = () => {
    try {
      window.localStorage.setItem(FIRST_RUN_HELP_KEY, "1");
    } catch {
      /* private mode: hide for this session only */
    }
    setShow(false);
  };

  return (
    <div className="relative mx-auto w-full max-w-2xl rounded-card border border-[var(--border)] bg-[var(--chat-rail)] px-4 py-3 pr-10 text-left">
      <p className="text-[12px] font-semibold text-[var(--foreground)]">How this works</p>
      <p className="mt-1 text-[12.5px] leading-5 text-[var(--muted)]">
        Ask about a company&rsquo;s filings in plain language. A deterministic pipeline runs against
        SEC data and returns an answer with a confidence read and evidence you can open and verify.
      </p>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss how this works"
        className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-control text-[var(--chat-faint)] transition-colors hover:bg-[var(--chat-hover)] hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

type Props = {
  messages: ChatMessage[];
  onPickPrompt?: (goal: string) => void;
  onStop?: () => void;
  /**
   * Docks a trace beside the conversation. The key identifies which one: a live answer is
   * keyed by its run, a recorded answer by its message — the replay tier has exactly one
   * trace, so the id only has to be stable, not resolvable.
   *
   * Absent = this surface cannot dock, and no control is offered.
   */
  onInspectTrace?: (key: string) => void;
  /** The trace currently docked, so its control reads as pressed. */
  openTraceKey?: string | null;
};

function EmptyState({ onPickPrompt }: { onPickPrompt?: (goal: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-7 px-4 py-12 text-center">
      <div className="space-y-2.5">
        <h2 className="text-2xl font-semibold leading-tight tracking-[-0.02em] text-[var(--foreground)] sm:text-[1.7rem]">
          Ask a question about a company&rsquo;s filings
        </h2>
        <p className="mx-auto max-w-md text-sm leading-6 text-[var(--muted)]">
          Deterministic SEC analysis with traceable evidence. Pick a starting point, or type your own below.
        </p>
      </div>
      {onPickPrompt ? (
        <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-2">
          {ANALYSIS_EXAMPLES.map((example) => (
            <button
              key={example.label}
              type="button"
              onClick={() => onPickPrompt(example.goal)}
              className="group rounded-card border border-[var(--border)] bg-[var(--surface)] p-4 text-left transition hover:-translate-y-0.5 hover:border-[var(--accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] motion-reduce:transition-none motion-reduce:hover:translate-y-0"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-[12px] font-semibold text-[var(--foreground)]">
                  {example.label}
                </p>
                <span className="font-mono text-[11px] text-[var(--accent)]">{example.tickers}</span>
              </div>
              <p className="mt-2 line-clamp-3 text-[13.5px] leading-6 text-[var(--foreground)]">{example.goal}</p>
            </button>
          ))}
        </div>
      ) : null}
      <FirstRunHint />
    </div>
  );
}

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
export function ChatMessageList({
  messages,
  onPickPrompt,
  onStop,
  onInspectTrace,
  openTraceKey,
}: Props) {
  return (
    <div
      className="scrollbar-hidden flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-4 py-4 md:px-6 md:py-5 lg:px-10"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
    >
      {messages.length === 0 ? (
        <EmptyState onPickPrompt={onPickPrompt} />
      ) : (
        messages.map((m) => {
          if (m.role === "user") {
            return (
              <article key={m.id} className="flex w-full justify-center">
                <div className="w-full max-w-[76rem]">
                  <div className="flex justify-end">
                    <div className="max-w-[min(100%,44rem)] whitespace-pre-wrap break-words rounded-card border border-[var(--border)] bg-[var(--chat-user)] px-4 py-3 text-[15px] leading-7 text-[var(--foreground)]">
                      {m.content}
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
          // A live answer is keyed by its run; a recorded one by its message, since the
          // replay tier holds a single trace and only needs a stable handle for it.
          const traceKey = onInspectTrace ? (m.runId ?? (m.recordedAnswer ? m.id : null)) : null;
          return (
            <article
              key={m.id}
              id={m.runId ? `answer-${m.runId}` : undefined}
              className="scroll-mt-24 flex w-full justify-center"
            >
              <div className="w-full max-w-[76rem]">
                {m.pending ? (
                  <ChatRunProgress view={m.phaseView} onStop={onStop} />
                ) : m.recordedAnswer ? (
                  <ChatRecordedAnswer answer={m.recordedAnswer} />
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
                  <div className="mx-auto max-w-[52rem] whitespace-pre-wrap break-words rounded-card border border-[var(--border)] bg-[var(--surface)] px-5 py-4 text-[15px] leading-7 text-[var(--foreground)]">
                    {m.content}
                  </div>
                )}
                {m.routingReason ? (
                  <div className="mx-auto mt-3 max-w-[52rem] rounded-card border border-[var(--border)] bg-[var(--chat-rail)] px-4 py-3 text-[12.5px] leading-6 text-[var(--muted)]">
                    {m.routingReason}
                  </div>
                ) : null}
                {m.rewriteSuggestions?.length ? (
                  <div className="mx-auto mt-3 max-w-[52rem] rounded-card border border-[var(--border)] bg-[var(--chat-rail)] px-4 py-3">
                    <p className="text-[12px] font-semibold text-[var(--foreground)]">
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
                {/* Docks the trace rather than navigating: the answer and the reason for it
                    are worth reading side by side. The card's own nav keeps the full page.
                    Hidden below `lg`, where there is no room to dock into and the control
                    would do nothing when pressed. */}
                {traceKey && !m.pending ? (
                  <div className="mx-auto mt-3 hidden max-w-[52rem] lg:block">
                    <button
                      type="button"
                      onClick={() => onInspectTrace?.(traceKey)}
                      aria-pressed={openTraceKey === traceKey}
                      className="rounded-control border border-[var(--border)] px-2.5 py-1.5 font-mono text-[11px] text-[var(--muted)] transition-colors hover:text-[var(--foreground)] aria-pressed:border-[var(--accent)] aria-pressed:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    >
                      {openTraceKey === traceKey ? "hide trace" : "inspect trace"}
                    </button>
                  </div>
                ) : null}
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
