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

/** Small navigational link (artifact page or deep-dive hash). */
export type EvidenceNavChip = {
  label: string;
  href: string;
};

export type TakeawayRow = {
  text: string;
  chips: EvidenceNavChip[];
};

export type AlignmentFindingCard = {
  code: string;
  severity: string;
  detail: string;
  chips: EvidenceNavChip[];
};

export type EvidenceLink = {
  role: string;
  artifactId: string;
};

export type PrimaryAnswerNavContext = {
  projectId: string;
  runId: string;
};

export type PrimaryAnswerView = {
  goalDisplay: string;
  summaryLine: string | null;
  orchestrationStatus: string | null;
  /** Takeaways with shared trace chips (report / evidence / critic). */
  takeawayRows: TakeawayRow[];
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
  /** One line under the conclusion when critic blocking or weak evidence warrants it. */
  conclusionRider: { text: string; href: string } | null;
  /** Optional footnote for the evidence block (sampling / truncation / unmapped artifacts). */
  evidenceProvenanceHint: string | null;
  /** Raw goal text for deterministic outcome hints (may match ``goalDisplay``). */
  suggestionGoalText: string;
  /** Tickers from ``input_payload_json`` for outcome hinting. */
  inputTickers: string[];
};

export type CompactChatAnswerView = {
  goalDisplay: string;
  summaryLine: string | null;
  orchestrationStatus: string | null;
  conclusionRider: { text: string; href: string } | null;
};

function inputGoalText(input: unknown): string | null {
  if (!input || typeof input !== "object" || Array.isArray(input)) return null;
  const g = (input as Record<string, unknown>).analysis_goal;
  return typeof g === "string" && g.trim() ? g.trim() : null;
}

function parseInputTickers(input: unknown): string[] {
  if (!input || typeof input !== "object" || Array.isArray(input)) return [];
  const t = (input as Record<string, unknown>).tickers;
  if (!Array.isArray(t)) return [];
  return t.filter((x): x is string => typeof x === "string").map((s) => s.trim()).filter(Boolean);
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

type NormalizedAlignment = Omit<AlignmentFindingCard, "chips">;

function normalizeFindings(raw: PlanAlignmentFindingWire[] | undefined): NormalizedAlignment[] {
  if (!raw?.length) return [];
  const out: NormalizedAlignment[] = [];
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

function tracePath(nav: PrimaryAnswerNavContext, hash: string): string {
  const h = hash.startsWith("#") ? hash : `#${hash}`;
  return `/projects/${nav.projectId}/runs/${nav.runId}/trace${h}`;
}

function hasCriticSurface(ai: ParsedAiAgents | null, tr: TraceabilityWire | undefined): boolean {
  if (
    tr?.critic &&
    (tr.critic.phase_status ||
      (tr.critic.blocking_caveats && tr.critic.blocking_caveats.length > 0) ||
      (tr.critic.plan_alignment_findings && tr.critic.plan_alignment_findings.length > 0))
  ) {
    return true;
  }
  if (ai?.critic && typeof ai.critic === "object" && ai.critic.phase_output != null) return true;
  return false;
}

function mergeCriticArtifactRoles(tr: TraceabilityWire | undefined): string[] {
  const a = tr?.critic?.artifact_summary_roles_used ?? tr?.critic?.excerpt_roles_used;
  if (!Array.isArray(a)) return [];
  const out: string[] = [];
  const seen = new Set<string>();
  for (const x of a) {
    if (typeof x !== "string" || !x.trim()) continue;
    const k = x.trim();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(k);
  }
  return out;
}

function buildTakeawayChips(
  nav: PrimaryAnswerNavContext | undefined,
  reportArtifactId: string | null,
  evidenceLinks: EvidenceLink[],
  totalArtifacts: number,
  hasCritic: boolean,
  contextSignals: PrimaryContextSignal[],
): EvidenceNavChip[] {
  if (!nav) return [];
  const chips: EvidenceNavChip[] = [];
  if (reportArtifactId) {
    chips.push({ label: "Report", href: `/artifacts/${reportArtifactId}` });
  }
  if (evidenceLinks.length > 0 || totalArtifacts > 0) {
    chips.push({ label: "Evidence", href: tracePath(nav, "#run-artifacts") });
  }
  if (hasCritic) {
    chips.push({ label: "Critic", href: tracePath(nav, "#run-agents") });
  }
  const trimmed = contextSignals.some(
    (c) => c.id === "llm_context_budget" || /trim|clip|limits/i.test(c.label),
  );
  if (trimmed && chips.length < 4) {
    chips.push({ label: "Context", href: tracePath(nav, "#run-context-transparency") });
  }
  return chips.slice(0, 4);
}

function buildAlignmentChips(
  nav: PrimaryAnswerNavContext | undefined,
  byRole: Record<string, string> | undefined,
  criticRoles: string[],
  findingIndex: number,
): EvidenceNavChip[] {
  if (!nav) return [];
  const chips: EvidenceNavChip[] = [{ label: "Critic review", href: tracePath(nav, "#run-agents") }];
  if (findingIndex !== 0 || !byRole) return chips;
  let n = 0;
  for (const role of criticRoles) {
    const id = byRole[role];
    if (typeof id === "string" && id.trim() && n < 2) {
      const raw = role.replace(/_/g, " ");
      const label = raw.length > 22 ? `${raw.slice(0, 20)}…` : raw;
      chips.push({ label, href: `/artifacts/${id.trim()}` });
      n++;
    }
  }
  return chips;
}

function buildConclusionRider(
  blocking: string[],
  weak: string[],
  nav: PrimaryAnswerNavContext | undefined,
): { text: string; href: string } | null {
  if (!nav) return null;
  const criticHref = tracePath(nav, "#run-agents");
  if (blocking.length > 0) {
    const text =
      blocking.length === 1 && blocking[0]?.trim()
        ? truncate(blocking[0]!.trim(), 120)
        : `${blocking.length} blocking caveats apply — review critic context before relying on this summary.`;
    return { text, href: criticHref };
  }
  if (weak.length > 0) {
    return {
      text: "Some conclusions depend on limited or flagged evidence — see critic in deep dive.",
      href: criticHref,
    };
  }
  return null;
}

function buildEvidenceProvenanceHint(
  weak: string[],
  context: PrimaryContextSignal[],
  extraArtifactCount: number,
  evidenceLinkCount: number,
): string | null {
  const trimmed = context.some(
    (c) => c.id === "llm_context_budget" || /trim|clip|limits/i.test(c.label),
  );
  if (weak.length && trimmed) {
    return "Evidence was flagged as limited and some model inputs were trimmed — open Model context in deep dive.";
  }
  if (trimmed) {
    return "Model context limits may mean summaries are partial — see Model context in deep dive.";
  }
  if (weak.length) {
    return "The critic recorded weak-evidence signals — verify supporting artifacts in deep dive.";
  }
  if (extraArtifactCount > 0 && evidenceLinkCount === 0) {
    return "This run has registered artifacts that are not yet mapped to evidence roles.";
  }
  if (extraArtifactCount > 2 && evidenceLinkCount > 0 && evidenceLinkCount < 4) {
    return "Several artifacts sit outside the evidence map — deep dive lists the full set.";
  }
  return null;
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
  nav?: PrimaryAnswerNavContext,
): PrimaryAnswerView {
  const suggestionGoalText =
    (input.orchestration_goal_text && input.orchestration_goal_text.trim()) ||
    inputGoalText(input.input_payload_json) ||
    "";

  const goalDisplay = suggestionGoalText || "—";

  const inputTickers = parseInputTickers(input.input_payload_json);

  const summaryLine =
    (orch?.final_summary && orch.final_summary.trim()) ||
    (orch?.message && orch.message.trim()) ||
    null;

  const orchestrationStatus = orch?.status ?? null;

  const tr = ai?.traceability;
  const preview = tr?.report?.key_takeaways_preview;
  const previewList = Array.isArray(preview) ? preview.filter((x): x is string => typeof x === "string") : [];
  const takeaways = dedupeTakeaways([...(userReport?.key_takeaways ?? []), ...previewList], 8);

  const alignmentRaw = normalizeFindings(tr?.critic?.plan_alignment_findings);
  const byRole =
    tr?.evidence_artifacts_by_role && typeof tr.evidence_artifacts_by_role === "object"
      ? (tr.evidence_artifacts_by_role as Record<string, string>)
      : undefined;
  const criticArtifactRoles = mergeCriticArtifactRoles(tr);
  const alignmentFindings = alignmentRaw.map((card, idx) => ({
    ...card,
    chips: buildAlignmentChips(nav, byRole, criticArtifactRoles, idx),
  }));

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

  const hasCritic = hasCriticSurface(ai, tr);
  const takeawayChips = buildTakeawayChips(nav, reportArtifactId, links, artifacts.length, hasCritic, contextSignals);
  const takeawayRows = takeaways.map((text) => ({ text, chips: takeawayChips }));

  const conclusionRider = buildConclusionRider(blockingCaveats, weakEvidenceSignals, nav);
  const evidenceProvenanceHint = buildEvidenceProvenanceHint(
    weakEvidenceSignals,
    contextSignals,
    extraArtifactCount,
    links.length,
  );

  return {
    goalDisplay,
    summaryLine,
    orchestrationStatus,
    takeawayRows,
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
    conclusionRider,
    evidenceProvenanceHint,
    suggestionGoalText,
    inputTickers,
  };
}

export function buildCompactChatAnswerView(view: PrimaryAnswerView): CompactChatAnswerView {
  return {
    goalDisplay: view.goalDisplay,
    summaryLine: view.summaryLine,
    orchestrationStatus: view.orchestrationStatus,
    conclusionRider: view.conclusionRider,
  };
}
