import Link from "next/link";

import { MarkdownReport } from "@/components/runs/markdown-report";
import type { TraceabilityWire } from "@/lib/ai-agents-meta";
import type { ArtifactMetadata } from "@/lib/api/types";
import type { LlmPhaseSummaryEntry } from "@/lib/orchestration-output";
import {
  buildReportEvidenceItems,
  classifyReportEvidenceStrength,
} from "@/lib/report-evidence-context";
import { stringArrayFromUnknown } from "@/lib/agent-transparency";

type Props = {
  markdown: string;
  keyTakeaways: string[];
  modelCallId?: string | null;
  reportPhaseOutput: Record<string, unknown> | null;
  criticPhaseOutput: Record<string, unknown> | null;
  traceability: TraceabilityWire | undefined;
  lpsCritic: LlmPhaseSummaryEntry | undefined;
  lpsReport: LlmPhaseSummaryEntry | undefined;
  artifacts: ArtifactMetadata[];
};

function strengthStyles(level: "solid" | "caution" | "weak"): string {
  switch (level) {
    case "weak":
      return "border-l-4 border-red-600 bg-red-50/60 dark:border-red-500 dark:bg-red-950/30";
    case "caution":
      return "border-l-4 border-amber-600 bg-amber-50/60 dark:border-amber-500 dark:bg-amber-950/25";
    default:
      return "border-l-4 border-emerald-700/70 bg-emerald-50/40 dark:border-emerald-600 dark:bg-emerald-950/20";
  }
}

/**
 * Final markdown report with explicit evidence links, critic context beside conclusions, and strength signal.
 */
export function FinalReportWithEvidence({
  markdown,
  keyTakeaways,
  modelCallId,
  reportPhaseOutput,
  criticPhaseOutput,
  traceability,
  lpsCritic,
  lpsReport,
  artifacts,
}: Props) {
  const evidenceItems = buildReportEvidenceItems(
    reportPhaseOutput,
    traceability,
    artifacts,
  );
  const strength = classifyReportEvidenceStrength(
    criticPhaseOutput,
    traceability?.critic,
    lpsCritic,
    lpsReport,
  );

  const issues = stringArrayFromUnknown(criticPhaseOutput?.issues, 12);
  const blocking = traceability?.critic?.blocking_caveats ?? [];
  const conf =
    (typeof criticPhaseOutput?.overall_confidence === "string"
      ? criticPhaseOutput.overall_confidence
      : null) ?? traceability?.critic?.overall_confidence ?? null;
  const hasFindingsExcerpt =
    typeof criticPhaseOutput?.findings_assessment_excerpt === "string";
  const hasCaveatsExcerpt =
    typeof criticPhaseOutput?.caveat_coverage_excerpt === "string";
  const showCriticAside =
    issues.length > 0 ||
    blocking.length > 0 ||
    conf != null ||
    hasFindingsExcerpt ||
    hasCaveatsExcerpt;

  const headingEvidenceFooter =
    evidenceItems.length > 0 ? (
      <>
        {evidenceItems.map((item, idx) => (
          <span key={item.artifactId}>
            {idx > 0 ? <span className="text-[var(--muted)]"> · </span> : null}
            <Link
              href={`/artifacts/${item.artifactId}`}
              className="font-mono text-[var(--foreground)] underline"
            >
              {item.roleKey}
            </Link>
            {item.basename ? (
              <span className="font-mono text-[var(--muted)]"> ({item.basename})</span>
            ) : null}
          </span>
        ))}
      </>
    ) : (
      <span className="font-mono text-[var(--muted)]">
        No artifact refs in report output — check run artifacts list.
      </span>
    );

  return (
    <div className="space-y-4">
      <div className={`rounded-r border border-[var(--border)] p-3 ${strengthStyles(strength.level)}`}>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--foreground)]">
          Evidence basis
          {strength.level === "weak"
            ? " — weak or partial"
            : strength.level === "caution"
              ? " — review caveats"
              : " — aligned with critic output"}
        </p>
        <ul className="mt-2 list-inside list-disc font-mono text-xs text-[var(--foreground)]">
          {strength.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </div>

      <div className="lg:grid lg:grid-cols-[1fr_13.5rem] lg:gap-6 xl:grid-cols-[1fr_15rem]">
        <div className="min-w-0 space-y-4">
          {keyTakeaways.length > 0 ? (
            <div className="rounded border border-[var(--border)] p-3">
              <p className="mb-2 text-xs font-semibold uppercase text-[var(--muted)]">
                Key takeaways
              </p>
              <ul className="list-inside list-disc space-y-2 font-mono text-sm">
                {keyTakeaways.map((t, i) => (
                  <li key={`${i}-${t.slice(0, 48)}`}>{t}</li>
                ))}
              </ul>
              <p className="mt-3 border-t border-[var(--border)] pt-2 font-mono text-[10px] text-[var(--muted)]">
                Each bullet should be read against the supporting files repeated under section
                headings and in the evidence column.
              </p>
            </div>
          ) : null}

          {showCriticAside ? (
            <div className="rounded border border-[var(--border)] border-dashed bg-neutral-50/80 p-3 dark:bg-neutral-950/40">
              <p className="mb-2 text-xs font-semibold uppercase text-[var(--muted)]">
                Critic context (alongside conclusions)
              </p>
              {conf ? (
                <p className="mb-2 font-mono text-xs">
                  <span className="text-[var(--muted)]">overall_confidence</span>{" "}
                  <span
                    className={
                      conf === "low"
                        ? "font-semibold text-red-800 dark:text-red-300"
                        : ""
                    }
                  >
                    {conf}
                  </span>
                </p>
              ) : null}
              {blocking.length > 0 ? (
                <div className="mb-2">
                  <p className="mb-1 font-mono text-[10px] font-semibold text-[var(--muted)]">
                    Blocking caveats
                  </p>
                  <ul className="list-inside list-disc font-mono text-xs">
                    {blocking.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {issues.length > 0 ? (
                <div className="mb-2">
                  <p className="mb-1 font-mono text-[10px] font-semibold text-[var(--muted)]">
                    Flagged issues (structured critic output)
                  </p>
                  <ul className="list-inside list-disc font-mono text-xs">
                    {issues.map((i) => (
                      <li key={i}>{i}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {typeof criticPhaseOutput?.findings_assessment_excerpt === "string" ? (
                <p className="mt-2 whitespace-pre-wrap border-t border-[var(--border)] pt-2 font-mono text-[11px] text-[var(--muted)]">
                  <span className="font-semibold text-[var(--foreground)]">Findings: </span>
                  {criticPhaseOutput.findings_assessment_excerpt}
                </p>
              ) : null}
              {typeof criticPhaseOutput?.caveat_coverage_excerpt === "string" ? (
                <p className="mt-2 whitespace-pre-wrap font-mono text-[11px] text-[var(--muted)]">
                  <span className="font-semibold text-[var(--foreground)]">Caveats: </span>
                  {criticPhaseOutput.caveat_coverage_excerpt}
                </p>
              ) : null}
            </div>
          ) : null}

          {modelCallId ? (
            <p className="font-mono text-[10px] text-[var(--muted)]">
              report model_call_id: {modelCallId}
            </p>
          ) : null}

          <MarkdownReport
            source={markdown}
            headingEvidenceFooter={headingEvidenceFooter}
          />
        </div>

        <aside className="mt-6 min-w-0 border-t border-[var(--border)] pt-4 font-mono text-[10px] lg:mt-0 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
          <p className="mb-2 font-semibold uppercase text-[var(--foreground)]">Evidence files</p>
          <p className="mb-3 text-[var(--muted)]">
            Roles the report agent attached plus pipeline paths (deduped). Open a row to inspect CSV
            / text.
          </p>
          <ul className="space-y-2">
            {evidenceItems.map((item) => (
              <li key={item.artifactId}>
                <Link href={`/artifacts/${item.artifactId}`} className="break-all underline">
                  {item.roleKey}
                </Link>
                {item.kind ? (
                  <span className="block text-[var(--muted)]">{item.kind}</span>
                ) : null}
                {item.basename ? (
                  <span className="block truncate text-[var(--muted)]">{item.basename}</span>
                ) : null}
              </li>
            ))}
          </ul>
          {traceability?.critic?.excerpt_roles_used &&
          traceability.critic.excerpt_roles_used.length > 0 ? (
            <div className="mt-4 border-t border-[var(--border)] pt-3">
              <p className="mb-1 font-semibold uppercase text-[var(--foreground)]">
                Critic excerpt roles
              </p>
              <p className="text-[var(--muted)]">
                {traceability.critic.excerpt_roles_used.join(", ")}
              </p>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
