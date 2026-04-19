"use client";

import Link from "next/link";

import { CaveatBadgeGroup, ConfidenceStrip, FindingCards, TopFindingsList } from "@/components/structured-answer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/ui/technical";
import { formatDate, shortId } from "@/lib/format";
import type { AnalysisRunStatus } from "@/lib/api/types";
import { contextReliabilityFootnote } from "@/lib/primary-answer-signals";
import type { ChatAnswerCardView } from "@/lib/run-primary-view";

type Props = {
  answerCard: ChatAnswerCardView;
  runId?: string;
  runHref?: string;
  runStatus?: AnalysisRunStatus;
  runCreatedAt?: string;
  runFinishedAt?: string | null;
};

export function ChatRunAnswerCard({
  answerCard,
  runId,
  runHref,
  runStatus,
  runCreatedAt,
  runFinishedAt,
}: Props) {
  const runTimestamp = formatDate(runFinishedAt ?? runCreatedAt);
  const hasFindings = answerCard.takeawayRows.length > 0 || answerCard.alignmentFindings.length > 0;
  const reliabilityNote = contextReliabilityFootnote(answerCard.contextSignals, answerCard.weakEvidenceSignals);

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
        <Separator />
        <section className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Top findings</p>
          {hasFindings ? (
            <div className="space-y-3">
              <TopFindingsList items={answerCard.takeawayRows} chipMode="secondary" />
              <FindingCards findings={answerCard.alignmentFindings} chipMode="secondary" />
            </div>
          ) : (
            <p className="text-sm leading-6 text-[var(--muted)]">
              No findings were surfaced for this run yet. Use the evidence links below for deeper verification.
            </p>
          )}
        </section>
        <Separator />
        <section className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Confidence & caveats
          </p>
          <ConfidenceStrip
            overallConfidence={answerCard.overallConfidence}
            criticPhaseStatus={answerCard.criticPhaseStatus}
            reportPhaseStatus={answerCard.reportPhaseStatus}
            reliabilityNote={reliabilityNote}
            className="mt-0 space-y-2"
          />
          <CaveatBadgeGroup
            blockingCaveats={answerCard.blockingCaveats}
            weakEvidenceSignals={answerCard.weakEvidenceSignals}
            contextSignals={answerCard.contextSignals}
            maxContextBadges={4}
            maxWeakBadges={3}
            overflowHref={answerCard.caveatOverflowHref ?? undefined}
            blockingHref={answerCard.conclusionRider?.href ?? answerCard.caveatOverflowHref ?? undefined}
            className="mt-0"
          />
        </section>
        <Separator />
        <section className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Open evidence</p>
          <div className="flex flex-wrap gap-2">
            {answerCard.navigationItems.map((item) => (
              <Link
                key={item.key}
                href={item.href}
                className="inline-flex items-center rounded-full border border-[var(--border)] bg-neutral-50 px-2.5 py-1 text-[11px] font-medium text-[var(--foreground)] transition-colors hover:border-[var(--foreground)]/30 hover:bg-[var(--background)] dark:bg-neutral-950/30"
              >
                {item.label}
              </Link>
            ))}
          </div>
          {answerCard.evidenceProvenanceHint ? (
            <p className="text-[11px] leading-5 text-[var(--muted)]">{answerCard.evidenceProvenanceHint}</p>
          ) : null}
        </section>
        {runId && runHref && runStatus ? (
          <>
            <Separator />
            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--border)]/70 bg-neutral-50/60 px-3 py-3 dark:bg-neutral-950/30">
              <StatusBadge status={runStatus} variant="friendly" />
              <span className="text-xs text-[var(--muted)]">{runTimestamp}</span>
              <span className="font-mono text-xs text-[var(--muted)]">{shortId(runId)}</span>
              <Button asChild size="sm" className="ml-auto">
                <Link href={runHref}>Open run</Link>
              </Button>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
