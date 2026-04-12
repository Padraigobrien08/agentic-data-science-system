"use client";

type Props = {
  messageId: string;
  /** Visual hint for empty vs waiting-for-blocks state. */
  variant?: "empty" | "pending";
};

/**
 * Placeholder for assistant structured output (report cards, run status, tables).
 * Deliberately not Chatbot UI-style markdown prose.
 */
export function AssistantStructuredFrame({ messageId, variant = "empty" }: Props) {
  return (
    <div
      className="w-full max-w-[min(100%,42rem)] rounded-2xl rounded-bl-md border border-dashed border-[var(--border)] bg-neutral-50/80 px-4 py-4 dark:bg-neutral-950/50"
      data-message-id={messageId}
      data-assistant-slot="structured"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Response
        </p>
        {variant === "pending" ? (
          <span className="text-[10px] text-[var(--muted)]">Updating…</span>
        ) : null}
      </div>
      <div className="mt-3 min-h-[4.5rem] rounded-md border border-[var(--border)]/60 bg-[var(--background)] p-3">
        <p className="text-xs text-[var(--muted)]">
          Structured blocks (run summary, evidence, actions) mount here — not plain assistant text.
        </p>
      </div>
    </div>
  );
}
