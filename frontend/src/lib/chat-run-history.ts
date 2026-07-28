import type {
  ChatAssistantMessage,
  ChatMessage,
  ChatRecentRun,
  ChatThreadSummary,
  ChatUserMessage,
} from "@/components/chat-shell/types";
import { parseAiAgents } from "@/lib/ai-agents-meta";
import { getConversation, listConversations } from "@/lib/api/conversations";
import { listProjects } from "@/lib/api/projects";
import { getRun, listRunArtifacts, listRuns } from "@/lib/api/runs";
import type {
  AnalysisRunDetail,
  AnalysisRunSummary,
  ChatMessageRead,
  ConversationRead,
  ProjectRead,
} from "@/lib/api/types";
import { parseOrchestrationOutput, parseUserFacingReport } from "@/lib/orchestration-output";
import { buildChatAnswerCardView, buildPrimaryAnswerView } from "@/lib/run-primary-view";

type ProjectChatHistory = {
  messages: ChatMessage[];
  recentRuns: ChatRecentRun[];
  chatThreads: ChatThreadSummary[];
};

type ConversationChatHistory = {
  messages: ChatMessage[];
  chatThreads: ChatThreadSummary[];
};

function goalText(run: AnalysisRunDetail): string {
  if (run.orchestration_goal_text?.trim()) {
    return run.orchestration_goal_text.trim();
  }
  const input = run.input_payload_json;
  if (input && typeof input === "object" && !Array.isArray(input)) {
    const analysisGoal = (input as Record<string, unknown>).analysis_goal;
    if (typeof analysisGoal === "string" && analysisGoal.trim()) {
      return analysisGoal.trim();
    }
  }
  return "Analysis run";
}

function buildAssistantMessage(
  projectId: string,
  run: AnalysisRunDetail,
  artifacts: Awaited<ReturnType<typeof listRunArtifacts>>,
): ChatAssistantMessage {
  const orch = parseOrchestrationOutput(run.output_payload_json);
  const userReport = parseUserFacingReport(run.output_payload_json);
  const ai = parseAiAgents(run.meta_json);
  const nav = {
    projectId,
    runId: run.id,
  };
  const answerView = buildPrimaryAnswerView(
    run,
    artifacts,
    orch,
    userReport,
    ai,
    run.transparency,
    nav,
  );
  const answerCard = buildChatAnswerCardView(answerView, nav);
  const fallbackContent =
    run.error_summary?.trim() ||
    (run.status === "error"
      ? "Run ended with an error before a summary was produced."
      : answerView.emptyStateReason ?? "Run completed without a narrative preview.");

  return {
    id: `assist-${run.id}`,
    role: "assistant",
    content: answerCard.narrativeAnswer.thesis ?? answerCard.emptyStateReason ?? fallbackContent,
    answerCard,
    runId: run.id,
    runHref: `/projects/${projectId}/runs/${run.id}/trace`,
    runStatus: run.status,
    runCreatedAt: run.created_at,
    runFinishedAt: run.finished_at,
    createdAt: run.finished_at ?? run.created_at,
  };
}

function compactHistoryTitle(text: string): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= 56) {
    return normalized;
  }
  return `${normalized.slice(0, 53).trimEnd()}...`;
}

function summaryGoalText(run: Pick<AnalysisRunDetail, "orchestration_goal_text">): string {
  return run.orchestration_goal_text?.trim() || "Analysis run";
}

function projectThreadFallbackTitle(project: Pick<ProjectRead, "name" | "tickers">): string {
  if (project.name.trim()) {
    return project.name.trim();
  }
  if (project.tickers?.length) {
    return `${project.tickers[0]} chat`;
  }
  return "New chat";
}

function buildChatThreadSummary(project: ProjectRead, runs: AnalysisRunSummary[]): ChatThreadSummary {
  const sortedRuns = [...runs].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  const firstRun = sortedRuns[0] ?? null;
  const lastRun = sortedRuns.at(-1) ?? null;
  const titleSource = firstRun ? summaryGoalText(firstRun) : projectThreadFallbackTitle(project);
  const updatedAt = lastRun?.updated_at ?? project.updated_at;

  return {
    id: project.id,
    title: compactHistoryTitle(titleSource),
    href: `/projects/${project.id}/chat`,
    hasMessages: runs.length > 0,
    updatedAt,
  };
}

function buildUserMessage(run: AnalysisRunDetail): ChatUserMessage {
  return {
    id: `user-${run.id}`,
    role: "user",
    content: goalText(run),
    createdAt: run.created_at,
  };
}

export async function buildProjectChatHistory(projectId: string, limit = 12): Promise<ProjectChatHistory> {
  const [runs, projects] = await Promise.all([listRuns(projectId), listProjects()]);
  const recentRunsSorted = [...runs]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, limit);

  const hydratedRuns = await Promise.all(
    recentRunsSorted.map(async (run) => ({
      run: await getRun(run.id, { includeTransparency: true }),
      artifacts: await listRunArtifacts(run.id),
    })),
  );

  const chronologicalRuns = [...hydratedRuns].sort(
    (a, b) => new Date(a.run.created_at).getTime() - new Date(b.run.created_at).getTime(),
  );

  const pairedMessages = chronologicalRuns.map(({ run, artifacts }) => {
    const userMessage = buildUserMessage(run);
    const assistantMessage = buildAssistantMessage(projectId, run, artifacts);
    return { run, userMessage, assistantMessage };
  });

  const messages = pairedMessages.flatMap(({ userMessage, assistantMessage }) => [userMessage, assistantMessage]);

  const recentRuns: ChatRecentRun[] = recentRunsSorted.map((run) => {
    return {
      id: run.id,
      status: run.status,
      title: compactHistoryTitle(summaryGoalText(run)),
      preview: null,
      createdAt: run.created_at,
      scrollTargetId: `answer-${run.id}`,
    };
  });

  const chatThreads = (
    await Promise.all(
      projects.map(async (project) => ({
        project,
        runs: project.id === projectId ? runs : await listRuns(project.id),
      })),
    )
  )
    .map(({ project, runs: projectRuns }) => buildChatThreadSummary(project, projectRuns))
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, limit);

  return { messages, recentRuns, chatThreads };
}

function metaStringList(meta: ChatMessageRead["meta_json"], key: string): string[] | undefined {
  if (!meta || typeof meta !== "object" || Array.isArray(meta)) return undefined;
  const value = (meta as Record<string, unknown>)[key];
  if (!Array.isArray(value)) return undefined;
  const list = value.filter((v): v is string => typeof v === "string");
  return list.length > 0 ? list : undefined;
}

function metaString(meta: ChatMessageRead["meta_json"], key: string): string | undefined {
  if (!meta || typeof meta !== "object" || Array.isArray(meta)) return undefined;
  const value = (meta as Record<string, unknown>)[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

/** A persisted assistant turn with no linked run (e.g. "couldn't route yet"). */
function plainAssistantMessage(message: ChatMessageRead): ChatAssistantMessage {
  return {
    id: `msg-${message.id}`,
    role: "assistant",
    content: message.content ?? message.error_summary ?? "",
    rewriteSuggestions: metaStringList(message.meta_json, "rewrite_suggestions"),
    routingReason: metaString(message.meta_json, "routing_reason"),
    createdAt: message.created_at,
  };
}

function buildThreadSummaryFromConversation(
  projectId: string,
  conversation: ConversationRead,
): ChatThreadSummary {
  return {
    id: conversation.id,
    title: compactHistoryTitle(conversation.title?.trim() || "New chat"),
    href: `/projects/${projectId}/chat/${conversation.id}`,
    hasMessages: conversation.last_message_at !== null,
    updatedAt: conversation.last_message_at ?? conversation.updated_at,
  };
}

/**
 * Durable history for one conversation. User/system turns render from stored content;
 * assistant turns rehydrate their rich answer card from the linked analysis run.
 */
export async function buildConversationHistory(
  projectId: string,
  conversationId: string,
): Promise<ConversationChatHistory> {
  const [detail, conversations] = await Promise.all([
    getConversation(conversationId),
    listConversations(projectId),
  ]);

  const messages: ChatMessage[] = await Promise.all(
    detail.messages.map(async (message): Promise<ChatMessage> => {
      if (message.role === "assistant") {
        if (message.analysis_run_id) {
          try {
            const [run, artifacts] = await Promise.all([
              getRun(message.analysis_run_id, { includeTransparency: true }),
              listRunArtifacts(message.analysis_run_id),
            ]);
            return buildAssistantMessage(projectId, run, artifacts);
          } catch {
            // Run was compacted or deleted — fall back to the stored narrative.
            return plainAssistantMessage(message);
          }
        }
        return plainAssistantMessage(message);
      }
      return {
        id: `msg-${message.id}`,
        role: message.role,
        content: message.content ?? "",
        createdAt: message.created_at,
      };
    }),
  );

  const chatThreads = conversations
    .map((conversation) => buildThreadSummaryFromConversation(projectId, conversation))
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());

  return { messages, chatThreads };
}
