import type { AnalysisRunStatus } from "@/lib/api/types";
import type { PrimaryContextSignal } from "@/lib/primary-answer-signals";
import type { AlignmentFindingCard, EvidenceLink, TakeawayRow } from "@/lib/run-primary-view";

export type { TakeawayRow };

export type { PrimaryContextSignal };

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
};

export type FindingCardsProps = {
  findings: AlignmentFindingCard[];
  className?: string;
};

export type ConfidenceStripProps = {
  overallConfidence: string | null;
  criticPhaseStatus: string | null;
  reportPhaseStatus: string | null;
  /** Single muted line when budgets / weak evidence imply reduced certainty. */
  reliabilityNote?: string | null;
  className?: string;
};

export type EvidenceSummaryProps = {
  links: EvidenceLink[];
  extraArtifactCount: number;
  provenanceHint?: string | null;
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
  className?: string;
};

export type DeepDiveActionsProps = {
  traceHref: string;
  reportArtifactId: string | null;
  chatHref: string;
  runsHref: string;
  className?: string;
};
