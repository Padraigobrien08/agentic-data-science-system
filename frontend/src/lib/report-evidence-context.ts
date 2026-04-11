import type { TraceabilityWire } from "@/lib/ai-agents-meta";
import type { ArtifactMetadata } from "@/lib/api/types";
import type { LlmPhaseSummaryEntry } from "@/lib/orchestration-output";
import { stringArrayFromUnknown } from "@/lib/agent-transparency";

export type ReportEvidenceItem = {
  roleKey: string;
  artifactId: string;
  basename?: string;
  kind?: string;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function parseReportArtifactRefs(
  raw: unknown,
): Array<{ role?: string; basename?: string }> {
  if (!Array.isArray(raw)) return [];
  const out: Array<{ role?: string; basename?: string }> = [];
  for (const x of raw) {
    if (!isRecord(x)) continue;
    out.push({
      role: typeof x.role === "string" ? x.role : undefined,
      basename: typeof x.basename === "string" ? x.basename : undefined,
    });
  }
  return out;
}

/**
 * Merge report phase_output artifact_refs, traceability path refs, and registered run artifacts.
 */
export function buildReportEvidenceItems(
  reportPhaseOutput: Record<string, unknown> | null,
  traceability: TraceabilityWire | undefined,
  artifacts: ArtifactMetadata[],
): ReportEvidenceItem[] {
  const byRole = new Map(artifacts.map((a) => [a.role_key, a]));
  const seen = new Set<string>();
  const ordered: ReportEvidenceItem[] = [];

  const push = (roleKey: string, basename?: string) => {
    const a = byRole.get(roleKey);
    if (!a || seen.has(a.id)) return;
    seen.add(a.id);
    ordered.push({
      roleKey,
      artifactId: a.id,
      basename: basename ?? undefined,
      kind: a.kind,
    });
  };

  for (const ref of parseReportArtifactRefs(reportPhaseOutput?.artifact_refs)) {
    const role = ref.role;
    if (role) push(role, ref.basename);
  }

  for (const ref of traceability?.evidence_artifact_refs ?? []) {
    const role = ref.role;
    if (role) push(role, ref.basename);
  }

  if (ordered.length === 0) {
    for (const a of artifacts) {
      if (!seen.has(a.id)) {
        seen.add(a.id);
        ordered.push({
          roleKey: a.role_key,
          artifactId: a.id,
          kind: a.kind,
        });
      }
    }
  }

  return ordered;
}

export type EvidenceStrengthLevel = "solid" | "caution" | "weak";

export type EvidenceStrengthResult = {
  level: EvidenceStrengthLevel;
  reasons: string[];
};

/**
 * Classify how strongly the narrative is grounded in pipeline + critic signals (UI copy only).
 */
export function classifyReportEvidenceStrength(
  criticPhaseOutput: Record<string, unknown> | null,
  traceCritic: TraceabilityWire["critic"] | undefined,
  lpsCritic: LlmPhaseSummaryEntry | undefined,
  lpsReport: LlmPhaseSummaryEntry | undefined,
): EvidenceStrengthResult {
  const reasons: string[] = [];

  const cStatus = lpsCritic?.phase_status ?? traceCritic?.phase_status;
  const rStatus = lpsReport?.phase_status;
  const conf =
    (typeof criticPhaseOutput?.overall_confidence === "string"
      ? criticPhaseOutput.overall_confidence
      : null) ?? traceCritic?.overall_confidence ?? null;
  const issues = stringArrayFromUnknown(criticPhaseOutput?.issues, 50);
  const weakSig = stringArrayFromUnknown(criticPhaseOutput?.weak_evidence_signals, 20);
  const blocking = traceCritic?.blocking_caveats ?? [];

  let level: EvidenceStrengthLevel = "solid";

  if (cStatus === "failed") {
    reasons.push("Critic phase failed; narrative may not reflect a full structured review.");
    level = "weak";
  } else if (cStatus === "skipped") {
    reasons.push("Critic phase was skipped.");
    level = "caution";
  } else if (cStatus === "degraded" || lpsCritic?.degraded) {
    reasons.push("Critic phase completed with degraded status.");
    level = "caution";
  }

  if (conf === "low") {
    reasons.push("Critic marked overall confidence as low.");
    level = "weak";
  }

  if (issues.length > 0) {
    reasons.push(`Critic flagged ${issues.length} issue(s) in structured output.`);
    if (level === "solid") level = "caution";
  }

  if (weakSig.length > 0) {
    reasons.push(`Weak evidence signals: ${weakSig.join(", ")}.`);
    if (level === "solid") level = "caution";
  }

  if (blocking.length > 0) {
    reasons.push(`${blocking.length} blocking caveat(s) recorded in traceability.`);
    if (level === "solid") level = "caution";
  }

  if (rStatus === "failed") {
    reasons.push("Report phase failed.");
    level = "weak";
  } else if (rStatus === "skipped") {
    reasons.push("Report phase was skipped (markdown may be incomplete).");
    if (level === "solid") level = "caution";
  }

  if (
    traceCritic?.ran === false &&
    cStatus !== "skipped" &&
    cStatus !== "failed"
  ) {
    reasons.push("Traceability indicates the critic did not run a full review.");
    if (level === "solid") level = "caution";
  }

  if (reasons.length === 0) {
    reasons.push(
      "Critic phase succeeded without low-confidence or skip flags; tie claims to artifact links beside the report.",
    );
  }

  return { level, reasons };
}
