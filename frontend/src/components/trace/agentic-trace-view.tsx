import { RunStepTrace } from "@/components/runs/run-step-trace";
import { AgentModelStepsPanel } from "@/components/trace/agent-model-steps-panel";
import { ArtifactsMetadataPanel } from "@/components/trace/artifacts-metadata-panel";
import { DeepDiveLayout } from "@/components/trace/deep-dive-layout";
import type { DeepDiveNavItem } from "@/components/trace/deep-dive-nav-config";
import { PlannerOutputPanel } from "@/components/trace/planner-output-panel";
import { RunTraceCollectionPanelProps } from "@/components/trace/run-trace-collection-panel";
import { RunTraceExperience } from "@/components/trace/run-trace-experience";
import { RunTraceSummaryView } from "@/components/trace/run-trace-summary-view";
import { ToolSequencePanel } from "@/components/trace/tool-sequence-panel";
import type {
  AnalysisRunStatus,
  ArtifactMetadata,
  ModelCallApiItem,
  RunStepDetail,
  RunTraceRawDetail,
  RunTraceShell,
} from "@/lib/api/types";

type Props = {
  projectId: string;
  runId: string;
  shell: RunTraceShell;
  collectionPanel: RunTraceCollectionPanelProps;
  runAnswerHref: string;
  activeCollection: "steps" | "artifacts" | "model-calls";
  collectionError?: string | null;
  rawDetail?: RunTraceRawDetail | null;
};

const SUMMARY_NAV: DeepDiveNavItem[] = [
  { href: "#trace-overview", label: "Overview" },
  { href: "#trace-timeline", label: "Timeline" },
  { href: "#trace-collections", label: "Collections" },
  { href: "#trace-inspector", label: "Inspector" },
  { href: "#legacy-audit-stack", label: "Legacy stack" },
];

function mergeById<T extends { id: string }>(primary: T[], secondary: T[]): T[] {
  const merged = new Map<string, T>();
  for (const item of primary) merged.set(item.id, item);
  for (const item of secondary) {
    if (!merged.has(item.id)) merged.set(item.id, item);
  }
  return [...merged.values()];
}

function deriveLegacyCollections(
  shell: RunTraceShell,
  collectionPanel: RunTraceCollectionPanelProps,
): {
  steps: RunStepDetail[];
  artifacts: ArtifactMetadata[];
  modelCalls: ModelCallApiItem[];
} {
  const stepItems =
    collectionPanel.collection === "steps"
      ? collectionPanel.items
      : shell.steps.items;
  const artifactItems =
    collectionPanel.collection === "artifacts"
      ? collectionPanel.items
      : shell.artifacts.items;
  const modelCallItems =
    collectionPanel.collection === "model-calls"
      ? collectionPanel.items
      : shell.model_calls.items;

  return {
    steps: mergeById(shell.timeline_preview, stepItems as RunStepDetail[]),
    artifacts: mergeById(shell.artifacts.items, artifactItems as ArtifactMetadata[]),
    modelCalls: mergeById(shell.model_calls.items, modelCallItems as ModelCallApiItem[]),
  };
}

/**
 * Summary-first trace surface with the dense legacy audit stack pushed below the fold.
 */
export function AgenticTraceView({
  projectId,
  runId,
  shell,
  collectionPanel,
  runAnswerHref,
  activeCollection,
  collectionError,
  rawDetail,
}: Props) {
  const legacy = deriveLegacyCollections(shell, collectionPanel);
  const includeLlmUsageAnchor = !!shell.transparency;

  return (
    <div className="space-y-8">
      <DeepDiveLayout includeLlmUsageAnchor={false} navItems={SUMMARY_NAV}>
        <RunTraceSummaryView
          projectId={projectId}
          runId={runId}
          shell={shell}
          activeCollection={activeCollection}
          collectionPanel={collectionPanel}
          runAnswerHref={runAnswerHref}
          errorMessage={collectionError}
          rawDetail={rawDetail}
        />
      </DeepDiveLayout>

      <details
        id="legacy-audit-stack"
        className="rounded-[28px] border border-[var(--border)] bg-[var(--surface-strong)]"
      >
        <summary className="cursor-pointer select-none border-b border-[var(--border)] px-5 py-4 text-sm font-semibold text-[var(--foreground)]">
          Legacy audit stack and technical inspector
        </summary>
        <div className="space-y-6 p-5">
          <DeepDiveLayout includeLlmUsageAnchor={includeLlmUsageAnchor}>
            <RunTraceExperience
              projectId={projectId}
              runId={runId}
              orch={null}
              ai={null}
              steps={legacy.steps}
              artifacts={legacy.artifacts}
              modelCalls={legacy.modelCalls}
              userFacingReport={null}
              compactTraceLink
              runStatus={shell.run.status as AnalysisRunStatus}
              runErrorSummary={shell.run.error_summary}
              runTransparency={shell.transparency}
            />
          </DeepDiveLayout>

          <details className="rounded-[24px] border border-[var(--border)] bg-[var(--surface)]">
            <summary className="cursor-pointer select-none border-b border-[var(--border)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--foreground)]">
              Technical inspector
            </summary>
            <div className="space-y-4 p-4">
              <PlannerOutputPanel orch={null} ai={null} />
              <ToolSequencePanel orch={null} />
              <AgentModelStepsPanel ai={null} />
              <SectionPersistedSteps projectId={projectId} runId={runId} steps={legacy.steps} />
              <ArtifactsMetadataPanel
                projectId={projectId}
                runId={runId}
                artifacts={legacy.artifacts}
                orchestrationPaths={null}
              />
            </div>
          </details>
        </div>
      </details>
    </div>
  );
}

function SectionPersistedSteps({
  projectId,
  runId,
  steps,
}: {
  projectId: string;
  runId: string;
  steps: RunStepDetail[];
}) {
  return (
    <div className="rounded-[24px] border border-[var(--border)] bg-[var(--surface)]">
      <header className="border-b border-[var(--border)] px-4 py-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--foreground)]">
          Persisted run steps
        </h2>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Slim step rows stay available here for lower-level inspection without making them the first-load experience.
        </p>
      </header>
      <div className="p-4">
        <RunStepTrace projectId={projectId} runId={runId} steps={steps} />
      </div>
    </div>
  );
}
