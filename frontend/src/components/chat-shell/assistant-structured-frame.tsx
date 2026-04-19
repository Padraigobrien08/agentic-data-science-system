"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

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
    <Card
      className="w-full max-w-[min(100%,42rem)] rounded-2xl rounded-bl-md bg-[var(--background)] shadow-none"
      data-message-id={messageId}
      data-assistant-slot="structured"
    >
      <CardHeader className="gap-1 pb-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Conclusion
          </p>
          {variant === "pending" ? (
            <span className="text-[10px] text-[var(--muted)]">Updating…</span>
          ) : null}
        </div>
        <p className="text-base font-semibold tracking-[-0.02em] text-[var(--foreground)]">
          {variant === "pending" ? "Running analysis..." : "Structured response pending"}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Separator />
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Goal</p>
          <Skeleton className="h-5 w-4/5" />
          <Skeleton className="h-5 w-3/5" />
        </div>
      </CardContent>
    </Card>
  );
}
