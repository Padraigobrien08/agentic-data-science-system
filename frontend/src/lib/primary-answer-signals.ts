import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";
import { stringArrayFromUnknown } from "@/lib/agent-transparency";

export type PrimaryContextSignal = {
  id: string;
  label: string;
  tone: "neutral" | "warning" | "info";
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

function auditFlags(audit: Record<string, unknown>): PrimaryContextSignal[] {
  const out: PrimaryContextSignal[] = [];
  if (audit.llm_context_budget_applied === true) {
    out.push({
      id: "llm_context_budget",
      label: "LLM context trimmed for limits",
      tone: "warning",
    });
  }
  if (audit.context_budget_truncated === true) {
    out.push({
      id: "artifact_summaries_truncated",
      label: "Artifact summaries clipped",
      tone: "warning",
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
      for (const f of auditFlags(raw)) push(f);
    }
  }

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
