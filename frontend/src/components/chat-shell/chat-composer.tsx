"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";

type Props = {
  disabled?: boolean;
  placeholder?: string;
  tickers: string[];
  error?: string;
  action: (payload: FormData) => void;
};

/**
 * Bottom input bar (Chatbot UI–style). Submits a server action that creates a run.
 */
export function ChatComposer({
  disabled = false,
  placeholder = "Describe your analysis goal…",
  tickers,
  error,
  action,
}: Props) {
  const [value, setValue] = useState("");
  const formRef = useRef<HTMLFormElement | null>(null);

  const submit = useCallback(() => {
    const t = value.trim();
    if (!t || disabled) return;
    formRef.current?.requestSubmit();
  }, [value, disabled]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  // If the action redirects on success, this never runs; but if it returns an error, keep the text.
  useEffect(() => {
    if (!error) return;
  }, [error]);

  return (
    <form
      ref={formRef}
      action={action}
      className="border-t border-[var(--border)] bg-[var(--background)] px-3 py-3 md:px-6"
    >
      <input type="hidden" name="tickers" value={tickers.join(",")} />
      <input type="hidden" name="goal" value={value} />
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
