"use client";

import { ChevronDown } from "lucide-react";

import type { ConfidenceStripProps } from "./types";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

function toneClasses(tone: ConfidenceStripProps["confidenceExplainer"]["tone"]): string {
  switch (tone) {
    case "good":
      return "border-[color:var(--status-success-border)] bg-[var(--status-success-bg)] text-[color:var(--status-success-ink)] hover:border-[color:var(--status-success-ink)]";
    case "medium":
      return "border-[color:var(--status-warning-border)] bg-[var(--status-warning-bg)] text-[color:var(--status-warning-ink)] hover:border-[color:var(--status-warning-ink)]";
    case "bad":
      return "border-[color:var(--status-danger-border)] bg-[var(--status-danger-bg)] text-[color:var(--status-danger-ink)] hover:border-[color:var(--status-danger-ink)]";
    default:
      return "border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)] hover:border-[var(--foreground)]/20";
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
      <p className="text-[12px] font-semibold text-[var(--foreground)]">{title}</p>
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
              "inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[12px] font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]",
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
              <p className="text-[11px] font-medium text-[var(--muted)]">Evidence strength</p>
              <p className="text-sm font-medium text-[var(--foreground)]">{confidenceExplainer.label}</p>
            </div>

            <ExplainerSection title="What supports this" items={confidenceExplainer.supports} />
            <ExplainerSection title="What weakens this" items={confidenceExplainer.weakens} />
            <ExplainerSection title="Coverage limits" items={confidenceExplainer.limits} />

            {reliabilityNote ? (
              <p className="rounded-control border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[12px] leading-5 text-[var(--muted)]">
                {reliabilityNote}
              </p>
            ) : null}
          </PopoverContent>
        ) : null}
      </Popover>
    </div>
  );
}
