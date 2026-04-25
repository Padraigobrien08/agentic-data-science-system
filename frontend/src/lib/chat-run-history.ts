import type { ChatAssistantMessage, ChatMessage, ChatRecentRun, ChatUserMessage } from "@/components/chat-shell/types";
import { parseAiAgents } from "@/lib/ai-agents-meta";
import { getRun, listRunArtifacts, listRuns } from "@/lib/api/runs";
import type { AnalysisRunDetail } from "@/lib/api/types";
import { parseOrchestrationOutput, parseUserFacingReport } from "@/lib/orchestration-output";
import { buildChatAnswerCardView, buildPrimaryAnswerView } from "@/lib/run-primary-view";

type ProjectChatHistory = {
  messages: ChatMessage[];
  recentRuns: ChatRecentRun[];
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

function historyTitle(fallbackTitle: string, assistant: ChatAssistantMessage): string {
  const thesis = assistant.answerCard?.narrativeAnswer.thesis?.trim();
  if (thesis) {
    return thesis;
  }
  return fallbackTitle;
}

function historyPreview(assistant: ChatAssistantMessage): string | null {
  const section = assistant.answerCard?.narrativeAnswer.sections[0]?.body?.trim();
  if (section) {
    return section;
  }
  const rider = assistant.answerCard?.conclusionRider?.text?.trim();
  if (rider) {
    return rider;
  }
  return null;
}

function summaryGoalText(run: Pick<AnalysisRunDetail, "orchestration_goal_text">): string {
  return run.orchestration_goal_text?.trim() || "Analysis run";
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
  const runs = await listRuns(projectId);
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

  const assistantByRunId = new Map(
    pairedMessages.map(({ run, assistantMessage }) => [run.id, assistantMessage] as const),
  );

  const recentRuns: ChatRecentRun[] = recentRunsSorted.map((run) => {
    const assistant = assistantByRunId.get(run.id);
    return {
      id: run.id,
      status: run.status,
      title: assistant ? historyTitle(summaryGoalText(run), assistant) : summaryGoalText(run),
      preview: assistant ? historyPreview(assistant) : null,
      createdAt: run.created_at,
      scrollTargetId: `answer-${run.id}`,
    };
  });

  return { messages, recentRuns };
}
