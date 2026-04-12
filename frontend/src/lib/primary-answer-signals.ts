import { stringArrayFromUnknown } from "@/lib/agent-transparency";
import { parseLlmContextAuditRows } from "@/lib/context-transparency";
import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";

export type PrimaryContextSignal = {
  id: string;
  label: string;
  tone: "neutral" | "warning" | "info";
  /** Longer explanation for hover / accessibility. */
  tooltip?: string;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function phaseOutput(po: unknown): Record<string, unknown> | null {
  return isRecord(po) ? po : null;
}

/** Critic ``phase_output.weak_evidence_signals`` (deterministic coarse hints). */
export function extractWeakEvidenceSignals(ai: ParsedAiAgents | null): string[] {
  const po = phaseOutput(ai?.critic?.phase_output);
  if (!po) return [];
  return stringArrayFromUnknown(po.weak_evidence_signals, 12);
}

/** Map ``llm_context_audit`` to product signals (granular budget keys when persisted). */
function auditToContextSignals(audit: Record<string, unknown>): PrimaryContextSignal[] {
  const rows = parseLlmContextAuditRows(audit);
  return rows.map((r) => ({
    id: `lcb_${r.key}`,
    label: r.shortLabel,
    tone: "warning" as const,
    tooltip: r.tooltip,
  }));
}

function orchestrationTransparencySignals(orch: ParsedOrchestrationOutput | null): PrimaryContextSignal[] {
  if (!orch) return [];
  const out: PrimaryContextSignal[] = [];
  const errN = Array.isArray(orch.errors) ? orch.errors.length : 0;
  const warnN = Array.isArray(orch.warnings) ? orch.warnings.length : 0;
  if (errN > 0) {
    out.push({
      id: "orch_errors",
      label: errN === 1 ? "1 run error" : `${errN} run errors`,
      tone: "warning",
      tooltip: "Orchestration recorded errors; the model may have seen only a sampled subset in context.",
    });
  }
  if (warnN > 0) {
    out.push({
      id: "orch_warnings",
      label: warnN === 1 ? "1 run warning" : `${warnN} run warnings`,
      tone: "info",
      tooltip: "Orchestration warnings were recorded; some may be omitted from model-facing context when budgets apply.",
    });
  }
  return out;
}

/**
 * Surfaces ``llm_context_audit`` (budget applied, summary clipping) and phase degradation
 * from orchestration summary — without embedding raw JSON.
 */
export function collectContextSignals(
  ai: ParsedAiAgents | null,
  orch: ParsedOrchestrationOutput | null,
): PrimaryContextSignal[] {
  const merged: PrimaryContextSignal[] = [];
  const seen = new Set<string>();

  const push = (row: PrimaryContextSignal) => {
    if (seen.has(row.id)) return;
    seen.add(row.id);
    merged.push(row);
  };

  for (const phase of [ai?.critic, ai?.report]) {
    const raw = phase && isRecord(phase) ? (phase as Record<string, unknown>).llm_context_audit : undefined;
    if (isRecord(raw)) {
      for (const f of auditToContextSignals(raw)) push(f);
    }
  }

  for (const f of orchestrationTransparencySignals(orch)) push(f);

  const lps = orch?.llm_phases_summary;
  if (lps?.critic?.degraded === true) {
    push({ id: "lps_critic_degraded", label: "Critic phase: degraded", tone: "warning" });
  }
  if (lps?.report?.degraded === true) {
    push({ id: "lps_report_degraded", label: "Report phase: degraded", tone: "warning" });
  }

  const metaCriticDegraded = ai?.critic && isRecord(ai.critic) ? (ai.critic as Record<string, unknown>).degraded === true : false;
  const metaReportDegraded = ai?.report && isRecord(ai.report) ? (ai.report as Record<string, unknown>).degraded === true : false;
  if (metaCriticDegraded && !seen.has("lps_critic_degraded")) {
    push({ id: "meta_critic_degraded", label: "Critic marked degraded", tone: "warning" });
  }
  if (metaReportDegraded && !seen.has("lps_report_degraded")) {
    push({ id: "meta_report_degraded", label: "Report marked degraded", tone: "warning" });
  }

  for (const [phase, entry] of [
    ["critic", lps?.critic],
    ["report", lps?.report],
  ] as const) {
    if (entry?.skipped && typeof entry.reason === "string" && entry.reason.trim()) {
      const id = `skipped_${phase}`;
      if (!seen.has(id)) {
        push({
          id,
          label: `${phase} skipped: ${entry.reason.replace(/_/g, " ")}`,
          tone: "info",
        });
      }
    }
  }

  return merged;
}

/**
 * One-line footnote for the confidence strip when budgets, sampling, or weak evidence apply.
 */
export function contextReliabilityFootnote(
  signals: PrimaryContextSignal[],
  weakEvidenceIds: string[],
): string | null {
  const budgetUmbrella = signals.some((s) => s.id === "lcb_llm_context_budget_applied");
  const granularBudget = signals.some((s) => s.id.startsWith("lcb_") && s.id !== "lcb_llm_context_budget_applied");
  const compact = budgetUmbrella || granularBudget;
  const sampled = signals.some(
    (s) =>
      s.id === "lcb_errors_sample_truncated" ||
      s.id === "lcb_warnings_sample_truncated" ||
      s.id === "lcb_plan_alignment_findings_truncated",
  );
  const orchNoise = signals.some((s) => s.id === "orch_errors" || s.id === "orch_warnings");

  if (compact && weakEvidenceIds.length > 0) {
    return "Compact model context and weak-evidence flags apply — treat conclusions as provisional.";
  }
  if (weakEvidenceIds.length > 0) {
    return "Weak-evidence signals were recorded — validate with artifacts before acting.";
  }
  if (sampled) {
    return "Errors, warnings, or alignment lists may be sampled in model context — see context panel in deep dive.";
  }
  if (compact) {
    return "Some model inputs were trimmed for limits — nuances may only appear in deep dive.";
  }
  if (orchNoise) {
    return "Orchestration reported warnings or errors — coverage may be incomplete.";
  }
  return null;
}
