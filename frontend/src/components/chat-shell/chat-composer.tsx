"use client";

import { useCallback, useState, type FormEvent, type KeyboardEvent } from "react";

type Props = {
  disabled?: boolean;
  placeholder?: string;
  onSend: (text: string) => void;
};

/**
 * Bottom input bar (Chatbot UI–style). Wired to parent; no API calls in the shell.
 */
export function ChatComposer({
  disabled = false,
  placeholder = "Describe your analysis goal…",
  onSend,
}: Props) {
  const [value, setValue] = useState("");

  const submit = useCallback(() => {
    const t = value.trim();
    if (!t || disabled) return;
    onSend(t);
    setValue("");
  }, [value, disabled, onSend]);

  const onSubmitForm = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form
      onSubmit={onSubmitForm}
      className="border-t border-[var(--border)] bg-[var(--background)] px-3 py-3 md:px-6"
    >
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
      <p className="mx-auto mt-2 max-w-4xl text-center text-[10px] text-[var(--muted)]">
        Shell only — messages are local until connected to the EDGAR run API.
      </p>
    </form>
  );
}
