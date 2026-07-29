"use client";

import type { ReactNode } from "react";
import { HelpCircle } from "lucide-react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

type Props = {
  /** Accessible name for the trigger, e.g. "What is scope?". */
  label: string;
  /** Short bold heading inside the popover. */
  title: string;
  children: ReactNode;
};

/**
 * A `?` affordance for point-of-use help. Reuses the shared Popover so it reads
 * as the same disclosure vocabulary as the confidence explainer.
 */
export function HelpHint({ label, title, children }: Props) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={label}
          className="inline-flex h-4 w-4 items-center justify-center rounded-full text-[var(--chat-faint)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        >
          <HelpCircle className="h-3.5 w-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 space-y-1.5">
        <p className="text-[12px] font-semibold text-[var(--foreground)]">{title}</p>
        <div className="text-[12.5px] leading-5 text-[var(--muted)]">{children}</div>
      </PopoverContent>
    </Popover>
  );
}
