"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Search } from "lucide-react";

export type PaletteCommand = {
  id: string;
  /** Row label; also the primary match target. */
  label: string;
  /** Right-aligned meta (tickers, shortcut hint). Also matched when filtering. */
  hint?: string;
  /** Heading this row sits under. Rows render in the order groups first appear. */
  group: string;
  disabled?: boolean;
  run: () => void;
};

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: PaletteCommand[];
};

function matches(command: PaletteCommand, query: string): boolean {
  if (!query) return true;
  const q = query.toLowerCase();
  return (
    command.label.toLowerCase().includes(q) ||
    command.group.toLowerCase().includes(q) ||
    (command.hint?.toLowerCase().includes(q) ?? false)
  );
}

/**
 * Keyboard-first launcher over chats, starter prompts, and shell actions.
 *
 * Uses the native `<dialog>` in modal mode so focus trapping, Escape, and top-layer
 * stacking come from the platform rather than a bespoke implementation — the palette
 * has to escape the sidebar's scroll container, where `position: absolute` would clip.
 */
export function CommandPalette({ open, onOpenChange, commands }: Props) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const visible = useMemo(() => commands.filter((c) => matches(c, query)), [commands, query]);

  // Group headings in first-appearance order, so callers control section order.
  const groups = useMemo(() => {
    const order: string[] = [];
    for (const c of visible) if (!order.includes(c.group)) order.push(c.group);
    return order;
  }, [visible]);

  const close = useCallback(() => onOpenChange(false), [onOpenChange]);

  // Drive the native dialog from `open`, and sync state back when the platform closes
  // it (Escape / backdrop click) so the two never disagree.
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) {
      setQuery("");
      setActiveIndex(0);
      el.showModal();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    const onClose = () => onOpenChange(false);
    el.addEventListener("close", onClose);
    el.addEventListener("cancel", onClose);
    return () => {
      el.removeEventListener("close", onClose);
      el.removeEventListener("cancel", onClose);
    };
  }, [onOpenChange]);

  // Keep the highlighted row in range as the filter narrows, and in view as it moves.
  useEffect(() => {
    setActiveIndex((i) => (visible.length === 0 ? 0 : Math.min(i, visible.length - 1)));
  }, [visible.length]);

  useEffect(() => {
    const row = listRef.current?.querySelector<HTMLElement>(`[data-index="${activeIndex}"]`);
    // Optional call: not implemented in jsdom, and non-essential to correctness.
    row?.scrollIntoView?.({ block: "nearest" });
  }, [activeIndex]);

  const runIndex = useCallback(
    (index: number) => {
      const command = visible[index];
      if (!command || command.disabled) return;
      close();
      command.run();
    },
    [visible, close],
  );

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => (visible.length ? (i + 1) % visible.length : 0));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => (visible.length ? (i - 1 + visible.length) % visible.length : 0));
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      setActiveIndex(0);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      setActiveIndex(Math.max(0, visible.length - 1));
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      runIndex(activeIndex);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      aria-label="Command palette"
      className="m-0 max-h-none max-w-none bg-transparent p-0 backdrop:bg-[rgba(9,9,11,0.45)] open:animate-in open:fade-in-0 motion-reduce:open:animate-none"
      onClick={(event) => {
        // A click landing on the dialog itself is the backdrop area; dismiss.
        if (event.target === dialogRef.current) close();
      }}
    >
      {/* Rendered only while open: a closed dialog's subtree would otherwise sit in the
          DOM, duplicating every chat title and prompt label for no benefit. */}
      {open ? (
        <div
          onKeyDown={onKeyDown}
          className="fixed left-1/2 top-[12vh] w-[min(92vw,34rem)] -translate-x-1/2 overflow-hidden rounded-card border border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)] shadow-[0_24px_80px_rgba(0,0,0,0.24)]"
        >
          <div className="flex items-center gap-2.5 border-b border-[var(--border)] px-4 py-3">
            <Search className="h-4 w-4 shrink-0 text-[var(--muted)]" aria-hidden="true" />
            {/* eslint-disable-next-line jsx-a11y/no-autofocus -- focus belongs in the search field when a palette opens */}
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search chats, prompts, actions…"
              aria-label="Search chats, prompts, and actions"
              role="combobox"
              aria-expanded
              aria-controls="command-palette-list"
              aria-activedescendant={
                visible.length ? `command-palette-option-${activeIndex}` : undefined
              }
              className="min-w-0 flex-1 bg-transparent text-[15px] leading-6 outline-none placeholder:text-[var(--muted)]"
            />
          </div>

          <ul
            ref={listRef}
            id="command-palette-list"
            role="listbox"
            aria-label="Results"
            className="scrollbar-hidden max-h-[min(60vh,26rem)] overflow-y-auto p-2"
          >
            {visible.length === 0 ? (
              <li className="px-2 py-6 text-center text-[13px] text-[var(--muted)]">
                Nothing matches &ldquo;{query}&rdquo;.
              </li>
            ) : (
              groups.map((group) => (
                <li key={group}>
                  <p className="px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                    {group}
                  </p>
                  <ul role="presentation">
                    {visible.map((command, index) =>
                      command.group === group ? (
                        <li
                          key={command.id}
                          id={`command-palette-option-${index}`}
                          data-index={index}
                          role="option"
                          aria-selected={index === activeIndex}
                          aria-disabled={command.disabled || undefined}
                        >
                          <button
                            type="button"
                            tabIndex={-1}
                            disabled={command.disabled}
                            onMouseMove={() => setActiveIndex(index)}
                            onClick={() => runIndex(index)}
                            className={`flex w-full items-center justify-between gap-3 rounded-control px-2.5 py-2 text-left text-[13.5px] leading-6 transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${
                              index === activeIndex ? "bg-[var(--chat-hover)]" : ""
                            }`}
                          >
                            <span className="min-w-0 truncate">{command.label}</span>
                            {command.hint ? (
                              <span className="shrink-0 font-mono text-[11px] text-[var(--muted)]">
                                {command.hint}
                              </span>
                            ) : null}
                          </button>
                        </li>
                      ) : null,
                    )}
                  </ul>
                </li>
              ))
            )}
          </ul>

          <div className="flex items-center justify-between border-t border-[var(--border)] px-4 py-2 text-[11px] text-[var(--muted)]">
            <span>↑↓ to move · ↵ to select</span>
            <span>esc to close</span>
          </div>
        </div>
      ) : null}
    </dialog>
  );
}
