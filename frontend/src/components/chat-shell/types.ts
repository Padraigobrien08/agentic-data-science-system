/**
 * EDGAR chat shell — provider-agnostic. Assistant turns are **not** plain prose;
 * they are containers for structured output (implemented in a follow-up).
 */

import type { AnalysisRunStatus, BackgroundDeliveryHealth, BackgroundDeliveryMode } from "@/lib/api/types";
import type { CompactChatAnswerView } from "@/lib/run-primary-view";

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
  answerCard?: CompactChatAnswerView;
  runId?: string;
  runHref?: string;
  deepDiveHref?: string;
  runsHref?: string;
  runStatus?: AnalysisRunStatus;
  runCreatedAt?: string;
  runFinishedAt?: string | null;
  pending?: boolean;
  deliveryMode?: BackgroundDeliveryMode;
  deliveryDetail?: string;
  reroutedFromBackground?: boolean;
  createdAt: string;
};

export type ChatMessage = ChatUserMessage | ChatSystemMessage | ChatAssistantMessage;

export type ChatRecentRun = {
  id: string;
  href: string;
  status: AnalysisRunStatus;
  goalDisplay: string;
  createdAt: string;
};

export type ChatBackgroundDelivery = BackgroundDeliveryHealth;
