"use client";

import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";

import {
  ConfidenceStrip,
  EvidenceSummary,
  InlineEvidenceCharts,
  SupplementalEvidenceRow,
} from "@/components/structured-answer";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import type { AnalysisRunStatus } from "@/lib/api/types";
import { contextReliabilityFootnote } from "@/lib/primary-answer-signals";
import type { ChatAnswerCardView, SupplementalEvidenceRow as SupplementalEvidenceRowType } from "@/lib/run-primary-view";
import { cn } from "@/lib/utils";

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

function fallbackSupplementalEvidence(answerCard: ChatAnswerCardView): SupplementalEvidenceRowType[] {
  const fromTakeaways = answerCard.takeawayRows.map((row, index) => ({
    id: `legacy-takeaway-${index}`,
    title: row.text.split(/[:.;]/)[0]?.trim() || `Supporting signal ${index + 1}`,
    reason: row.text,
    jump: row.chips[0] ? { label: "Open source", href: row.chips[0].href } : null,
    source: "takeaway" as const,
  }));
  const fromAlignment = answerCard.alignmentFindings.map((finding, index) => ({
    id: `legacy-alignment-${finding.code}-${index}`,
    title: finding.detail.split(/[:.;]/)[0]?.trim() || `Supporting check ${index + 1}`,
    reason: finding.detail,
    jump: finding.chips[0] ? { label: "Open source", href: finding.chips[0].href } : null,
    source: "alignment" as const,
  }));
  return [...fromTakeaways, ...fromAlignment];
}

export function ChatRunAnswerCard({
  answerCard,
  runStatus,
}: Props) {
  const reliabilityNote = contextReliabilityFootnote(answerCard.contextSignals, answerCard.weakEvidenceSignals);
  const narrativeSections = sortNarrativeSections(answerCard);
  const isErrorState = runStatus === "error" || answerCard.orchestrationStatus === "error";
  const isNoDataState = !isErrorState && (runStatus === "no_data" || answerCard.orchestrationStatus === "no_data");
  const [evidenceOpen, setEvidenceOpen] = useState(false);
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
  const supplementalEvidence = useMemo(
    () => answerCard.supplementalEvidence ?? fallbackSupplementalEvidence(answerCard),
    [answerCard],
  );
  const inlineCharts = answerCard.inlineCharts;
  const inlineChartNotice = answerCard.inlineChartNotice;
  const supplementalEvidenceState =
    answerCard.supplementalEvidenceState ??
    (supplementalEvidence.length > 0
      ? {
          mode: "available" as const,
          closedLabel: "Show supporting evidence",
          openLabel: "Hide supporting evidence",
          heading: null,
          body: null,
        }
      : {
          mode: "limited" as const,
          closedLabel: "Show supporting evidence",
          openLabel: "Hide supporting evidence",
          heading: "Supporting evidence is limited",
          body:
            answerCard.evidenceProvenanceHint ??
            answerCard.emptyStateReason ??
            "We checked for supporting evidence, but the mapped support for this answer is limited.",
        });
  const hasSupportBody = supplementalEvidence.length > 0;

  return (
    <div className="w-full">
      <div className="mx-auto w-full max-w-[58rem] space-y-6">
        <section className="space-y-5 border-b border-[var(--border)]/80 pb-7">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <ConfidenceStrip
              overallConfidence={answerCard.overallConfidence}
              confidenceExplainer={answerCard.confidenceExplainer}
              reliabilityNote={reliabilityNote}
            />
          </div>
          <p className="max-w-[46rem] text-[1.12rem] font-medium leading-[1.64] tracking-[-0.03em] text-[var(--foreground)] sm:text-[1.34rem]">
            {thesis}
          </p>

          {!isErrorState && narrativeSections.length > 0 ? (
            <div className="max-w-[48rem] space-y-5">
              {narrativeSections.map((section) => (
                <section key={`${section.heading}-${section.body.slice(0, 24)}`} className="space-y-2">
                  <h3 className="text-base font-semibold leading-tight tracking-[-0.01em] text-[var(--foreground)]">
                    {section.heading}
                  </h3>
                  <p className="text-[15px] leading-[1.82] text-[var(--foreground)]/95 sm:text-[15.5px]">
                    {section.body}
                  </p>
                </section>
              ))}
            </div>
          ) : null}

          {supportNote ? (
            <p className="max-w-[44rem] text-[12.5px] leading-6 text-[var(--muted)]">{supportNote}</p>
          ) : null}
        </section>

        {/* Visual evidence stays between the narrative answer and supporting evidence disclosure. */}
        {inlineCharts.length > 0 || inlineChartNotice ? (
          <InlineEvidenceCharts charts={inlineCharts} notice={inlineChartNotice} />
        ) : null}

        <section className="space-y-4">
          <Collapsible open={evidenceOpen} onOpenChange={setEvidenceOpen}>
            <div className="rounded-card border border-[var(--border)] bg-[var(--surface)] px-4 py-3.5">
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-4 rounded-control text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  aria-label={evidenceOpen ? supplementalEvidenceState.openLabel : supplementalEvidenceState.closedLabel}
                >
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                      {evidenceOpen ? supplementalEvidenceState.openLabel : supplementalEvidenceState.closedLabel}
                    </p>
                    {!evidenceOpen && supplementalEvidenceState.mode !== "available" ? (
                      <p className="mt-1 text-[12px] leading-5 text-[var(--muted)]">
                        {supplementalEvidenceState.heading}
                      </p>
                    ) : null}
                  </div>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 shrink-0 text-[var(--muted)] transition-transform duration-200",
                      evidenceOpen ? "rotate-180" : "",
                    )}
                  />
                </button>
              </CollapsibleTrigger>

              <CollapsibleContent className="data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down overflow-hidden">
                <div className="mt-4 space-y-3 border-t border-[var(--border)]/70 pt-4">
                  {hasSupportBody ? (
                    supplementalEvidence.map((row) => <SupplementalEvidenceRow key={row.id} row={row} />)
                  ) : (
                    <div className="rounded-card border border-dashed border-[var(--border)] bg-[var(--chat-rail)] px-4 py-3">
                      {supplementalEvidenceState.heading ? (
                        <p className="text-[13px] font-semibold leading-5 text-[var(--foreground)]">
                          {supplementalEvidenceState.heading}
                        </p>
                      ) : null}
                      {supplementalEvidenceState.body ? (
                        <p className="mt-1.5 text-[13px] leading-6 text-[var(--muted)]">
                          {supplementalEvidenceState.body}
                        </p>
                      ) : null}
                    </div>
                  )}
                </div>
              </CollapsibleContent>
            </div>
          </Collapsible>

          {answerCard.navigationItems.length > 0 || answerCard.evidenceProvenanceHint ? (
            <EvidenceSummary
              links={answerCard.evidenceLinks}
              extraArtifactCount={answerCard.extraArtifactCount}
              provenanceHint={answerCard.evidenceProvenanceHint}
              navItems={answerCard.navigationItems.map((item) => ({ label: item.label, href: item.href }))}
              runStatus={runStatus}
            />
          ) : null}

          {answerCard.orchestrationStatus ? (
            <details className="group rounded-card border border-[var(--border)] bg-[var(--chat-rail)] px-4 py-3">
              <summary className="cursor-pointer list-none rounded-chip text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">
                Run details
              </summary>
              <p className="mt-3 max-w-[42rem] text-sm leading-6 text-[var(--foreground)]">
                {answerCard.orchestrationStatus}
              </p>
            </details>
          ) : null}
        </section>
      </div>
    </div>
  );
}
