import { JsonPanel, MetaRow, Section } from "@/components/ui/technical";
import type { ParsedAiAgents } from "@/lib/ai-agents-meta";

type Props = {
  ai: ParsedAiAgents | null;
};

function PhaseCard({
  title,
  subtitle,
  meta,
}: {
  title: string;
  subtitle: string;
  meta: Record<string, unknown> | undefined;
}) {
  if (!meta || Object.keys(meta).length === 0) {
    return (
      <div className="rounded border border-dashed border-[var(--border)] p-3 text-sm text-[var(--muted)]">
        <p className="font-medium text-[var(--foreground)]">{title}</p>
        <p className="text-xs">No data for this phase on this run.</p>
      </div>
    );
  }

  const skipped = meta.skipped === true;
  const err = typeof meta.error === "string" ? meta.error : null;
  const reason = typeof meta.reason === "string" ? meta.reason : null;
  const modelCallId = typeof meta.model_call_id === "string" ? meta.model_call_id : null;

  return (
    <div className="rounded border border-[var(--border)] p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-sm font-semibold">{title}</h4>
        <span className="font-mono text-[10px] text-[var(--muted)]">{subtitle}</span>
      </div>
      <div className="mt-2 space-y-1 text-xs">
        {skipped ? (
          <p className="text-amber-800 dark:text-amber-200">
            Skipped
            {reason ? `: ${reason}` : ""}
          </p>
        ) : null}
        {err ? <p className="text-red-700 dark:text-red-300">{err}</p> : null}
        {modelCallId ? (
          <p className="font-mono text-[10px] text-[var(--muted)]">
            model_call_id: {modelCallId}
          </p>
        ) : null}
        {"interpreted_goal" in meta && meta.interpreted_goal !== undefined ? (
          <div className="mt-2">
            <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
              interpreted_goal
            </p>
            <JsonPanel value={meta.interpreted_goal} />
          </div>
        ) : null}
        {"steps" in meta && Array.isArray(meta.steps) ? (
          <p className="mt-2 text-[10px] text-[var(--muted)]">
            Planning step count: {(meta.steps as unknown[]).length} (table in Planner output).
          </p>
        ) : null}
      </div>
      {"result" in meta && meta.result !== undefined ? (
        <div className="mt-2">
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">result</p>
          <JsonPanel value={meta.result} />
        </div>
      ) : null}
      <details className="mt-2">
        <summary className="cursor-pointer text-[10px] text-[var(--muted)]">Full meta JSON</summary>
        <JsonPanel value={meta} />
      </details>
    </div>
  );
}

/**
 * Surfaces **LLM / agent phases** stored under `meta_json.ai_agents` (intent, planning, critic,
 * report) so behavior is auditable without opening raw blobs first.
 */
export function AgentModelStepsPanel({ ai }: Props) {
  if (!ai) {
    return (
      <Section
        title="Agent / model phases"
        description="Persisted under meta_json.ai_agents when LLM agents run."
      >
        <p className="text-sm text-[var(--muted)]">
          No <code>ai_agents</code> block on <code>meta_json</code> for this run.
        </p>
      </Section>
    );
  }

  const hasPhases =
    ai.intent ||
    ai.planning ||
    ai.critic ||
    ai.report ||
    ai.prompt_versions ||
    ai.traceable_pipeline ||
    ai.mcp_trace;

  return (
    <Section
      title="Agent / model phases"
      description="Intent and planning (pre-MCP), critic and report (post-MCP), plus pipeline bookkeeping. ModelCall rows are referenced by model_call_id in the API DB."
    >
      {!hasPhases ? (
        <p className="text-sm text-[var(--muted)]">Empty ai_agents object.</p>
      ) : (
        <div className="space-y-4">
          {ai.prompt_versions && Object.keys(ai.prompt_versions).length > 0 ? (
            <div className="rounded border border-[var(--border)] bg-neutral-50/80 p-3 dark:bg-neutral-950/40">
              <h4 className="text-xs font-semibold uppercase text-[var(--muted)]">
                Prompt template versions
              </h4>
              <div className="mt-2 border-t border-[var(--border)]">
                {Object.entries(ai.prompt_versions).map(([k, v]) => (
                  <MetaRow key={k} label={k}>
                    {v}
                  </MetaRow>
                ))}
              </div>
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            <PhaseCard
              title="Intent agent"
              subtitle="meta_json.ai_agents.intent"
              meta={ai.intent as Record<string, unknown> | undefined}
            />
            <PhaseCard
              title="Planning agent"
              subtitle="meta_json.ai_agents.planning"
              meta={ai.planning as Record<string, unknown> | undefined}
            />
            <PhaseCard
              title="Critic agent"
              subtitle="meta_json.ai_agents.critic"
              meta={ai.critic as Record<string, unknown> | undefined}
            />
            <PhaseCard
              title="Report agent"
              subtitle="meta_json.ai_agents.report"
              meta={ai.report as Record<string, unknown> | undefined}
            />
          </div>

          {ai.traceable_pipeline !== undefined ? (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase text-[var(--muted)]">
                traceable_pipeline
              </h4>
              <JsonPanel value={ai.traceable_pipeline} />
            </div>
          ) : null}
          {ai.mcp_trace !== undefined ? (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase text-[var(--muted)]">
                mcp_trace
              </h4>
              <JsonPanel value={ai.mcp_trace} />
            </div>
          ) : null}
        </div>
      )}
    </Section>
  );
}
