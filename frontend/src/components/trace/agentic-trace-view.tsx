import { RunStepTrace } from "@/components/runs/run-step-trace";
import { AgentModelStepsPanel } from "@/components/trace/agent-model-steps-panel";
import { ArtifactsMetadataPanel } from "@/components/trace/artifacts-metadata-panel";
import { PlannerOutputPanel } from "@/components/trace/planner-output-panel";
import { ToolSequencePanel } from "@/components/trace/tool-sequence-panel";
import type { ArtifactMetadata, RunStepDetail } from "@/lib/api/types";
import { parseAiAgents } from "@/lib/ai-agents-meta";
import { parseOrchestrationOutput } from "@/lib/orchestration-output";

type Props = {
  projectId: string;
  runId: string;
  outputPayload: unknown;
  metaJson: unknown;
  steps: RunStepDetail[];
  artifacts: ArtifactMetadata[];
};

/**
 * Composed **transparent** trace: planner → tools → LLM phases → persisted steps → artifacts.
 */
export function AgenticTraceView({
  projectId,
  runId,
  outputPayload,
  metaJson,
  steps,
  artifacts,
}: Props) {
  const orch = parseOrchestrationOutput(outputPayload);
  const ai = parseAiAgents(metaJson);

  return (
    <div className="space-y-4">
      <PlannerOutputPanel orch={orch} ai={ai} />
      <ToolSequencePanel orch={orch} />
      <AgentModelStepsPanel ai={ai} />
      <SectionPersistedSteps steps={steps} />
      <ArtifactsMetadataPanel
        projectId={projectId}
        runId={runId}
        artifacts={artifacts}
        orchestrationPaths={orch?.artifact_paths ?? null}
      />
    </div>
  );
}

function SectionPersistedSteps({ steps }: { steps: RunStepDetail[] }) {
  return (
    <div className="border border-[var(--border)] rounded">
      <header className="border-b border-[var(--border)] bg-neutral-50 px-3 py-2 dark:bg-neutral-900/50">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--foreground)]">
          Persisted run steps
        </h2>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          GET /v1/runs/&#123;id&#125;/steps — MCP executor steps (envelopes in DB) and LLM phases
          (critic / report) with model_call_id in meta.
        </p>
      </header>
      <div className="p-3">
        <RunStepTrace steps={steps} />
      </div>
    </div>
  );
}
