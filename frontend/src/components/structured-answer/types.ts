import type { AnalysisRunStatus } from "@/lib/api/types";
import type { PrimaryContextSignal } from "@/lib/primary-answer-signals";
import type { AlignmentFindingCard, EvidenceLink } from "@/lib/run-primary-view";

export type { PrimaryContextSignal };

export type AnswerSummaryProps = {
  goalDisplay: string;
  summaryLine: string | null;
  orchestrationStatus: string | null;
  isQueued: boolean;
  runStatus: AnalysisRunStatus;
  className?: string;
};

export type TopFindingsListProps = {
  items: string[];
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
  className?: string;
};

export type EvidenceSummaryProps = {
  links: EvidenceLink[];
  extraArtifactCount: number;
  className?: string;
};

export type CaveatBadgeGroupProps = {
  blockingCaveats: string[];
  weakEvidenceSignals: string[];
  contextSignals: PrimaryContextSignal[];
  className?: string;
};

export type DeepDiveActionsProps = {
  traceHref: string;
  reportArtifactId: string | null;
  chatHref: string;
  runsHref: string;
  className?: string;
};
