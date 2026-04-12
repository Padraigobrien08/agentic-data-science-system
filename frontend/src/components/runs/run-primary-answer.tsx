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
import type { PrimaryAnswerView } from "@/lib/run-primary-view";

type Props = {
  projectId: string;
  runId: string;
  runStatus: AnalysisRunStatus;
  view: PrimaryAnswerView;
  isQueued: boolean;
};

/**
 * Main product surface for a completed (or in-progress) run: conclusion, findings, evidence, actions.
 * No full markdown report or trace tables — link out for those.
 */
export function RunPrimaryAnswer({ projectId, runId, runStatus, view, isQueued }: Props) {
  const traceHref = `/projects/${projectId}/runs/${runId}/trace`;
  const runsHref = `/projects/${projectId}/runs`;
  const chatHref = `/projects/${projectId}/chat`;

  const hasFindings = view.keyTakeaways.length > 0 || view.alignmentFindings.length > 0;

  const highlightConfidence =
    view.blockingCaveats.length > 0 ||
    view.weakEvidenceSignals.length > 0 ||
    view.contextSignals.some((s) => s.tone === "warning");

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <AnswerSummary
        goalDisplay={view.goalDisplay}
        summaryLine={view.summaryLine}
        orchestrationStatus={view.orchestrationStatus}
        isQueued={isQueued}
        runStatus={runStatus}
      />

      {hasFindings ? (
        <section className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Top findings</p>
          <TopFindingsList items={view.keyTakeaways} />
          <FindingCards findings={view.alignmentFindings} />
        </section>
      ) : !isQueued ? (
        <section>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Top findings</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            No takeaways or plan-alignment cards yet — open deep dive for step-level detail or re-run if the
            pipeline skipped reporting.
          </p>
        </section>
      ) : null}

      <section
        className={`rounded-xl border px-4 py-3 ${
          highlightConfidence
            ? "border-amber-300/80 bg-amber-50/60 dark:border-amber-800 dark:bg-amber-950/25"
            : "border-[var(--border)] bg-[var(--background)]"
        }`}
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Confidence & caveats</p>
        <ConfidenceStrip
          overallConfidence={view.overallConfidence}
          criticPhaseStatus={view.criticPhaseStatus}
          reportPhaseStatus={view.reportPhaseStatus}
        />
        <CaveatBadgeGroup
          blockingCaveats={view.blockingCaveats}
          weakEvidenceSignals={view.weakEvidenceSignals}
          contextSignals={view.contextSignals}
          className="mt-2"
        />
      </section>

      <section className="space-y-3">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Evidence</p>
        <EvidenceSummary links={view.evidenceLinks} extraArtifactCount={view.extraArtifactCount} />
      </section>

      <section className="space-y-3 border-t border-[var(--border)] pt-6">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Next steps</p>
        <DeepDiveActions
          traceHref={traceHref}
          reportArtifactId={view.reportArtifactId}
          chatHref={chatHref}
          runsHref={runsHref}
        />
      </section>
    </div>
  );
}
