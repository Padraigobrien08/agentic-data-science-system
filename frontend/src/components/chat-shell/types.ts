/**
 * EDGAR chat shell — provider-agnostic. Assistant turns are **not** plain prose;
 * they are containers for structured output (implemented in a follow-up).
 */

import type { AnalysisRunStatus, BackgroundDeliveryHealth, BackgroundDeliveryMode } from "@/lib/api/types";
import type { ComposedAnswer } from "@/lib/demo-answer";
import type { PipelinePhaseView } from "@/lib/run-pipeline-phases";
import type { ChatAnswerCardView } from "@/lib/run-primary-view";

export type ChatUserMessage = {
  id: string;
  role: "user";
  content: string;
  createdAt: string;
};

export type ChatSystemMessage = {
  id: string;
  role: "system";
  content: string;
  createdAt: string;
};

export type ChatAssistantMessage = {
  id: string;
  role: "assistant";
  content: string;
  rewriteSuggestions?: string[];
  routingReason?: string;
  answerCard?: ChatAnswerCardView;
  /**
   * A recorded run's answer, composed from persisted investigation state. Set only on the
   * replay tier, where there is no run view model to build an `answerCard` from.
   */
  recordedAnswer?: ComposedAnswer;
  runId?: string;
  runHref?: string;
  deepDiveHref?: string;
  runsHref?: string;
  runStatus?: AnalysisRunStatus;
  runCreatedAt?: string;
  runFinishedAt?: string | null;
  pending?: boolean;
  /** Live pipeline-phase progress while the run executes (polled). */
  phaseView?: PipelinePhaseView;
  deliveryMode?: BackgroundDeliveryMode;
  deliveryDetail?: string;
  reroutedFromBackground?: boolean;
  createdAt: string;
};

export type ChatMessage = ChatUserMessage | ChatSystemMessage | ChatAssistantMessage;

export type ChatRecentRun = {
  id: string;
  status: AnalysisRunStatus;
  title: string;
  preview?: string | null;
  createdAt: string;
  scrollTargetId?: string;
};

export type ChatThreadSummary = {
  id: string;
  title: string;
  href: string;
  hasMessages: boolean;
  updatedAt: string;
};

export type ChatBackgroundDelivery = BackgroundDeliveryHealth;
