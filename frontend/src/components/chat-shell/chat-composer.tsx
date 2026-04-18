"use client";

import { useCallback, useRef, useState, type KeyboardEvent } from "react";

import type { ChatBackgroundDelivery } from "./types";

type Props = {
  disabled?: boolean;
  placeholder?: string;
  tickers: string[];
  backgroundDelivery: ChatBackgroundDelivery;
  error?: string;
  action: (payload: FormData) => void;
  onSend?: (text: string, requestId: string) => void;
};

/**
 * Bottom input bar (Chatbot UI–style). Submits a server action that creates a run.
 */
export function ChatComposer({
  disabled = false,
  placeholder = "Describe your analysis goal…",
  tickers,
  backgroundDelivery,
  error,
  action,
  onSend,
}: Props) {
  const [value, setValue] = useState("");
  const [refresh, setRefresh] = useState(false);
  const [requestId, setRequestId] = useState("");
  const formRef = useRef<HTMLFormElement | null>(null);
  const requestIdRef = useRef<HTMLInputElement | null>(null);

  const submit = useCallback(() => {
    const t = value.trim();
    if (!t || disabled) return;
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `rq-${Date.now()}`;
    setRequestId(id);
    if (requestIdRef.current) {
      requestIdRef.current.value = id;
    }
    onSend?.(t, id);
    formRef.current?.requestSubmit();
  }, [value, disabled, onSend]);

  const statusTitle =
    backgroundDelivery.delivery_mode === "background_ready"
      ? "Background delivery ready"
      : backgroundDelivery.delivery_mode === "background_degraded"
        ? "Background delivery degraded"
        : "Sync only";
  const statusDetail =
    backgroundDelivery.detail ??
    (backgroundDelivery.background_available
      ? "Queued background delivery is healthy."
      : "Chat requests execute immediately in this workspace.");
  const statusTone =
    backgroundDelivery.delivery_mode === "background_ready"
      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
      : backgroundDelivery.delivery_mode === "background_degraded"
        ? "border-amber-200 bg-amber-50 text-amber-900"
        : "border-blue-200 bg-blue-50 text-blue-900";

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form
      ref={formRef}
      action={action}
      className="border-t border-[var(--border)] bg-[var(--background)] px-3 py-3 md:px-6"
    >
      <input type="hidden" name="tickers" value={tickers.join(",")} />
      <input type="hidden" name="goal" value={value} />
      <input ref={requestIdRef} type="hidden" name="request_id" value={requestId} readOnly />
      <input type="hidden" name="refresh" value={refresh ? "on" : "off"} />
      <input type="hidden" name="execute_now" value="on" />
      <input type="hidden" name="enqueue_execution" value="off" />
      <div className={`mx-auto mb-2 max-w-4xl rounded-xl border px-3 py-2 text-xs ${statusTone}`}>
        <p className="font-semibold uppercase tracking-[0.18em]">{statusTitle}</p>
        <p className="mt-1 leading-5">{statusDetail}</p>
      </div>
      <div className="mx-auto flex max-w-4xl gap-2 rounded-xl border border-[var(--border)] bg-neutral-50 p-2 dark:bg-neutral-950">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={1}
          className="max-h-40 min-h-[2.5rem] flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-[var(--muted)]"
          placeholder={placeholder}
          aria-label="Message input"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="self-end rounded-lg border border-[var(--border)] bg-[var(--background)] px-4 py-2 text-sm font-medium text-[var(--foreground)] disabled:opacity-40"
        >
          Send
        </button>
      </div>
      <div className="mx-auto mt-2 flex max-w-4xl flex-wrap items-center gap-3 text-xs text-[var(--muted)]">
        <label className="inline-flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={refresh}
            onChange={(e) => setRefresh(e.target.checked)}
            className="rounded border-[var(--border)]"
          />
          <span>Refresh SEC cache</span>
        </label>
        <span>Chat runs execute immediately in this phase.</span>
      </div>
      {error ? (
        <p className="mx-auto mt-2 max-w-4xl text-center font-mono text-[10px] text-red-700 dark:text-red-400">
          {error}
        </p>
      ) : (
        <p className="mx-auto mt-2 max-w-4xl text-center text-[10px] text-[var(--muted)]">
          Press Enter to submit · Shift+Enter for newline
        </p>
      )}
    </form>
  );
}
