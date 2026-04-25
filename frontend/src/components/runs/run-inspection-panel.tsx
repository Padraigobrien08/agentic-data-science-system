import Link from "next/link";

import { OutcomeSuggestionsPanel } from "@/components/runs/outcome-suggestions-panel";
import { VerifyAnalysisSection } from "@/components/runs/verify-analysis-section";
import type { AnalysisRunStatus } from "@/lib/api/types";
import type { PrimaryAnswerView } from "@/lib/run-primary-view";

type Props = {
  projectId: string;
  runId: string;
  runStatus: AnalysisRunStatus;
  view: PrimaryAnswerView;
  canExecute: boolean;
};

export function RunInspectionPanel({ projectId, runId, runStatus, view, canExecute }: Props) {
  const traceHref = `/projects/${projectId}/runs/${runId}/trace`;
  const chatHref = `/projects/${projectId}/chat`;

  return (
    <article className="space-y-6">
      <section className="rounded-xl border border-[var(--border)] bg-neutral-50/50 px-4 py-4 sm:px-5 dark:bg-neutral-950/30">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Inspection focus</p>
        <p className="mt-2 max-w-prose text-sm leading-relaxed text-[var(--foreground)]">
          The full answer lives in chat. Use this page to verify artifacts, inspect execution, and rerun the
          pipeline when the run needs another pass.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Link
            href={chatHref}
            className="inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-[var(--foreground)] px-4 py-2 text-sm font-medium text-[var(--background)]"
          >
            Back to chat
          </Link>
          <Link
            href={traceHref}
            className="inline-flex items-center justify-center rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)]"
          >
            Open trace
          </Link>
        </div>
      </section>

      <VerifyAnalysisSection
        traceHref={traceHref}
        evidenceLinks={view.evidenceLinks}
        reportArtifactId={view.reportArtifactId}
        projectId={projectId}
        runId={runId}
        canExecute={canExecute}
      />

      <OutcomeSuggestionsPanel
        status={runStatus}
        goalText={view.suggestionGoalText}
        tickers={view.inputTickers}
        contextSignals={view.contextSignals}
        weakEvidenceCount={view.weakEvidenceSignals.length}
        projectId={projectId}
        traceHref={traceHref}
      />
    </article>
  );
}
