/**
 * Derive structured “primary answer” view data from existing run payloads (no new API).
 */

import type { ArtifactMetadata } from "@/lib/api/types";
import type { ParsedAiAgents, PlanAlignmentFindingWire, TraceabilityWire } from "@/lib/ai-agents-meta";
import {
  collectContextSignals,
  extractWeakEvidenceSignals,
  type PrimaryContextSignal,
} from "@/lib/primary-answer-signals";
import type { ParsedOrchestrationOutput, UserFacingReport } from "@/lib/orchestration-output";

export type { PrimaryContextSignal };

export type AlignmentFindingCard = {
  code: string;
  severity: string;
  detail: string;
};

export type EvidenceLink = {
  role: string;
  artifactId: string;
};

export type PrimaryAnswerView = {
  goalDisplay: string;
  summaryLine: string | null;
  orchestrationStatus: string | null;
  keyTakeaways: string[];
  alignmentFindings: AlignmentFindingCard[];
  overallConfidence: string | null;
  blockingCaveats: string[];
  criticPhaseStatus: string | null;
  reportPhaseStatus: string | null;
  evidenceLinks: EvidenceLink[];
  extraArtifactCount: number;
  reportArtifactId: string | null;
  /** Critic ``phase_output.weak_evidence_signals`` (machine ids; UI humanizes). */
  weakEvidenceSignals: string[];
  /** Budget / truncation / skip / degradation hints (no raw JSON). */
  contextSignals: PrimaryContextSignal[];
};

function inputGoalText(input: unknown): string | null {
  if (!input || typeof input !== "object" || Array.isArray(input)) return null;
  const g = (input as Record<string, unknown>).analysis_goal;
  return typeof g === "string" && g.trim() ? g.trim() : null;
}

function truncate(s: string, max: number): string {
  const t = s.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function dedupeTakeaways(rows: string[], max: number): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const r of rows) {
    const k = r.trim();
    if (!k || seen.has(k)) continue;
    seen.add(k);
    out.push(k);
    if (out.length >= max) break;
  }
  return out;
}

function normalizeFindings(raw: PlanAlignmentFindingWire[] | undefined): AlignmentFindingCard[] {
  if (!raw?.length) return [];
  const out: AlignmentFindingCard[] = [];
  for (const f of raw.slice(0, 8)) {
    const detail = typeof f.detail === "string" ? truncate(f.detail, 220) : "";
    if (!detail && !f.code) continue;
    out.push({
      code: typeof f.code === "string" ? f.code : "finding",
      severity: typeof f.severity === "string" ? f.severity : "info",
      detail: detail || (typeof f.code === "string" ? f.code : ""),
    });
  }
  return out.slice(0, 6);
}

function evidenceFromTraceability(
  tr: TraceabilityWire | undefined,
  artifacts: ArtifactMetadata[],
): { links: EvidenceLink[]; reportArtifactId: string | null } {
  const byRole = tr?.evidence_artifacts_by_role;
  const links: EvidenceLink[] = [];
  if (byRole && typeof byRole === "object") {
    const roles = Object.keys(byRole).sort();
    for (const role of roles) {
      const id = byRole[role];
      if (typeof id === "string" && id.trim()) {
        links.push({ role, artifactId: id.trim() });
      }
    }
  }
  let reportArtifactId: string | null =
    typeof byRole?.report_md === "string" ? byRole.report_md.trim() || null : null;
  if (!reportArtifactId) {
    const hit = artifacts.find((a) => a.role_key === "report_md");
    reportArtifactId = hit?.id ?? null;
  }
  return { links: links.slice(0, 14), reportArtifactId };
}

export function buildPrimaryAnswerView(
  input: {
    orchestration_goal_text: string | null;
    input_payload_json: unknown;
    output_payload_json: unknown;
  },
  artifacts: ArtifactMetadata[],
  orch: ParsedOrchestrationOutput | null,
  userReport: UserFacingReport | null,
  ai: ParsedAiAgents | null,
): PrimaryAnswerView {
  const goalDisplay =
    (input.orchestration_goal_text && input.orchestration_goal_text.trim()) ||
    inputGoalText(input.input_payload_json) ||
    "—";

  const summaryLine =
    (orch?.final_summary && orch.final_summary.trim()) ||
    (orch?.message && orch.message.trim()) ||
    null;

  const orchestrationStatus = orch?.status ?? null;

  const tr = ai?.traceability;
  const preview = tr?.report?.key_takeaways_preview;
  const previewList = Array.isArray(preview) ? preview.filter((x): x is string => typeof x === "string") : [];
  const takeaways = dedupeTakeaways([...(userReport?.key_takeaways ?? []), ...previewList], 8);

  const alignmentFindings = normalizeFindings(tr?.critic?.plan_alignment_findings);

  const overallConfidence =
    typeof tr?.critic?.overall_confidence === "string" ? tr.critic.overall_confidence : null;
  const blockingCaveats = Array.isArray(tr?.critic?.blocking_caveats)
    ? tr!.critic!.blocking_caveats!
        .filter((x): x is string => typeof x === "string")
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, 5)
    : [];

  const criticPhaseStatus =
    typeof tr?.critic?.phase_status === "string"
      ? tr.critic.phase_status
      : typeof orch?.llm_phases_summary?.critic?.phase_status === "string"
        ? orch.llm_phases_summary!.critic!.phase_status!
        : null;
  const reportPhaseStatus =
    typeof tr?.report?.phase_status === "string"
      ? tr.report.phase_status
      : typeof orch?.llm_phases_summary?.report?.phase_status === "string"
        ? orch.llm_phases_summary!.report!.phase_status!
        : null;

  const { links, reportArtifactId } = evidenceFromTraceability(tr, artifacts);
  const linkedIds = new Set(links.map((l) => l.artifactId));
  const extraArtifactCount = artifacts.filter((a) => !linkedIds.has(a.id)).length;

  const weakEvidenceSignals = extractWeakEvidenceSignals(ai);
  const contextSignals = collectContextSignals(ai, orch);

  return {
    goalDisplay,
    summaryLine,
    orchestrationStatus,
    keyTakeaways: takeaways,
    alignmentFindings,
    overallConfidence,
    blockingCaveats,
    criticPhaseStatus,
    reportPhaseStatus,
    evidenceLinks: links,
    extraArtifactCount,
    reportArtifactId,
    weakEvidenceSignals,
    contextSignals,
  };
}
