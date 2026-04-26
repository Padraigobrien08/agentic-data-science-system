import type {
  ChatAssistantMessage,
  ChatMessage,
  ChatRecentRun,
  ChatThreadSummary,
  ChatUserMessage,
} from "@/components/chat-shell/types";
import { parseAiAgents } from "@/lib/ai-agents-meta";
import { listProjects } from "@/lib/api/projects";
import { getRun, listRunArtifacts, listRuns } from "@/lib/api/runs";
import type { AnalysisRunDetail, AnalysisRunSummary, ProjectRead } from "@/lib/api/types";
import { parseOrchestrationOutput, parseUserFacingReport } from "@/lib/orchestration-output";
import { buildChatAnswerCardView, buildPrimaryAnswerView } from "@/lib/run-primary-view";

type ProjectChatHistory = {
  messages: ChatMessage[];
  recentRuns: ChatRecentRun[];
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
