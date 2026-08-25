"use client";

import {
  useCallback,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MutableRefObject,
  type ReactNode,
  type Ref,
} from "react";
import { ArrowUp, Lock } from "lucide-react";

import type { ChatBackgroundDelivery } from "./types";

const MAX_COMPOSER_HEIGHT = 176; // px — ~7 lines, matches max-h-44

/**
 * Why this composer cannot send — shown rather than implied.
 *
 * A composer that is simply gone reads as a surface that does not have one. Present and
 * locked reads as a surface that has one *here and now*, which is the true statement on the
 * replay tier and the one worth making.
 */
export type ComposerLock = {
  /** One line, used as the placeholder — the version nobody has to hover to find. */
  short: string;
  /** The full explanation, on hover or keyboard focus. */
  detail: ReactNode;
};

type Props = {
  disabled?: boolean;
  placeholder?: string;
  /** Present + locked. Implies `disabled`. */
  lock?: ComposerLock;
  backgroundDelivery: ChatBackgroundDelivery;
  error?: string;
  onSend?: (text: string, requestId: string) => void;
  /** Optional controlled value so a starter prompt can prefill the box. */
  value?: string;
  onValueChange?: (value: string) => void;
  inputRef?: Ref<HTMLTextAreaElement>;
};

/**
 * Bottom input bar. Submits imperatively via `onSend`; the ChatShell orchestrates
 * start → poll progress → finalize (no single-shot form action).
 */
export function ChatComposer({
  disabled = false,
  placeholder = "Describe your analysis goal…",
  lock,
  backgroundDelivery,
  error,
  onSend,
  value: controlledValue,
  onValueChange,
  inputRef,
}: Props) {
  const [internalValue, setInternalValue] = useState("");
  const value = controlledValue ?? internalValue;
  const setValue = onValueChange ?? setInternalValue;
  const [lockOpen, setLockOpen] = useState(false);
  const lockId = useId();
  const isLocked = !!lock;
  const isDisabled = disabled || isLocked;

  const taRef = useRef<HTMLTextAreaElement | null>(null);
  const setRefs = useCallback(
    (el: HTMLTextAreaElement | null) => {
      taRef.current = el;
      if (typeof inputRef === "function") inputRef(el);
      else if (inputRef) (inputRef as MutableRefObject<HTMLTextAreaElement | null>).current = el;
    },
    [inputRef],
  );

  // Grow the box to fit the message (up to a cap), then scroll.
  useLayoutEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_COMPOSER_HEIGHT)}px`;
  }, [value]);

  const submit = useCallback(() => {
    const t = value.trim();
    if (!t || isDisabled) return;
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `rq-${Date.now()}`;
    setValue("");
    onSend?.(t, id);
  }, [value, isDisabled, onSend, setValue]);

  // Only surface the banner when delivery is degraded — a healthy or sync-only
  // state is the expected case and doesn't need a persistent notice.
  const showStatusBanner = backgroundDelivery.delivery_mode === "background_degraded";
  const statusDetail =
    backgroundDelivery.detail ??
    "Runs still complete, but queued background delivery is unavailable — requests execute immediately in this conversation.";

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="bg-[var(--background)] px-3 pt-2 md:px-6"
      style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
    >
      {showStatusBanner ? (
        <div
          role="status"
          className="mx-auto mb-2 max-w-3xl rounded-control border border-[color:var(--status-warning-border)] bg-[var(--status-warning-bg)] px-3 py-2 text-xs text-[color:var(--status-warning-ink)]"
        >
          <p className="font-semibold">Background delivery degraded</p>
          <p className="mt-1 leading-5">{statusDetail}</p>
        </div>
      ) : null}
      {/* The wrapper, not the textarea, carries the hover handlers: a disabled control
          fires no mouse events, so a tooltip bound to it would never open. */}
      <div
        className="relative mx-auto max-w-3xl"
        onMouseEnter={isLocked ? () => setLockOpen(true) : undefined}
        onMouseLeave={isLocked ? () => setLockOpen(false) : undefined}
        onFocusCapture={isLocked ? () => setLockOpen(true) : undefined}
        onBlurCapture={isLocked ? () => setLockOpen(false) : undefined}
      >
        {lock && lockOpen ? (
          <div
            role="tooltip"
            id={lockId}
            className="absolute bottom-full left-0 right-0 z-20 mb-2 rounded-card border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-[12.5px] leading-5 text-[var(--muted)] shadow-[0_16px_48px_rgba(0,0,0,0.28)]"
          >
            {lock.detail}
          </div>
        ) : null}
        <div className="flex items-end gap-2 rounded-card border border-[var(--border)] bg-[var(--chat-raise)] p-2 pl-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-colors focus-within:border-[var(--muted)]">
          <textarea
            ref={setRefs}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={isDisabled}
            rows={1}
            className="scrollbar-hidden min-h-[2.25rem] flex-1 resize-none overflow-y-auto bg-transparent py-1.5 text-[15px] leading-6 outline-none placeholder:text-[var(--muted)] disabled:cursor-not-allowed"
            placeholder={lock?.short ?? placeholder}
            aria-label="Message input"
            aria-describedby={lock ? lockId : undefined}
          />
          <button
            type={isLocked ? "button" : "submit"}
            // Locked stays focusable, marked `aria-disabled`: a real `disabled` button drops
            // out of tab order, which would leave the reason reachable only by hovering.
            disabled={isLocked ? undefined : isDisabled || !value.trim()}
            aria-disabled={isLocked || undefined}
            aria-label={isLocked ? "Sending is unavailable" : "Send"}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--chat-primary)] text-[var(--chat-primary-ink)] transition-[opacity,transform] duration-150 hover:opacity-90 active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:opacity-30 disabled:hover:opacity-30 disabled:active:scale-100 aria-disabled:cursor-not-allowed aria-disabled:opacity-30 aria-disabled:hover:opacity-30 aria-disabled:active:scale-100 motion-reduce:transition-none motion-reduce:active:scale-100"
          >
            {isLocked ? <Lock className="h-3.5 w-3.5" /> : <ArrowUp className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {error ? (
        <p className="mx-auto mt-2 max-w-3xl text-center font-mono text-[11px] text-[color:var(--status-danger-ink)]">
          {error}
        </p>
      ) : null}
    </form>
  );
}
