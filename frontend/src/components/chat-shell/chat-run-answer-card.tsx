"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { CompactChatAnswerView } from "@/lib/run-primary-view";

type Props = {
  answerCard: CompactChatAnswerView;
};

export function ChatRunAnswerCard({ answerCard }: Props) {
  return (
    <Card className="w-full max-w-[min(100%,42rem)] rounded-2xl rounded-bl-md bg-[var(--background)] shadow-none">
      <CardHeader className="gap-1 pb-4">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Conclusion
        </p>
        <p className="text-base font-semibold tracking-[-0.02em] text-[var(--foreground)]">
          {answerCard.summaryLine ?? "Run completed without a summary line."}
        </p>
        {answerCard.conclusionRider ? (
          <p className="text-xs leading-5 text-[var(--muted)]">{answerCard.conclusionRider.text}</p>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        <Separator />
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Goal</p>
          <p className="text-sm leading-6 text-[var(--foreground)]">{answerCard.goalDisplay}</p>
        </div>
        {answerCard.orchestrationStatus ? (
          <>
            <Separator />
            <details className="group rounded-2xl border border-[var(--border)]/70 bg-neutral-50/60 px-3 py-2 dark:bg-neutral-950/30">
              <summary className="cursor-pointer list-none text-[11px] font-medium text-[var(--muted)]">
                Orchestration status (technical)
              </summary>
              <p className="mt-2 text-sm text-[var(--foreground)]">{answerCard.orchestrationStatus}</p>
            </details>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
