import Link from "next/link";

import { JsonPanel } from "@/components/ui/technical";
import type { TraceabilityWire } from "@/lib/ai-agents-meta";
import type { LlmPhaseSummaryEntry } from "@/lib/orchestration-output";
import type { ArtifactMetadata } from "@/lib/api/types";
import { PhaseStatusChip } from "@/components/transparency/phase-status-chip";
import { stringArrayFromUnknown } from "@/lib/agent-transparency";
import { ModelCallInlineSummary } from "@/components/transparency/model-call-summary-card";
import type { ModelCallApiItem } from "@/lib/api/types";

type ArtifactRef = { role?: string; basename?: string };

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function parseArtifactRefs(raw: unknown): ArtifactRef[] {
  if (!Array.isArray(raw)) return [];
  const out: ArtifactRef[] = [];
  for (const x of raw) {
    if (!isRecord(x)) continue;
    out.push({
      role: typeof x.role === "string" ? x.role : undefined,
      basename: typeof x.basename === "string" ? x.basename : undefined,
    });
  }
  return out;
}

type Props = {
  lps: LlmPhaseSummaryEntry | undefined;
  phaseStatus?: string;
  trace: TraceabilityWire["report"] | undefined;
  phaseOutput: Record<string, unknown> | null;
  artifacts: ArtifactMetadata[];
  reportModelCall: ModelCallApiItem | null;
};

/**
 * Report phase: takeaways preview, markdown excerpt, artifact roles linked to registered artifacts.
 */
export function ReportEvidencePanel({
  lps,
  phaseStatus,
  trace,
  phaseOutput,
  artifacts,
  reportModelCall,
}: Props) {
  const status = lps?.phase_status ?? phaseStatus ?? trace?.phase_status;
  const takeaways = phaseOutput ? stringArrayFromUnknown(phaseOutput.key_takeaways, 20) : [];
  const preview =
    typeof phaseOutput?.markdown_preview === "string" ? phaseOutput.markdown_preview : null;
  const charCount =
    typeof phaseOutput?.markdown_char_count === "number" ? phaseOutput.markdown_char_count : null;
  const refs = phaseOutput ? parseArtifactRefs(phaseOutput.artifact_refs) : [];
  const byRole = new Map(artifacts.map((a) => [a.role_key, a]));

  const previewTakeaways = trace?.key_takeaways_preview ?? [];

  const hasAny =
    status ||
    takeaways.length > 0 ||
    previewTakeaways.length > 0 ||
    preview ||
    refs.length > 0 ||
    trace?.rationale_summary ||
    lps?.error_excerpt ||
    reportModelCall;

  if (!hasAny) {
    return (
      <div className="rounded border border-dashed border-[var(--border)] p-3 text-sm text-[var(--muted)]">
        No report phase data on this run.
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded border border-[var(--border)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide">Report and evidence</h3>
        <PhaseStatusChip status={status} />
      </div>

      {lps?.skipped ? (
        <p className="text-sm text-[var(--muted)]">
          Skipped{lps.reason ? `: ${lps.reason}` : ""}
        </p>
      ) : null}
      {lps?.error_excerpt ? (
        <p className="whitespace-pre-wrap text-sm text-red-800 dark:text-red-200">
          {lps.error_excerpt}
        </p>
      ) : null}

      {trace?.rationale_summary ? (
        <p className="max-w-prose whitespace-pre-wrap text-xs text-[var(--muted)]">
          {trace.rationale_summary}
        </p>
      ) : null}

      {previewTakeaways.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Takeaways (traceability preview)
          </p>
          <ul className="list-inside list-disc font-mono text-xs">
            {previewTakeaways.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {takeaways.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Key takeaways (phase_output)
          </p>
          <ul className="list-inside list-disc font-mono text-xs">
            {takeaways.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {preview ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Markdown preview
            {charCount != null ? (
              <span className="font-mono text-[var(--muted)]"> ({charCount} chars)</span>
            ) : null}
          </p>
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded border border-[var(--border)] bg-neutral-50 p-2 font-mono text-[11px] dark:bg-neutral-950">
            {preview}
          </pre>
        </div>
      ) : null}

      {refs.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Artifact refs (report output)
          </p>
          <ul className="space-y-1 font-mono text-xs">
            {refs.map((ref, i) => {
              const role = ref.role ?? "";
              const art = role ? byRole.get(role) : undefined;
              return (
                <li key={`${role}-${i}`}>
                  {art ? (
                    <Link href={`/artifacts/${art.id}`} className="underline">
                      {role || "?"}
                    </Link>
                  ) : (
                    <span>{role || "?"}</span>
                  )}
                  {ref.basename ? (
                    <span className="text-[var(--muted)]"> → {ref.basename}</span>
                  ) : null}
                  {!art && role ? (
                    <span className="text-[10px] text-[var(--muted)]"> (not registered)</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {reportModelCall ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Report model call
          </p>
          <ModelCallInlineSummary call={reportModelCall} />
        </div>
      ) : lps?.model_call_id ? (
        <p className="font-mono text-[10px] text-[var(--muted)]">
          model_call_id {lps.model_call_id} (no matching ModelCall row in API response)
        </p>
      ) : null}

      <details>
        <summary className="cursor-pointer font-mono text-[10px] text-[var(--muted)]">
          Raw report phase_output
        </summary>
        <div className="mt-2">
          {phaseOutput ? (
            <JsonPanel value={phaseOutput} />
          ) : (
            <p className="text-xs text-[var(--muted)]">—</p>
          )}
        </div>
      </details>
    </div>
  );
}
