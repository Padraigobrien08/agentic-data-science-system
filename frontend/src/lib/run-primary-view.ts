/**
 * Derive structured “primary answer” view data from existing run payloads (no new API).
 */

import type {
  ArtifactMetadata,
  ConfidenceExplainerPreview,
  RunTransparencySummary,
} from "@/lib/api/types";
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

export type SupplementalEvidenceJump = {
  label: string;
  href: string;
};

export type SupplementalEvidenceRow = {
  id: string;
  title: string;
  reason: string;
  jump: SupplementalEvidenceJump | null;
  source: "takeaway" | "alignment";
};

export type SupplementalEvidenceState = {
  mode: "available" | "limited" | "empty";
  closedLabel: string;
  openLabel: string;
  heading: string | null;
  body: string | null;
};

export type EvidenceLink = {
  role: string;
  artifactId: string;
};

export type PrimaryAnswerNavContext = {
  projectId: string;
  runId: string;
};

export type NarrativeAnswerSectionView = {
  heading: string;
  body: string;
};

export type NarrativeAnswerView = {
  mode: "full" | "partial" | "legacy";
  thesis: string;
  sections: NarrativeAnswerSectionView[];
  fallbackReason: string | null;
};

export type ConfidenceTone = "good" | "medium" | "bad" | "neutral";

export type ConfidenceExplainerView = {
  label: "Strong" | "Moderate" | "Weak" | "Not rated";
  tone: ConfidenceTone;
  supports: string[];
  weakens: string[];
  limits: string[];
};

export type InlineChartSeriesView = {
  key: string;
  label: string;
  colorToken: "chart-1" | "chart-2" | "chart-3" | "chart-4";
};

export type InlineChartMarkerView = {
  xValue: string;
  label: string;
};

export type InlineChartView = {
  chartId: string;
  kind: "line" | "grouped_bar";
  metricKey: string;
  metricLabel: string;
  caption: string;
  xAxisLabel: string;
  yAxisLabel: string;
  valueFormat: "currency" | "percent" | "ratio" | "count" | "number";
  series: InlineChartSeriesView[];
  rows: Array<{
    xValue: string;
    values: Record<string, number | null>;
  }>;
  markers: InlineChartMarkerView[];
};

export type PrimaryAnswerView = {
  goalDisplay: string;
  narrativeAnswer: NarrativeAnswerView;
  summaryLine: string | null;
  orchestrationStatus: string | null;
  /** Explanation when the run finished but no structured summary/findings were surfaced. */
  emptyStateReason: string | null;
  /** Takeaways with shared trace chips (report / evidence / critic). */
  takeawayRows: TakeawayRow[];
  alignmentFindings: AlignmentFindingCard[];
  supplementalEvidence: SupplementalEvidenceRow[];
  supplementalEvidenceState: SupplementalEvidenceState;
  overallConfidence: string | null;
  confidenceExplainer: ConfidenceExplainerView;
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
  inlineCharts: InlineChartView[];
  inlineChartNotice: string | null;
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
  narrativeAnswer: NarrativeAnswerView;
  summaryLine: string | null;
  orchestrationStatus: string | null;
  emptyStateReason: string | null;
  conclusionRider: { text: string; href: string } | null;
};

export type ChatEvidenceNavItem = {
  key: "report" | "evidence" | "artifacts" | "critic" | "trace";
  label: string;
  href: string;
};

export type ChatAnswerCardView = CompactChatAnswerView & {
  takeawayRows: TakeawayRow[];
  alignmentFindings: AlignmentFindingCard[];
  supplementalEvidence?: SupplementalEvidenceRow[];
  supplementalEvidenceState?: SupplementalEvidenceState;
  overallConfidence: string | null;
  confidenceExplainer: ConfidenceExplainerView;
  blockingCaveats: string[];
  criticPhaseStatus: string | null;
  reportPhaseStatus: string | null;
  weakEvidenceSignals: string[];
  contextSignals: PrimaryContextSignal[];
  inlineCharts: InlineChartView[];
  inlineChartNotice: string | null;
  evidenceLinks: EvidenceLink[];
  extraArtifactCount: number;
  reportArtifactId: string | null;
  evidenceProvenanceHint: string | null;
  navigationItems: ChatEvidenceNavItem[];
  traceHref: string | null;
  caveatOverflowHref: string | null;
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

function compactWhitespace(input: string): string {
  return input.replace(/\s+/g, " ").trim();
}

function buildEvidenceTitle(input: string, fallback: string): string {
  const clean = compactWhitespace(input);
  if (!clean) return fallback;
  const clause = clean.split(/[:.;]/)[0]?.trim() || clean;
  const words = clause.split(/\s+/).slice(0, 7).join(" ");
  return truncate(words || fallback, 52);
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

function mapConfidenceTone(value: string | null): ConfidenceTone {
  switch (value) {
    case "high":
      return "good";
    case "medium":
      return "medium";
    case "low":
      return "bad";
    default:
      return "neutral";
  }
}

function mapConfidenceLabel(value: string | null): ConfidenceExplainerView["label"] {
  switch (value) {
    case "high":
      return "Strong";
    case "medium":
      return "Moderate";
    case "low":
      return "Weak";
    default:
      return "Not rated";
  }
}

function sanitizeExplainerList(items: unknown, max = 4): string[] {
  if (!Array.isArray(items)) return [];
  const out: string[] = [];
  const seen = new Set<string>();
  for (const item of items) {
    if (typeof item !== "string" || !item.trim()) continue;
    const clean = item.trim();
    const key = clean.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(clean);
    if (out.length >= max) break;
  }
  return out;
}

function buildConfidenceExplainer(
  overallConfidence: string | null,
  transparency: RunTransparencySummary | null | undefined,
  tr: TraceabilityWire | undefined,
  blockingCaveats: string[],
  weakEvidenceSignals: string[],
  contextSignals: PrimaryContextSignal[],
): ConfidenceExplainerView {
  const raw: ConfidenceExplainerPreview | null | undefined = transparency?.confidence_explainer
    ? transparency.confidence_explainer
    : tr?.critic?.confidence_explainer
      ? {
          supports: tr.critic.confidence_explainer.supports ?? [],
          weakens: tr.critic.confidence_explainer.weakens ?? [],
          limits: tr.critic.confidence_explainer.limits ?? [],
        }
      : null;

  const supports = sanitizeExplainerList(raw?.supports);
  const weakens = sanitizeExplainerList(raw?.weakens);
  const limits = sanitizeExplainerList(raw?.limits);

  if (supports.length || weakens.length || limits.length) {
    return {
      label: mapConfidenceLabel(overallConfidence),
      tone: mapConfidenceTone(overallConfidence),
      supports,
      weakens,
      limits,
    };
  }

  return {
    label: mapConfidenceLabel(overallConfidence),
    tone: mapConfidenceTone(overallConfidence),
    supports: [],
    weakens: sanitizeExplainerList(blockingCaveats),
    limits: sanitizeExplainerList([
      ...weakEvidenceSignals.map((signal) => signal.replace(/_/g, " ")),
      ...contextSignals.map((signal) => signal.label),
    ]),
  };
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

function hasCriticSurfaceFromTransparency(transparency: RunTransparencySummary | null | undefined): boolean {
  if (!transparency) return false;
  return Boolean(
    transparency.critic_phase_status ||
      transparency.critic_overall_confidence ||
      (transparency.critic_blocking_caveats ?? []).length,
  );
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
    const text = truncate(blocking[0]!.trim(), 140);
    return { text, href: criticHref };
  }
  if (weak.length > 0) {
    return {
      text: "Some conclusions depend on limited or flagged evidence.",
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

function selectExactJump(chips: EvidenceNavChip[]): SupplementalEvidenceJump | null {
  if (!chips.length) return null;
  const preferred =
    chips.find((chip) => chip.href.startsWith("/artifacts/")) ??
    chips.find((chip) => chip.href.includes("#")) ??
    chips[0];
  if (!preferred) return null;
  return { label: "Open source", href: preferred.href };
}

function buildSupplementalEvidence(
  takeawayRows: TakeawayRow[],
  alignmentFindings: AlignmentFindingCard[],
): SupplementalEvidenceRow[] {
  const rows: SupplementalEvidenceRow[] = [];

  takeawayRows.forEach((row, index) => {
    rows.push({
      id: `takeaway-${index}`,
      title: buildEvidenceTitle(row.text, `Supporting signal ${index + 1}`),
      reason: row.text,
      jump: selectExactJump(row.chips),
      source: "takeaway",
    });
  });

  alignmentFindings.forEach((finding, index) => {
    rows.push({
      id: `alignment-${finding.code}-${index}`,
      title: buildEvidenceTitle(finding.detail, `Supporting check ${index + 1}`),
      reason: finding.detail,
      jump: selectExactJump(finding.chips),
      source: "alignment",
    });
  });

  return rows;
}

function buildSupplementalEvidenceState(input: {
  supplementalEvidence: SupplementalEvidenceRow[];
  emptyStateReason: string | null;
  evidenceProvenanceHint: string | null;
  evidenceLinkCount: number;
  extraArtifactCount: number;
  reportArtifactId: string | null;
  weakEvidenceSignals: string[];
}): SupplementalEvidenceState {
  const closedLabel = "Show supporting evidence";
  const openLabel = "Hide supporting evidence";

  if (input.supplementalEvidence.length > 0) {
    return {
      mode: "available",
      closedLabel,
      openLabel,
      heading: null,
      body: null,
    };
  }

  if (
    input.evidenceProvenanceHint ||
    input.emptyStateReason ||
    input.evidenceLinkCount > 0 ||
    input.extraArtifactCount > 0 ||
    input.reportArtifactId ||
    input.weakEvidenceSignals.length > 0
  ) {
    return {
      mode: "limited",
      closedLabel,
      openLabel,
      heading: "Supporting evidence is limited",
      body:
        input.evidenceProvenanceHint ??
        input.emptyStateReason ??
        "We checked for supporting evidence, but the mapped support for this answer is limited.",
    };
  }

  return {
    mode: "empty",
    closedLabel,
    openLabel,
    heading: "No mapped support is available",
    body: "Artifacts or mapped support were not available for this answer view.",
  };
}

function isGenericSuccessSummary(summary: string | null): boolean {
  if (!summary) return false;
  return /orchestration completed successfully/i.test(summary);
}

function buildEmptyStateReason(input: {
  orchestrationStatus: string | null;
  orchestrationMessage: string | null;
  summaryLine: string | null;
  takeawaysCount: number;
  alignmentFindingsCount: number;
  anomalyCount: number | null;
  panelRowCount: number | null;
  reportCharacterCount: number | null;
  reportArtifactId: string | null;
  evidenceLinkCount: number;
  extraArtifactCount: number;
}): string | null {
  if (input.takeawaysCount > 0 || input.alignmentFindingsCount > 0) {
    return null;
  }

  if (input.orchestrationStatus === "no_data") {
    return input.orchestrationMessage?.trim() || "No usable SEC data was returned for the selected scope.";
  }

  if (input.panelRowCount === 0) {
    return "The pipeline completed, but the panel was empty for the selected scope.";
  }

  if (input.anomalyCount === 0) {
    return "The pipeline completed, but it did not surface any anomaly rows for this scope.";
  }

  if ((input.reportCharacterCount ?? 0) > 0 && input.reportArtifactId) {
    return "The run completed and produced a report, but no structured findings were extracted into this answer card.";
  }

  if (input.reportArtifactId && input.evidenceLinkCount === 0) {
    return "The run completed and produced artifacts, but the evidence map for this view is still empty.";
  }

  if (input.extraArtifactCount > 0 && input.evidenceLinkCount === 0) {
    return "The run completed and produced artifacts, but none have been mapped into structured evidence for this view yet.";
  }

  if (input.orchestrationMessage?.trim() && !/completed successfully/i.test(input.orchestrationMessage)) {
    return input.orchestrationMessage.trim();
  }

  if (isGenericSuccessSummary(input.summaryLine)) {
    return "The run completed successfully, but it did not surface a user-facing summary for this request.";
  }

  return null;
}

function buildChatEvidenceNavigation(
  nav: PrimaryAnswerNavContext | undefined,
  reportArtifactId: string | null,
): ChatEvidenceNavItem[] {
  if (!nav) return [];
  const traceHref = `/projects/${nav.projectId}/runs/${nav.runId}/trace`;
  const artifactHref = tracePath(nav, "#run-artifacts");
  const criticHref = tracePath(nav, "#run-agents");

  return [
    { key: "report", label: "Report", href: reportArtifactId ? `/artifacts/${reportArtifactId}` : artifactHref },
    { key: "evidence", label: "Evidence", href: artifactHref },
    { key: "artifacts", label: "Artifacts", href: artifactHref },
    { key: "critic", label: "Critic", href: criticHref },
    { key: "trace", label: "Trace", href: traceHref },
  ];
}

function evidenceFromTraceability(
  tr: TraceabilityWire | undefined,
  transparency: RunTransparencySummary | null | undefined,
  artifacts: ArtifactMetadata[],
): { links: EvidenceLink[]; reportArtifactId: string | null } {
  const byRole = tr?.evidence_artifacts_by_role ?? transparency?.evidence_artifacts_by_role;
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

function buildLegacyNarrativeAnswer(input: {
  rawSummaryLine: string | null;
  takeaways: string[];
  emptyStateReason: string | null;
  blockingCaveats: string[];
}): NarrativeAnswerView {
  const thesis =
    (input.rawSummaryLine && !isGenericSuccessSummary(input.rawSummaryLine) ? input.rawSummaryLine : null) ??
    input.takeaways[0] ??
    input.emptyStateReason ??
    "Analysis completed, but the narrative preview is not available for this run.";

  const supportTakeaway = input.takeaways.find((row) => row !== thesis) ?? null;
  const weakSignal = input.emptyStateReason ?? input.blockingCaveats[0] ?? null;
  const sectionBody = supportTakeaway ?? weakSignal;
  const sectionHeading =
    input.emptyStateReason || input.blockingCaveats.length > 0
      ? "What weakens the claim"
      : "Why we think that";

  return {
    mode: "legacy",
    thesis,
    sections: sectionBody ? [{ heading: sectionHeading, body: sectionBody }] : [],
    fallbackReason: "legacy_summary",
  };
}

const INLINE_CHART_KINDS = new Set<InlineChartView["kind"]>(["line", "grouped_bar"]);
const INLINE_CHART_COLOR_TOKENS = new Set<InlineChartSeriesView["colorToken"]>([
  "chart-1",
  "chart-2",
  "chart-3",
  "chart-4",
]);
const INLINE_CHART_VALUE_FORMATS = new Set<InlineChartView["valueFormat"]>([
  "currency",
  "percent",
  "ratio",
  "count",
  "number",
]);
const INLINE_CHART_NOTICE =
  "Chart preview unavailable. Read the answer text, then open supporting evidence or trace to inspect the underlying run artifacts.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function mapInlineCharts(transparency: RunTransparencySummary | null | undefined): {
  charts: InlineChartView[];
  notice: string | null;
} {
  // Render only backend-authored transparency.inline_charts previews; never infer charts client-side.
  const previews = transparency?.inline_charts ?? [];

  if (!Array.isArray(previews)) {
    return { charts: [], notice: null };
  }
  if (previews.length === 0) {
    return { charts: [], notice: null };
  }

  const charts: InlineChartView[] = [];

  for (const preview of previews) {
    if (!preview || !INLINE_CHART_KINDS.has(preview.kind)) {
      continue;
    }

    if (!INLINE_CHART_VALUE_FORMATS.has(preview.value_format)) {
      continue;
    }

    const chartId = typeof preview.chart_id === "string" ? preview.chart_id.trim() : "";
    const metricKey = typeof preview.metric_key === "string" ? preview.metric_key.trim() : "";
    const metricLabel = typeof preview.metric_label === "string" ? preview.metric_label.trim() : "";
    const caption = typeof preview.caption === "string" ? preview.caption.trim() : "";
    const xAxisLabel = typeof preview.x_axis_label === "string" ? preview.x_axis_label.trim() : "";
    const yAxisLabel = typeof preview.y_axis_label === "string" ? preview.y_axis_label.trim() : "";

    if (!chartId || !metricKey || !metricLabel || !caption || !xAxisLabel || !yAxisLabel) {
      continue;
    }

    const series = Array.isArray(preview.series)
      ? preview.series
          .map((item) => {
            const key = typeof item.key === "string" ? item.key.trim() : "";
            const label = typeof item.label === "string" ? item.label.trim() : "";
            const colorToken = item.color_token;

            if (!key || !label || !INLINE_CHART_COLOR_TOKENS.has(colorToken)) {
              return null;
            }

            return {
              key,
              label,
              colorToken,
            } satisfies InlineChartSeriesView;
          })
          .filter((item): item is InlineChartSeriesView => item !== null)
      : [];

    if (!series.length) {
      continue;
    }

    const rows = Array.isArray(preview.rows)
      ? preview.rows
          .map((row) => {
            const xValue = typeof row.x_value === "string" ? row.x_value.trim() : "";
            if (!xValue || !isRecord(row.values)) {
              return null;
            }

            const values = Object.fromEntries(
              series.map((item) => {
                const value = row.values[item.key];
                return [item.key, typeof value === "number" && Number.isFinite(value) ? value : null];
              }),
            );

            const hasSeriesValue = Object.values(values).some((value) => typeof value === "number");
            if (!hasSeriesValue) {
              return null;
            }

            return {
              xValue,
              values,
            };
          })
          .filter((item): item is InlineChartView["rows"][number] => item !== null)
      : [];

    if (!rows.length) {
      continue;
    }

    const markers = Array.isArray(preview.markers)
      ? preview.markers
          .map((marker) => {
            const xValue = typeof marker.x_value === "string" ? marker.x_value.trim() : "";
            const label = typeof marker.label === "string" ? marker.label.trim() : "";

            if (!xValue || !label) {
              return null;
            }

            return {
              xValue,
              label,
            } satisfies InlineChartMarkerView;
          })
          .filter((item): item is InlineChartMarkerView => item !== null)
      : [];

    charts.push({
      chartId,
      kind: preview.kind,
      metricKey,
      metricLabel,
      caption,
      xAxisLabel,
      yAxisLabel,
      valueFormat: preview.value_format,
      series,
      rows,
      markers,
    });
  }

  const boundedCharts = charts.slice(0, 2);
  return {
    charts: boundedCharts,
    notice: boundedCharts.length === 0 ? INLINE_CHART_NOTICE : null,
  };
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
  transparency?: RunTransparencySummary | null,
  nav?: PrimaryAnswerNavContext,
): PrimaryAnswerView {
  const suggestionGoalText =
    (input.orchestration_goal_text && input.orchestration_goal_text.trim()) ||
    inputGoalText(input.input_payload_json) ||
    "";

  const goalDisplay = suggestionGoalText || "—";

  const inputTickers = parseInputTickers(input.input_payload_json);

  const rawSummaryLine =
    (orch?.final_summary && orch.final_summary.trim()) ||
    (orch?.message && orch.message.trim()) ||
    null;

  const orchestrationStatus = orch?.status ?? null;

  const tr = ai?.traceability;
  const preview = tr?.report?.key_takeaways_preview;
  const previewList = Array.isArray(preview)
    ? preview.filter((x): x is string => typeof x === "string")
    : transparency?.report_key_takeaways_preview ?? [];
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
    typeof tr?.critic?.overall_confidence === "string"
      ? tr.critic.overall_confidence
      : transparency?.critic_overall_confidence ?? null;
  const blockingCaveats = Array.isArray(tr?.critic?.blocking_caveats)
    ? tr!.critic!.blocking_caveats!
        .filter((x): x is string => typeof x === "string")
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, 5)
    : (transparency?.critic_blocking_caveats ?? []).slice(0, 5);

  const criticPhaseStatus =
    typeof tr?.critic?.phase_status === "string"
      ? tr.critic.phase_status
      : typeof transparency?.critic_phase_status === "string"
        ? transparency.critic_phase_status
      : typeof orch?.llm_phases_summary?.critic?.phase_status === "string"
        ? orch.llm_phases_summary!.critic!.phase_status!
        : null;
  const reportPhaseStatus =
    typeof tr?.report?.phase_status === "string"
      ? tr.report.phase_status
      : typeof transparency?.report_phase_status === "string"
        ? transparency.report_phase_status
      : typeof orch?.llm_phases_summary?.report?.phase_status === "string"
        ? orch.llm_phases_summary!.report!.phase_status!
        : null;

  const { links, reportArtifactId } = evidenceFromTraceability(tr, transparency, artifacts);
  const linkedIds = new Set(links.map((l) => l.artifactId));
  const extraArtifactCount = artifacts.filter((a) => !linkedIds.has(a.id)).length;

  const weakEvidenceSignals = extractWeakEvidenceSignals(ai);
  const contextSignals = collectContextSignals(ai, orch);
  const confidenceExplainer = buildConfidenceExplainer(
    overallConfidence,
    transparency,
    tr,
    blockingCaveats,
    weakEvidenceSignals,
    contextSignals,
  );
  const { charts: inlineCharts, notice: inlineChartNotice } = mapInlineCharts(transparency);

  const hasCritic = hasCriticSurface(ai, tr) || hasCriticSurfaceFromTransparency(transparency);
  const takeawayChips = buildTakeawayChips(nav, reportArtifactId, links, artifacts.length, hasCritic, contextSignals);
  const takeawayRows = takeaways.map((text) => ({ text, chips: takeawayChips }));

  const pipelineSummary = orch?.tool_results_summary?.find((row) => row.tool_name === "run_pipeline") ?? null;
  const emptyStateReasonCandidate = buildEmptyStateReason({
    orchestrationStatus,
    orchestrationMessage: orch?.message?.trim() || null,
    summaryLine: rawSummaryLine,
    takeawaysCount: takeaways.length,
    alignmentFindingsCount: alignmentFindings.length,
    anomalyCount: typeof pipelineSummary?.anomaly_count === "number" ? pipelineSummary.anomaly_count : null,
    panelRowCount: typeof pipelineSummary?.panel_row_count === "number" ? pipelineSummary.panel_row_count : null,
    reportCharacterCount:
      typeof pipelineSummary?.report_character_count === "number" ? pipelineSummary.report_character_count : null,
    reportArtifactId,
    evidenceLinkCount: links.length,
    extraArtifactCount,
  });
  const transparencyNarrative = transparency?.narrative_answer;
  const narrativeAnswer: NarrativeAnswerView = transparencyNarrative
    ? {
        mode: transparencyNarrative.mode,
        thesis: transparencyNarrative.thesis,
        sections: transparencyNarrative.sections.map((section) => ({
          heading: section.heading,
          body: section.body,
        })),
        fallbackReason: transparencyNarrative.fallback_reason,
      }
    : buildLegacyNarrativeAnswer({
        rawSummaryLine,
        takeaways,
        emptyStateReason: emptyStateReasonCandidate,
        blockingCaveats,
      });
  const summaryLine = narrativeAnswer.thesis;
  const emptyStateReason = transparencyNarrative ? null : emptyStateReasonCandidate;

  const conclusionRider = buildConclusionRider(blockingCaveats, weakEvidenceSignals, nav);
  const evidenceProvenanceHint = buildEvidenceProvenanceHint(
    weakEvidenceSignals,
    contextSignals,
    extraArtifactCount,
    links.length,
  );
  const supplementalEvidence = buildSupplementalEvidence(takeawayRows, alignmentFindings);
  const supplementalEvidenceState = buildSupplementalEvidenceState({
    supplementalEvidence,
    emptyStateReason,
    evidenceProvenanceHint,
    evidenceLinkCount: links.length,
    extraArtifactCount,
    reportArtifactId,
    weakEvidenceSignals,
  });

  return {
    goalDisplay,
    narrativeAnswer,
    summaryLine,
    orchestrationStatus,
    emptyStateReason,
    takeawayRows,
    alignmentFindings,
    supplementalEvidence,
    supplementalEvidenceState,
    overallConfidence,
    confidenceExplainer,
    blockingCaveats,
    criticPhaseStatus,
    reportPhaseStatus,
    inlineCharts,
    inlineChartNotice,
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
    narrativeAnswer: view.narrativeAnswer,
    summaryLine: view.summaryLine,
    orchestrationStatus: view.orchestrationStatus,
    emptyStateReason: view.emptyStateReason,
    conclusionRider: view.conclusionRider,
  };
}

export function buildChatAnswerCardView(
  view: PrimaryAnswerView,
  nav?: PrimaryAnswerNavContext,
): ChatAnswerCardView {
  return {
    goalDisplay: view.goalDisplay,
    narrativeAnswer: view.narrativeAnswer,
    summaryLine: view.summaryLine,
    orchestrationStatus: view.orchestrationStatus,
    emptyStateReason: view.emptyStateReason,
    conclusionRider: view.conclusionRider,
    takeawayRows: view.takeawayRows,
    alignmentFindings: view.alignmentFindings,
    supplementalEvidence: view.supplementalEvidence,
    supplementalEvidenceState: view.supplementalEvidenceState,
    overallConfidence: view.overallConfidence,
    confidenceExplainer: view.confidenceExplainer,
    blockingCaveats: view.blockingCaveats,
    criticPhaseStatus: view.criticPhaseStatus,
    reportPhaseStatus: view.reportPhaseStatus,
    inlineCharts: view.inlineCharts,
    inlineChartNotice: view.inlineChartNotice,
    weakEvidenceSignals: view.weakEvidenceSignals,
    contextSignals: view.contextSignals,
    evidenceLinks: view.evidenceLinks,
    extraArtifactCount: view.extraArtifactCount,
    reportArtifactId: view.reportArtifactId,
    evidenceProvenanceHint: view.evidenceProvenanceHint,
    navigationItems: buildChatEvidenceNavigation(nav, view.reportArtifactId),
    traceHref: nav ? `/projects/${nav.projectId}/runs/${nav.runId}/trace` : null,
    caveatOverflowHref: nav ? tracePath(nav, "#run-context-transparency") : null,
  };
}
