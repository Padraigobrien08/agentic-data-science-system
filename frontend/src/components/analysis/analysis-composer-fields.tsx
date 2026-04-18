"use client";

import { useCallback, useMemo, useState } from "react";

import {
  ANALYSIS_EXAMPLES,
  GOAL_SNIPPETS,
  parseTickerString,
  type AnalysisExample,
} from "@/lib/analysis-examples";

type Variant = "landing" | "project";

type Props = {
  variant?: Variant;
  /** For labels / ids when multiple composers could exist */
  idPrefix?: string;
};

const GOAL_PLACEHOLDER =
  "Ask in plain language — e.g. whether margin pressure is temporary or structural, which company is weaker, or what looks anomalous in recent quarters.";

function addToGoal(prev: string, fragment: string): string {
  const t = fragment.trim();
  if (!t) return prev;
  if (!prev.trim()) return t;
  const joiner = prev.endsWith("\n") || prev.endsWith(".") ? " " : ". ";
  return `${prev.trimEnd()}${joiner}${t}`;
}

export function AnalysisComposerFields({ variant = "landing", idPrefix = "analysis" }: Props) {
  const [goal, setGoal] = useState("");
  const [tickers, setTickers] = useState<string[]>([]);
  const [tickerDraft, setTickerDraft] = useState("");

  const tickersSerialized = useMemo(() => tickers.join(","), [tickers]);

  const addTicker = useCallback((raw: string) => {
    const parts = parseTickerString(raw);
    if (!parts.length) return;
    setTickers((prev) => {
      const next = [...prev];
      for (const p of parts) {
        if (!next.includes(p)) next.push(p);
      }
      return next;
    });
    setTickerDraft("");
  }, []);

  const removeTicker = useCallback((t: string) => {
    setTickers((prev) => prev.filter((x) => x !== t));
  }, []);

  const applyExample = useCallback((ex: AnalysisExample) => {
    setGoal(ex.goal);
    setTickers(parseTickerString(ex.tickers));
    setTickerDraft("");
  }, []);

  const goalId = `${idPrefix}-goal`;
  const hintsOpen = variant === "landing";

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <label htmlFor={goalId} className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          {variant === "landing" ? "Your question" : "Analysis goal"}
        </label>
        <textarea
          id={goalId}
          name="goal"
          required
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={variant === "landing" ? 5 : 4}
          className="w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--background)] px-3.5 py-3 text-sm leading-relaxed text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-neutral-400/80 dark:focus:ring-neutral-600"
          placeholder={GOAL_PLACEHOLDER}
          autoComplete="off"
        />
        <input type="hidden" name="tickers" value={tickersSerialized} aria-hidden />
      </div>

      <div className="space-y-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Tickers</span>
        <div className="flex min-h-[2.75rem] flex-wrap items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--background)] px-2 py-1.5 focus-within:ring-2 focus-within:ring-neutral-400/80 dark:focus-within:ring-neutral-600">
          {tickers.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => removeTicker(t)}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-neutral-100 px-2.5 py-0.5 font-mono text-xs font-medium text-[var(--foreground)] transition-colors hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700"
              title={`Remove ${t}`}
            >
              <span className="text-[var(--muted)]">×</span>
              {t}
            </button>
          ))}
          <input
            type="text"
            value={tickerDraft}
            onChange={(e) => setTickerDraft(e.target.value.toUpperCase())}
            onBlur={() => {
              if (tickerDraft.trim()) addTicker(tickerDraft);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === ",") {
                e.preventDefault();
                addTicker(tickerDraft);
              }
              if (e.key === "Backspace" && !tickerDraft && tickers.length > 0) {
                removeTicker(tickers[tickers.length - 1]!);
              }
            }}
            onPaste={(e) => {
              const text = e.clipboardData.getData("text");
              if (/[,\n]/.test(text)) {
                e.preventDefault();
                addTicker(text);
              }
            }}
            className="min-w-[7rem] flex-1 border-0 bg-transparent py-1 font-mono text-sm uppercase text-[var(--foreground)] outline-none placeholder:text-[var(--muted)]"
            placeholder={tickers.length ? "Add symbol…" : "e.g. AAPL — Enter or comma"}
            autoComplete="off"
            aria-label="Add ticker symbol"
          />
        </div>
        <p className="text-[11px] leading-snug text-[var(--muted)]">
          Symbols for SEC company panels. Paste a comma-separated list or type a symbol and press{" "}
          <kbd className="rounded border border-[var(--border)] px-1 font-mono text-[10px]">Enter</kbd>.
        </p>
      </div>

      <details
        className="rounded-xl border border-[var(--border)] bg-neutral-50/40 px-3 py-2 dark:bg-neutral-950/25"
        open={hintsOpen}
      >
        <summary className="cursor-pointer text-xs font-semibold text-[var(--foreground)]">
          Strong goals for this planner
        </summary>
        <p className="mt-2 text-[11px] leading-snug text-[var(--muted)]">
          The pipeline resolves intent, picks tools, and builds panels from your text. Goals that name{" "}
          <strong className="font-medium text-[var(--foreground)]">metrics</strong>,{" "}
          <strong className="font-medium text-[var(--foreground)]">time horizon</strong>,{" "}
          <strong className="font-medium text-[var(--foreground)]">peers or relative comparisons</strong>, and{" "}
          <strong className="font-medium text-[var(--foreground)]">what to down-rank</strong> (noise, one-offs) tend to
          produce sharper runs. Phrasing like <em>whether margin pressure is temporary or structural</em> or{" "}
          <em>which company is weaker</em> now maps cleanly onto the supported deterministic routes.
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {GOAL_SNIPPETS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setGoal((g) => addToGoal(g, s.append))}
              className="rounded-full border border-dashed border-[var(--border)] bg-[var(--background)] px-2.5 py-1 text-[10px] font-medium text-[var(--foreground)] transition-colors hover:border-[var(--foreground)]/30 hover:bg-neutral-50 dark:hover:bg-neutral-900"
              title={s.append}
            >
              {s.label}
            </button>
          ))}
        </div>
      </details>

      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">Example goals</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {ANALYSIS_EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => applyExample(ex)}
              className="rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 text-left text-xs text-[var(--foreground)] transition-colors hover:border-neutral-400 hover:bg-neutral-50 dark:hover:border-neutral-600 dark:hover:bg-neutral-900/60"
            >
              <span className="font-medium">{ex.label}</span>
              <span className="mt-1 block line-clamp-2 text-[var(--muted)]">{ex.goal}</span>
              <span className="mt-1 font-mono text-[10px] text-[var(--muted)]">{ex.tickers}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
