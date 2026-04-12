import Link from "next/link";

import {
  AnswerSummary,
  CaveatBadgeGroup,
  ConfidenceStrip,
  DeepDiveActions,
  EvidenceSummary,
  FindingCards,
  TopFindingsList,
} from "@/components/structured-answer";
import type { AnalysisRunStatus } from "@/lib/api/types";
import { contextReliabilityFootnote } from "@/lib/primary-answer-signals";
import type { PrimaryAnswerView } from "@/lib/run-primary-view";

type Props = {
  projectId: string;
  runId: string;
  runStatus: AnalysisRunStatus;
  view: PrimaryAnswerView;
};

/**
 * Main product surface for a completed (or in-progress) run: conclusion, findings, evidence, actions.
 * No full markdown report or trace tables — link out for those.
 */
export function RunPrimaryAnswer({ projectId, runId, runStatus, view }: Props) {
  const traceHref = `/projects/${projectId}/runs/${runId}/trace`;
  const runsHref = `/projects/${projectId}/runs`;
  const chatHref = `/projects/${projectId}/chat`;

  const runInFlight = runStatus === "queued" || runStatus === "running";
  const hasFindings = view.takeawayRows.length > 0 || view.alignmentFindings.length > 0;

  const highlightConfidence =
    view.blockingCaveats.length > 0 ||
    view.weakEvidenceSignals.length > 0 ||
    view.contextSignals.some((s) => s.tone === "warning");

  const reliabilityNote = contextReliabilityFootnote(view.contextSignals, view.weakEvidenceSignals);

  return (
    <article className="space-y-10">
      <AnswerSummary
        goalDisplay={view.goalDisplay}
        summaryLine={view.summaryLine}
        orchestrationStatus={view.orchestrationStatus}
        runStatus={runStatus}
        conclusionRider={view.conclusionRider}
      />

      {hasFindings ? (
        <section className="space-y-4">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Top findings</p>
          <TopFindingsList items={view.takeawayRows} />
          <FindingCards findings={view.alignmentFindings} />
        </section>
      ) : !runInFlight ? (
        <section className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Top findings</p>
          <p className="text-sm leading-relaxed text-[var(--muted)]">
            No takeaways or plan-alignment cards yet. Reporting may not have emitted cards, or the run may still be
            finishing — use deep dive for step detail, then re-run or adjust inputs if needed.
          </p>
        </section>
      ) : (
        <section className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Top findings</p>
          <p className="text-sm leading-relaxed text-[var(--muted)]">
            Findings populate as phases complete. Open{" "}
            <Link href={traceHref} className="font-medium text-[var(--foreground)] underline">
              deep dive
            </Link>{" "}
            for live steps and partial artifacts.
          </p>
        </section>
      )}

      <section className="space-y-3">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Evidence</p>
        <EvidenceSummary
          links={view.evidenceLinks}
          extraArtifactCount={view.extraArtifactCount}
          provenanceHint={view.evidenceProvenanceHint}
          deepDiveHref={traceHref}
          runStatus={runStatus}
        />
      </section>

      <section
        className={`rounded-xl border px-4 py-4 sm:px-5 ${
          highlightConfidence
            ? "border-amber-300/80 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20"
            : "border-[var(--border)] bg-neutral-50/40 dark:bg-neutral-950/30"
        }`}
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Confidence & caveats</p>
        <ConfidenceStrip
          overallConfidence={view.overallConfidence}
          criticPhaseStatus={view.criticPhaseStatus}
          reportPhaseStatus={view.reportPhaseStatus}
          reliabilityNote={reliabilityNote}
        />
        <CaveatBadgeGroup
          blockingCaveats={view.blockingCaveats}
          weakEvidenceSignals={view.weakEvidenceSignals}
          contextSignals={view.contextSignals}
          maxContextBadges={4}
          maxWeakBadges={2}
          overflowHref={`${traceHref}#run-context-transparency`}
          className="mt-2"
        />
      </section>

      <section className="space-y-3 border-t border-[var(--border)] pt-8">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Next steps</p>
        <DeepDiveActions
          traceHref={traceHref}
          reportArtifactId={view.reportArtifactId}
          chatHref={chatHref}
          runsHref={runsHref}
        />
      </section>
    </article>
  );
}
