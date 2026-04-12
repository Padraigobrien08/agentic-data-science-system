import Link from "next/link";

import type { AnalysisRunStatus } from "@/lib/api/types";
import type { PrimaryContextSignal } from "@/lib/primary-answer-signals";
import {
  buildOutcomeSuggestions,
  classifyGoalArchetype,
  type GoalArchetype,
} from "@/lib/run-outcome-suggestions";

const ARCH_LABEL: Record<GoalArchetype, string> = {
  peer_compare: "Detected: comparison / peers focus",
  time_series: "Detected: time period or filings focus",
  risk_signal: "Detected: risk or anomaly style ask",
  document_deep: "Detected: document / section depth focus",
  general: "Detected: general analysis ask",
};

type Props = {
  status: AnalysisRunStatus;
  goalText: string;
  tickers: string[];
  contextSignals: PrimaryContextSignal[];
  weakEvidenceCount: number;
  projectId: string;
  traceHref: string;
};

export function OutcomeSuggestionsPanel({
  status,
  goalText,
  tickers,
  contextSignals,
  weakEvidenceCount,
  projectId,
  traceHref,
}: Props) {
  const actions = buildOutcomeSuggestions(
    status,
    goalText,
    tickers,
    contextSignals,
    weakEvidenceCount,
    projectId,
    traceHref,
  );

  if (!actions) {
    return null;
  }

  const arch = classifyGoalArchetype(goalText, tickers);
  const tone =
    status === "no_data"
      ? "border-violet-300/80 bg-violet-50/50 dark:border-violet-800 dark:bg-violet-950/25"
      : "border-orange-300/80 bg-orange-50/50 dark:border-orange-900 dark:bg-orange-950/20";

  return (
    <section
      className={`rounded-xl border px-4 py-4 sm:px-5 ${tone}`}
      aria-labelledby="outcome-suggestions-heading"
    >
      <h2 id="outcome-suggestions-heading" className="text-sm font-semibold text-[var(--foreground)]">
        {status === "no_data" ? "No data — suggested next steps" : "Partial result — suggested next steps"}
      </h2>
      <p className="mt-1 text-[11px] leading-snug text-[var(--muted)]">{ARCH_LABEL[arch]}</p>
      <ol className="mt-3 space-y-3">
        {actions.map((a, i) => (
          <li key={`${a.title}-${i}`} className="flex gap-3">
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--background)] text-[11px] font-semibold text-[var(--muted)]"
              aria-hidden
            >
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <Link
                href={a.href}
                className="text-sm font-medium text-[var(--foreground)] underline decoration-dotted underline-offset-2 hover:decoration-solid"
              >
                {a.title}
              </Link>
              <p className="mt-0.5 text-xs leading-relaxed text-[var(--muted)]">{a.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
