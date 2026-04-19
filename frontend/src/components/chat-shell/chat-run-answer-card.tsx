"use client";

import Link from "next/link";

import { CaveatBadgeGroup, ConfidenceStrip, FindingCards, TopFindingsList } from "@/components/structured-answer";
import { Separator } from "@/components/ui/separator";
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

const NARRATIVE_SECTION_ORDER = ["What's happening", "Why we think that", "What weakens the claim"] as const;

function sortNarrativeSections(answerCard: ChatAnswerCardView) {
  const priority: Record<string, number> = Object.fromEntries(
    NARRATIVE_SECTION_ORDER.map((heading, index) => [heading, index]),
  );
  return [...answerCard.narrativeAnswer.sections].sort((left, right) => {
    const leftPriority = priority[left.heading] ?? NARRATIVE_SECTION_ORDER.length;
    const rightPriority = priority[right.heading] ?? NARRATIVE_SECTION_ORDER.length;
    if (leftPriority !== rightPriority) {
      return leftPriority - rightPriority;
    }
    return left.heading.localeCompare(right.heading);
  });
}

function partialLimitation(answerCard: ChatAnswerCardView): string | null {
  if (answerCard.narrativeAnswer.mode !== "partial") return null;
  switch (answerCard.narrativeAnswer.fallbackReason) {
    case "limited_evidence":
      return "This answer is partial because the loaded evidence is limited.";
    case "report_unavailable":
      return "This answer is partial because the report preview was unavailable.";
    default:
      return answerCard.emptyStateReason ?? "This answer is partial because the supporting evidence is limited.";
  }
}

export function ChatRunAnswerCard({
  answerCard,
  runStatus,
}: Props) {
  const hasFindings = answerCard.takeawayRows.length > 0 || answerCard.alignmentFindings.length > 0;
  const reliabilityNote = contextReliabilityFootnote(answerCard.contextSignals, answerCard.weakEvidenceSignals);
  const narrativeSections = sortNarrativeSections(answerCard);
  const isErrorState = runStatus === "error" || answerCard.orchestrationStatus === "error";
  const isNoDataState = !isErrorState && (runStatus === "no_data" || answerCard.orchestrationStatus === "no_data");
  const thesis =
    isErrorState
      ? "This analysis didn’t finish cleanly."
      : answerCard.narrativeAnswer.thesis ||
        answerCard.emptyStateReason ||
        answerCard.summaryLine ||
        "Analysis completed without a narrative preview.";
  const supportNote = isErrorState
    ? "Open trace to inspect what failed, then retry with narrower wording or refreshed SEC data."
    : partialLimitation(answerCard) ??
      answerCard.conclusionRider?.text ??
      (isNoDataState ? answerCard.emptyStateReason : null);
  const hasSupportSection =
    hasFindings ||
    Boolean(answerCard.overallConfidence) ||
    answerCard.blockingCaveats.length > 0 ||
    answerCard.weakEvidenceSignals.length > 0 ||
    answerCard.contextSignals.length > 0 ||
    answerCard.navigationItems.length > 0 ||
    Boolean(answerCard.evidenceProvenanceHint) ||
    Boolean(answerCard.orchestrationStatus);

  return (
    <div className="w-full">
      <div className="mx-auto w-full max-w-[54rem] space-y-8">
        <section className="space-y-6 border-b border-[var(--border)]/80 pb-8">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">Answer</p>
          <p className="text-[1.1rem] font-medium leading-[1.65] tracking-[-0.025em] text-[var(--foreground)] sm:text-[1.35rem]">
            {thesis}
          </p>

          {!isErrorState && narrativeSections.length > 0 ? (
            <div className="space-y-5">
              {narrativeSections.map((section) => (
                <section key={`${section.heading}-${section.body.slice(0, 24)}`} className="space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
                    {section.heading}
                  </p>
                  <p className="text-[15px] leading-7 text-[var(--foreground)]">{section.body}</p>
                </section>
              ))}
            </div>
          ) : null}

          {supportNote ? (
            <p className="max-w-3xl text-[13px] leading-6 text-[var(--muted)]">{supportNote}</p>
          ) : null}
        </section>

        {hasSupportSection ? (
          <section className="space-y-6 rounded-[1.75rem] border border-[var(--border)]/70 bg-white/70 px-5 py-5 dark:bg-neutral-950/30">
            {hasFindings ? (
              <section className="space-y-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
                  Supporting detail
                </p>
                <div className="space-y-4">
                  {answerCard.takeawayRows.length > 0 ? (
                    <TopFindingsList items={answerCard.takeawayRows} chipMode="secondary" className="space-y-3" />
                  ) : null}
                  {answerCard.alignmentFindings.length > 0 ? (
                    <FindingCards
                      findings={answerCard.alignmentFindings}
                      chipMode="secondary"
                      className="space-y-3"
                    />
                  ) : null}
                </div>
              </section>
            ) : null}

            {(Boolean(answerCard.overallConfidence) ||
              answerCard.blockingCaveats.length > 0 ||
              answerCard.weakEvidenceSignals.length > 0 ||
              answerCard.contextSignals.length > 0) ? (
              <>
                {hasFindings ? <Separator /> : null}
                <section className="space-y-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
                    Confidence
                  </p>
                  <ConfidenceStrip
                    overallConfidence={answerCard.overallConfidence}
                    criticPhaseStatus={answerCard.criticPhaseStatus}
                    reportPhaseStatus={answerCard.reportPhaseStatus}
                    reliabilityNote={reliabilityNote}
                    className="space-y-3"
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
              </>
            ) : null}

            {answerCard.navigationItems.length > 0 || answerCard.evidenceProvenanceHint ? (
              <>
                {hasFindings ||
                answerCard.blockingCaveats.length > 0 ||
                answerCard.weakEvidenceSignals.length > 0 ||
                answerCard.contextSignals.length > 0 ||
                Boolean(answerCard.overallConfidence) ? (
                  <Separator />
                ) : null}
                <section className="space-y-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
                    Evidence
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {answerCard.navigationItems.map((item) => (
                      <Link
                        key={item.key}
                        href={item.href}
                        className="inline-flex items-center rounded-full border border-[var(--border)] bg-neutral-50 px-3 py-1.5 text-[11px] font-medium text-[var(--foreground)] transition-colors hover:border-[var(--foreground)]/30 hover:bg-[var(--background)] dark:bg-neutral-950/30"
                      >
                        {item.label}
                      </Link>
                    ))}
                  </div>
                  {answerCard.evidenceProvenanceHint ? (
                    <p className="text-[11px] leading-5 text-[var(--muted)]">{answerCard.evidenceProvenanceHint}</p>
                  ) : null}
                </section>
              </>
            ) : null}

            {answerCard.orchestrationStatus ? (
              <>
                {hasFindings ||
                answerCard.navigationItems.length > 0 ||
                answerCard.blockingCaveats.length > 0 ||
                answerCard.weakEvidenceSignals.length > 0 ||
                answerCard.contextSignals.length > 0 ||
                Boolean(answerCard.overallConfidence) ? (
                  <Separator />
                ) : null}
                <details className="group rounded-[1.2rem] border border-[var(--border)]/70 bg-neutral-50/65 px-4 py-3 dark:bg-neutral-950/20">
                  <summary className="cursor-pointer list-none text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Orchestration status
                  </summary>
                  <p className="mt-3 text-sm leading-6 text-[var(--foreground)]">{answerCard.orchestrationStatus}</p>
                </details>
              </>
            ) : null}
          </section>
        ) : null}
      </div>
    </div>
  );
}
