import { JsonPanel, MetaRow } from "@/components/ui/technical";
import type { TraceabilityWire } from "@/lib/ai-agents-meta";
import type { LlmPhasesSummaryWire } from "@/lib/orchestration-output";
import { PhaseStatusChip } from "@/components/transparency/phase-status-chip";
import { stringArrayFromUnknown } from "@/lib/agent-transparency";
import { ModelCallInlineSummary } from "@/components/transparency/model-call-summary-card";
import type { ModelCallApiItem } from "@/lib/api/types";
import { collectPlanAlignmentFindings } from "@/components/trace/plan-alignment-callout";

type Props = {
  lps: LlmPhasesSummaryWire | undefined;
  phaseStatus?: string;
  trace: TraceabilityWire["critic"] | undefined;
  phaseOutput: Record<string, unknown> | null;
  criticModelCall: ModelCallApiItem | null;
};

/**
 * Critic phase: status, issues, excerpts — full phase_output JSON only under details.
 */
export function CriticFindingsCard({
  lps,
  phaseStatus,
  trace,
  phaseOutput,
  criticModelCall,
}: Props) {
  const summary = lps?.critic;
  const status =
    summary?.phase_status ?? phaseStatus ?? trace?.phase_status;

  const issues = phaseOutput ? stringArrayFromUnknown(phaseOutput.issues, 24) : [];
  const conf =
    typeof phaseOutput?.overall_confidence === "string"
      ? phaseOutput.overall_confidence
      : trace?.overall_confidence ?? null;
  const findings =
    typeof phaseOutput?.findings_assessment_excerpt === "string"
      ? phaseOutput.findings_assessment_excerpt
      : null;
  const caveats =
    typeof phaseOutput?.caveat_coverage_excerpt === "string"
      ? phaseOutput.caveat_coverage_excerpt
      : null;
  const trust =
    typeof phaseOutput?.trustworthiness_notes_excerpt === "string"
      ? phaseOutput.trustworthiness_notes_excerpt
      : null;
  const weak = stringArrayFromUnknown(phaseOutput?.weak_evidence_signals, 12);

  const { findings: planAlign } = collectPlanAlignmentFindings(
    phaseOutput,
    trace,
  );

  const hasAny =
    status ||
    trace?.decision_summary ||
    issues.length > 0 ||
    findings ||
    caveats ||
    trust ||
    summary?.error_excerpt ||
    criticModelCall ||
    planAlign.length > 0;

  if (!hasAny) {
    return (
      <div className="rounded border border-dashed border-[var(--border)] p-3 text-sm text-[var(--muted)]">
        No critic phase data on this run.
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded border border-[var(--border)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide">Critic findings</h3>
        <PhaseStatusChip status={status} />
      </div>

      {trace?.decision_summary ? (
        <p className="max-w-prose whitespace-pre-wrap text-sm">{trace.decision_summary}</p>
      ) : null}

      {summary?.skipped ? (
        <p className="text-sm text-[var(--muted)]">
          Skipped{summary.reason ? `: ${summary.reason}` : ""}
        </p>
      ) : null}

      {summary?.error_excerpt ? (
        <p className="whitespace-pre-wrap text-sm text-red-800 dark:text-red-200">
          {summary.error_excerpt}
        </p>
      ) : null}

      {conf ? (
        <p className="font-mono text-xs">
          <span className="text-[var(--muted)]">overall_confidence</span> {conf}
        </p>
      ) : null}

      {planAlign.length > 0 ? (
        <p className="rounded border border-[var(--border)] bg-[var(--background)]/40 px-2 py-1.5 text-xs text-[var(--muted)]">
          Deterministic plan–goal alignment notes are shown under{" "}
          <a href="#run-plan-decision" className="font-mono text-[var(--foreground)] underline">
            Planning quality → Plan template…
          </a>
          .
        </p>
      ) : null}

      {issues.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">Issues</p>
          <ul className="list-inside list-disc space-y-1 font-mono text-xs">
            {issues.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {weak.length > 0 ? (
        <p className="font-mono text-[10px] text-[var(--muted)]">
          weak_evidence: {weak.join(", ")}
        </p>
      ) : null}

      {findings ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Findings assessment (excerpt)
          </p>
          <p className="whitespace-pre-wrap text-xs">{findings}</p>
        </div>
      ) : null}
      {caveats ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Caveat coverage (excerpt)
          </p>
          <p className="whitespace-pre-wrap text-xs">{caveats}</p>
        </div>
      ) : null}
      {trust ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Trustworthiness (excerpt)
          </p>
          <p className="whitespace-pre-wrap text-xs">{trust}</p>
        </div>
      ) : null}

      {trace?.blocking_caveats && trace.blocking_caveats.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Blocking caveats
          </p>
          <ul className="list-inside list-disc font-mono text-xs">
            {trace.blocking_caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {(trace?.artifact_summary_roles_used?.length ?? trace?.excerpt_roles_used?.length) ? (
        <MetaRow label="artifact_summary_roles_used">
          {(trace?.artifact_summary_roles_used ?? trace?.excerpt_roles_used ?? []).join(", ")}
        </MetaRow>
      ) : null}

      {criticModelCall ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Critic model call
          </p>
          <ModelCallInlineSummary call={criticModelCall} />
        </div>
      ) : summary?.model_call_id ? (
        <p className="font-mono text-[10px] text-[var(--muted)]">
          model_call_id {summary.model_call_id} (no matching ModelCall row in API response)
        </p>
      ) : null}

      <details>
        <summary className="cursor-pointer font-mono text-[10px] text-[var(--muted)]">
          Raw critic phase_output
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
