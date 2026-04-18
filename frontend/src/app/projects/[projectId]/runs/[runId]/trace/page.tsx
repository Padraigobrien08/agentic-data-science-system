import Link from "next/link";
import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ProjectWorkspaceNav } from "@/components/layout/project-workspace-nav";
import { RunPipelinePhaseTrack } from "@/components/runs/run-pipeline-phase-track";
import { RunStateBanner } from "@/components/runs/run-state-banner";
import { AgenticTraceView } from "@/components/trace/agentic-trace-view";
import { StatusBadge } from "@/components/ui/technical";
import { ApiError } from "@/lib/api/errors";
import {
  getRunTraceSummary,
  listRunArtifacts,
  listRunModelCalls,
  listRunSteps,
} from "@/lib/api/runs";
import type {
  ArtifactKind,
  ArtifactMetadata,
  ModelCallApiItem,
  ModelCallStatus,
  RunStepDetail,
  RunStepStatus,
  TraceCollectionKey,
} from "@/lib/api/types";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

const DEFAULT_LIMIT = 8;
const STEP_STATUSES: RunStepStatus[] = ["pending", "running", "success", "skipped", "no_data", "error"];
const MODEL_CALL_STATUSES: ModelCallStatus[] = ["pending", "running", "success", "error", "cancelled"];
const ARTIFACT_KINDS: ArtifactKind[] = ["tabular", "document", "binary", "json", "other"];

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function normalizeCollection(value: string | undefined): TraceCollectionKey {
  if (value === "artifacts" || value === "model-calls") return value;
  return "steps";
}

function parsePositiveInt(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return Math.min(parsed, 50);
}

function parseOffset(value: string | undefined): number {
  const parsed = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(parsed) || parsed < 0) return 0;
  return parsed;
}

export default async function RunTracePage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ projectId: string; runId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const { projectId, runId } = await params;
  const qp = await searchParams;
  const activeCollection = normalizeCollection(firstValue(qp.collection));
  const limit = parsePositiveInt(firstValue(qp.limit), DEFAULT_LIMIT);
  const offset = parseOffset(firstValue(qp.offset));
  const focus = firstValue(qp.focus) ?? null;
  let shell;

  try {
    shell = await getRunTraceSummary(runId, {
      stepsLimit: 5,
      artifactsLimit: 4,
      modelCallsLimit: 4,
    });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Deep dive</h1>
          <SignInHint nextPath={`/projects/${projectId}/runs/${runId}/trace`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return <p className="font-mono text-sm text-red-700 dark:text-red-400">{msg}</p>;
  }

  if (shell.run.project_id !== projectId) {
    notFound();
  }

  const stepStatus = firstValue(qp.status);
  const trace = firstValue(qp.trace);
  const artifactRoleKey = firstValue(qp.role_key);
  const artifactKind = firstValue(qp.kind);
  const modelStatus = firstValue(qp.status);
  const promptId = firstValue(qp.prompt_id);
  const q = firstValue(qp.q);

  let collectionError: string | null = null;
  let stepItems: RunStepDetail[] = [];
  let artifactItems: ArtifactMetadata[] = [];
  let modelCallItems: ModelCallApiItem[] = [];

  try {
    if (activeCollection === "steps") {
      stepItems = await listRunSteps(runId, {
        includeTransparency: true,
        status: STEP_STATUSES.includes(stepStatus as RunStepStatus)
          ? (stepStatus as RunStepStatus)
          : undefined,
        trace,
        q,
        limit,
        offset,
      });
    } else if (activeCollection === "artifacts") {
      artifactItems = await listRunArtifacts(runId, {
        roleKey: artifactRoleKey,
        kind: ARTIFACT_KINDS.includes(artifactKind as ArtifactKind)
          ? (artifactKind as ArtifactKind)
          : undefined,
        includeDeleted: false,
        limit,
        offset,
      });
    } else {
      modelCallItems = await listRunModelCalls(runId, {
        status: MODEL_CALL_STATUSES.includes(modelStatus as ModelCallStatus)
          ? (modelStatus as ModelCallStatus)
          : undefined,
        promptId,
        q,
        limit,
        offset,
      });
    }
  } catch (e) {
    collectionError = e instanceof ApiError ? e.body || e.message : "Unknown error";
  }

  const collectionPanel =
    activeCollection === "steps"
      ? {
          projectId,
          runId,
          collection: "steps" as const,
          items: stepItems,
          status: STEP_STATUSES.includes(stepStatus as RunStepStatus)
            ? (stepStatus as RunStepStatus)
            : undefined,
          trace,
          q,
          limit,
          offset,
          hasMore: stepItems.length === limit,
          selectedId: focus,
        }
      : activeCollection === "artifacts"
        ? {
            projectId,
            runId,
            collection: "artifacts" as const,
            items: artifactItems,
            roleKey: artifactRoleKey,
            kind: ARTIFACT_KINDS.includes(artifactKind as ArtifactKind)
              ? (artifactKind as ArtifactKind)
              : undefined,
            limit,
            offset,
            hasMore: artifactItems.length === limit,
            selectedId: focus,
          }
        : {
            projectId,
            runId,
            collection: "model-calls" as const,
            items: modelCallItems,
            status: MODEL_CALL_STATUSES.includes(modelStatus as ModelCallStatus)
              ? (modelStatus as ModelCallStatus)
              : undefined,
            promptId,
            q,
            limit,
            offset,
            hasMore: modelCallItems.length === limit,
            selectedId: focus,
          };

  const runAnswerHref = `/projects/${projectId}/runs/${runId}`;

  return (
    <div className="space-y-6">
      <ProjectWorkspaceNav projectId={projectId} runId={runId} current="trace" />

      <header className="border-b border-[var(--border)] pb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
              Audit trail
            </p>
            <h1 className="text-xl font-semibold tracking-tight text-[var(--foreground)]">Deep dive</h1>
            <p className="max-w-prose text-xs leading-relaxed text-[var(--foreground)]">
              Summary-first trace inspection for large runs: open on the timeline, move through one collection at a time, and fetch raw payloads only when you explicitly inspect a single item.
            </p>
            <details className="max-w-prose text-[11px] leading-relaxed text-[var(--muted)]">
              <summary className="cursor-pointer font-medium text-[var(--foreground)] underline decoration-dotted underline-offset-2">
                How this differs from run answer
              </summary>
              <p className="mt-2">
                This page starts with the execution spine and collection summaries. Use{" "}
                <Link href={runAnswerHref} className="font-medium text-[var(--foreground)] underline">
                  run answer
                </Link>{" "}
                first for the conclusion, then return here to verify the evidence trail.
              </p>
            </details>
            <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
              <StatusBadge status={shell.run.status} variant="friendly" />
              <span className="hidden sm:inline">·</span>
              <span>
                {formatDate(shell.run.created_at)}
                {shell.run.finished_at ? ` → ${formatDate(shell.run.finished_at)}` : ""}
              </span>
            </div>
            <details className="text-[10px] text-[var(--muted)]">
              <summary className="cursor-pointer font-mono underline">Run id</summary>
              <p className="mt-1 break-all">{runId}</p>
            </details>
          </div>
          <div className="flex flex-shrink-0 flex-wrap gap-2">
            <Link
              href={runAnswerHref}
              className="rounded-full border border-[var(--border)] bg-[var(--foreground)] px-3 py-2 text-center text-sm font-medium text-[var(--background)]"
            >
              Run answer
            </Link>
            <Link
              href={`/projects/${projectId}/chat`}
              className="rounded-full border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--foreground)]"
            >
              Chat
            </Link>
            <Link
              href={`/projects/${projectId}/runs`}
              className="rounded-full border border-[var(--border)] px-3 py-2 text-sm text-[var(--muted)]"
            >
              All runs
            </Link>
          </div>
        </div>
      </header>

      <RunStateBanner status={shell.run.status} surface="trace" runAnswerHref={runAnswerHref} />

      <RunPipelinePhaseTrack status={shell.run.status} steps={shell.timeline_preview} />

      <AgenticTraceView
        projectId={projectId}
        runId={runId}
        shell={shell}
        collectionPanel={collectionPanel}
        runAnswerHref={runAnswerHref}
        activeCollection={activeCollection}
        collectionError={collectionError}
      />
    </div>
  );
}
