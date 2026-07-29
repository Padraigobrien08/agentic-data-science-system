import type { ReactNode } from "react";

import type { TraceabilityWire } from "@/lib/ai-agents-meta";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";

/** High-signal tables often absent on anomaly-only runs — surface explicitly in the UI. */
const SYNTHESIS_LAYERS: { role: string; label: string }[] = [
  { role: "unified_findings_csv", label: "Unified findings" },
  { role: "deterioration_focus_csv", label: "Deterioration focus" },
  { role: "trend_break_signals_csv", label: "Trend-break signals" },
  { role: "peer_signals_csv", label: "Peer signals" },
  { role: "findings_summary_by_company_csv", label: "Company-level summaries" },
  { role: "metric_coverage_summary_csv", label: "Metric coverage" },
  { role: "data_quality_csv", label: "Data quality" },
  { role: "exclusions_csv", label: "Exclusions" },
];

function sortRoles(roles: string[]): string[] {
  return [...roles].sort((a, b) => a.localeCompare(b));
}

function cell(ok: boolean): ReactNode {
  return (
    <span
      className={
        ok
          ? "text-emerald-800 dark:text-emerald-300"
          : "text-[var(--muted)]"
      }
    >
      {ok ? "yes" : "—"}
    </span>
  );
}

type Props = {
  orch: ParsedOrchestrationOutput | null;
  traceability: TraceabilityWire | undefined;
  blockingCaveats: string[];
  overallConfidence: string | null;
};

/**
 * At-a-glance: which narrative layers exist on disk, which were summarized for the critic,
 * and what the critic flagged — so “what’s missing” is visible without reading prose.
 */
export function RunGapOverview({
  orch,
  traceability,
  blockingCaveats,
  overallConfidence,
}: Props) {
  const pathRoles = orch?.artifact_paths ? sortRoles(Object.keys(orch.artifact_paths)) : [];
  const pathSet = new Set(pathRoles);
  const criticSummaryRoles = sortRoles(
    traceability?.critic?.artifact_summary_roles_used ??
      traceability?.critic?.excerpt_roles_used ??
      [],
  );
  const criticSummarySet = new Set(criticSummaryRoles);
  const evidenceRoles = traceability?.evidence_artifacts_by_role
    ? sortRoles(Object.keys(traceability.evidence_artifacts_by_role))
    : [];
  const evidenceSet = new Set(evidenceRoles);

  const topCaveats = blockingCaveats.slice(0, 4);
  const extra = Math.max(0, blockingCaveats.length - topCaveats.length);

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--background)] shadow-sm">
      <div className="border-b border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <h2 className="text-sm font-semibold tracking-tight text-[var(--foreground)]">
          Run overview — coverage &amp; gaps
        </h2>
        <p className="mt-1 max-w-prose text-xs leading-relaxed text-[var(--muted)]">
          Compare what the pipeline <strong className="text-[var(--foreground)]">wrote to disk</strong>, what was{" "}
          <strong className="text-[var(--foreground)]">summarized for the critic</strong>, and what was{" "}
          <strong className="text-[var(--foreground)]">registered as evidence</strong>. Empty synthesis layers
          usually mean that step did not run or produced no file — not a UI bug.
        </p>
      </div>

      <div className="space-y-4 p-4">
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 border-b border-dashed border-[var(--border)] pb-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Critic confidence
            </p>
            <p className="font-mono text-sm text-[var(--foreground)]">
              {overallConfidence ?? "—"}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Open issues (from critic)
            </p>
            <p className="font-mono text-sm text-[var(--foreground)]">{blockingCaveats.length}</p>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Roles on disk
            </p>
            <p className="font-mono text-xs text-[var(--foreground)]">
              {pathRoles.length ? pathRoles.join(", ") : "—"}
            </p>
          </div>
        </div>

        {topCaveats.length > 0 ? (
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Top critic gaps
            </p>
            <ol className="list-decimal space-y-1 pl-5 text-xs leading-relaxed text-[var(--foreground)]">
              {topCaveats.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ol>
            {extra > 0 ? (
              <p className="mt-2 text-[10px] text-[var(--muted)]">+ {extra} more in the critic card below.</p>
            ) : null}
          </div>
        ) : null}

        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Synthesis &amp; governance layers (expected on full runs)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[28rem] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">Layer</th>
                  <th className="py-2 pr-3 font-medium">On disk</th>
                  <th className="py-2 pr-3 font-medium">Critic read</th>
                  <th className="py-2 font-medium">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {SYNTHESIS_LAYERS.map(({ role, label }) => (
                  <tr key={role} className="border-b border-[var(--border)]">
                    <td className="py-2 pr-3">
                      <span className="text-[var(--foreground)]">{label}</span>
                      <span className="mt-0.5 block font-mono text-[10px] text-[var(--muted)]">{role}</span>
                    </td>
                    <td className="py-2 pr-3 font-mono">{cell(pathSet.has(role))}</td>
                    <td className="py-2 pr-3 font-mono">{cell(criticSummarySet.has(role))}</td>
                    <td className="py-2 font-mono">{cell(evidenceSet.has(role))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Core tables this run (union of disk / critic summaries / evidence)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] border-collapse text-left text-[10px]">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-1.5 pr-2 font-medium">role_key</th>
                  <th className="py-1.5 pr-2 font-medium">disk</th>
                  <th className="py-1.5 pr-2 font-medium">critic</th>
                  <th className="py-1.5 font-medium">evidence</th>
                </tr>
              </thead>
              <tbody>
                {sortRoles(
                  Array.from(
                    new Set([...pathRoles, ...criticSummaryRoles, ...evidenceRoles]),
                  ),
                ).map((role) => (
                  <tr key={role} className="border-b border-[var(--border)]">
                    <td className="py-1.5 pr-2 font-mono text-[var(--foreground)]">{role}</td>
                    <td className="py-1.5 pr-2 font-mono">{cell(pathSet.has(role))}</td>
                    <td className="py-1.5 pr-2 font-mono">{cell(criticSummarySet.has(role))}</td>
                    <td className="py-1.5 font-mono">{cell(evidenceSet.has(role))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
