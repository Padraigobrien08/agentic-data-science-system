"use client";

import { ChevronDown } from "lucide-react";

import type { ConfidenceStripProps } from "./types";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

function toneClasses(tone: ConfidenceStripProps["confidenceExplainer"]["tone"]): string {
  switch (tone) {
    case "good":
      return "border-emerald-300/80 bg-emerald-50 text-emerald-900 hover:border-emerald-400 dark:border-emerald-800 dark:bg-emerald-950/35 dark:text-emerald-100";
    case "medium":
      return "border-amber-300/80 bg-amber-50 text-amber-900 hover:border-amber-400 dark:border-amber-800 dark:bg-amber-950/35 dark:text-amber-100";
    case "bad":
      return "border-rose-300/80 bg-rose-50 text-rose-900 hover:border-rose-400 dark:border-rose-800 dark:bg-rose-950/35 dark:text-rose-100";
    default:
      return "border-[var(--border)] bg-neutral-50 text-[var(--foreground)] hover:border-[var(--foreground)]/20 dark:bg-neutral-950/35";
  }
}

function ExplainerSection({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">{title}</p>
      <ul className="space-y-2 text-[13px] leading-6 text-[var(--foreground)]">
        {items.map((item) => (
          <li key={`${title}-${item}`} className="flex gap-2">
            <span className="mt-[0.45rem] h-1.5 w-1.5 flex-none rounded-full bg-current/70" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Compact header disclosure for answer confidence and its grouped rationale. */
export function ConfidenceStrip({
  overallConfidence,
  confidenceExplainer,
  reliabilityNote,
  className,
}: ConfidenceStripProps) {
  const hasExplainer =
    confidenceExplainer.supports.length > 0 ||
    confidenceExplainer.weakens.length > 0 ||
    confidenceExplainer.limits.length > 0 ||
    Boolean(reliabilityNote);

  return (
    <div className={className}>
      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[12px] font-medium transition-colors",
              toneClasses(confidenceExplainer.tone),
            )}
            aria-label={`Evidence strength: ${confidenceExplainer.label}`}
          >
            <span className="text-[var(--foreground)]/75">Evidence strength:</span>
            <span className="font-semibold text-current">{confidenceExplainer.label}</span>
            <ChevronDown className="h-3.5 w-3.5 opacity-70" />
          </button>
        </PopoverTrigger>
        {hasExplainer ? (
          <PopoverContent align="end" className="space-y-4">
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
                Evidence strength
              </p>
              <p className="text-sm font-medium text-[var(--foreground)]">
                {confidenceExplainer.label}
                {overallConfidence ? (
                  <span className="ml-2 text-[11px] font-normal uppercase tracking-[0.18em] text-[var(--muted)]">
                    {overallConfidence}
                  </span>
                ) : null}
              </p>
            </div>

            <ExplainerSection title="What supports this" items={confidenceExplainer.supports} />
            <ExplainerSection title="What weakens this" items={confidenceExplainer.weakens} />
            <ExplainerSection title="Coverage limits" items={confidenceExplainer.limits} />

            {reliabilityNote ? (
              <p className="rounded-xl border border-[var(--border)]/70 bg-neutral-50/85 px-3 py-2 text-[12px] leading-5 text-[var(--muted)] dark:bg-neutral-950/35">
                {reliabilityNote}
              </p>
            ) : null}
          </PopoverContent>
        ) : null}
      </Popover>
    </div>
  );
}
