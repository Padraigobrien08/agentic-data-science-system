import Link from "next/link";

import type { InvestigationSummary } from "@/lib/api/types";
import { formatConfidence, investigationStatusTone } from "@/lib/investigation-view";

import { Pill } from "./pill";

function CountChip({ label, value }: Readonly<{ label: string; value: number }>) {
  return (
    <span className="inline-flex items-baseline gap-1 text-xs text-neutral-500 dark:text-neutral-400">
      <span className="font-mono font-medium text-neutral-700 dark:text-neutral-200">{value}</span>
      {label}
    </span>
  );
}

export function InvestigationSummaryList({
  projectId,
  investigations,
}: Readonly<{ projectId: string; investigations: InvestigationSummary[] }>) {
  if (investigations.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
        No investigations yet. Runs that execute through the agentic engine appear here with their
        hypotheses, evidence, and decisions.
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {investigations.map((inv) => {
        const tone = investigationStatusTone(inv.status);
        return (
          <li key={inv.id}>
            <Link
              href={`/projects/${projectId}/investigations/${inv.id}`}
              className="block rounded-lg border border-neutral-200 p-4 transition-colors hover:border-neutral-300 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:border-neutral-700 dark:hover:bg-neutral-900"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {inv.objective ?? "Investigation"}
                </p>
                <Pill tone={tone} />
              </div>
              {inv.conclusion ? (
                <p className="mt-1 line-clamp-2 text-sm text-neutral-600 dark:text-neutral-300">
                  {inv.conclusion}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1">
                <CountChip label="hypotheses" value={inv.counts.hypotheses} />
                <CountChip label="evidence" value={inv.counts.evidence} />
                <CountChip label="experiments" value={inv.counts.experiments} />
                <CountChip label="decisions" value={inv.counts.decisions} />
                <span className="ml-auto text-xs text-neutral-400 dark:text-neutral-500">
                  confidence {formatConfidence(inv.confidence)}
                  {inv.adapter_id ? ` · ${inv.adapter_id}` : ""}
                </span>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
