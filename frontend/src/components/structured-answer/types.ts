import type { AnalysisRunStatus } from "@/lib/api/types";
import type { PrimaryContextSignal } from "@/lib/primary-answer-signals";
import type {
  AlignmentFindingCard,
  ConfidenceExplainerView,
  EvidenceLink,
  SupplementalEvidenceRow,
  SupplementalEvidenceState,
  TakeawayRow,
} from "@/lib/run-primary-view";

export type { TakeawayRow };
export type { SupplementalEvidenceRow, SupplementalEvidenceState };

export type { PrimaryContextSignal };

export type InlineEvidenceChartSeries = {
  key: string;
  label: string;
  colorToken: "chart-1" | "chart-2" | "chart-3" | "chart-4";
};

export type InlineEvidenceChartRow = {
  xValue: string;
  values: Record<string, number | null>;
};

export type InlineEvidenceChartMarker = {
  xValue: string;
  label: string;
};

export type InlineEvidenceChart = {
  chartId: string;
  kind: "line" | "grouped_bar";
  metricKey: string;
  metricLabel: string;
  caption: string;
  xAxisLabel: string;
  yAxisLabel: string;
  valueFormat: "currency" | "percent" | "ratio" | "count" | "number";
  series: InlineEvidenceChartSeries[];
  rows: InlineEvidenceChartRow[];
  markers: InlineEvidenceChartMarker[];
};

export type InlineEvidenceChartsProps = {
  charts: InlineEvidenceChart[];
  notice?: string | null;
  className?: string;
};

export type AnswerSummaryProps = {
  goalDisplay: string;
  summaryLine: string | null;
  orchestrationStatus: string | null;
  runStatus: AnalysisRunStatus;
  /** Critic caveat or weak-evidence line with link into deep dive (critic section). */
  conclusionRider?: { text: string; href: string } | null;
  className?: string;
};

export type TopFindingsListProps = {
  items: TakeawayRow[];
  className?: string;
  chipMode?: "full" | "hidden" | "secondary";
  secondaryLinkLabel?: string;
};

export type FindingCardsProps = {
  findings: AlignmentFindingCard[];
  className?: string;
  chipMode?: "full" | "hidden" | "secondary";
  secondaryLinkLabel?: string;
};

export type ConfidenceStripProps = {
  overallConfidence: string | null;
  confidenceExplainer: ConfidenceExplainerView;
  /** Single muted line when budgets / weak evidence imply reduced certainty. */
  reliabilityNote?: string | null;
  className?: string;
};

export type EvidenceSummaryProps = {
  links: EvidenceLink[];
  extraArtifactCount: number;
  provenanceHint?: string | null;
  navItems?: { label: string; href: string }[];
  /** Shown with provenance hint as a follow-up action. */
  deepDiveHref?: string;
  /** When set, softens empty copy while the worker is still producing artifacts. */
  runStatus?: AnalysisRunStatus | null;
  className?: string;
};

export type CaveatBadgeGroupProps = {
  blockingCaveats: string[];
  weakEvidenceSignals: string[];
  contextSignals: PrimaryContextSignal[];
  /** Cap context badges on dense surfaces (primary page). */
  maxContextBadges?: number;
  maxWeakBadges?: number;
  /** Target for "+N" overflow chip (e.g. deep-dive context panel). */
  overflowHref?: string;
  blockingHref?: string;
  secondaryLinkLabel?: string;
  className?: string;
};

export type DeepDiveActionsProps = {
  traceHref: string;
  reportArtifactId: string | null;
  chatHref: string;
  className?: string;
};
