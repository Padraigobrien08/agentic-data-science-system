import type { ReactNode } from "react";

import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";
import { JsonPanel, MetaRow, Section } from "@/components/ui/technical";

type Props = {
  orch: ParsedOrchestrationOutput | null;
  ai: ParsedAiAgents | null;
};

function interpretedGoalSummary(goal: unknown): ReactNode {
  if (!goal || typeof goal !== "object" || Array.isArray(goal)) {
    return <JsonPanel value={goal} />;
  }
  const g = goal as Record<string, unknown>;
  const code = typeof g.code === "string" ? g.code : null;
  const desc = typeof g.description === "string" ? g.description : null;
  const userGoal = typeof g.user_goal_text === "string" ? g.user_goal_text : null;
  const intent = typeof g.intent === "string" ? g.intent : null;
  if (!code && !desc) return <JsonPanel value={goal} />;
  return (
    <div className="space-y-0 border-t border-[var(--border)]">
      {code ? <MetaRow label="code">{code}</MetaRow> : null}
      {intent ? <MetaRow label="intent">{intent}</MetaRow> : null}
      {desc ? (
        <MetaRow label="description">
          <span className="whitespace-pre-wrap">{desc}</span>
        </MetaRow>
      ) : null}
      {userGoal ? (
        <MetaRow label="user_goal_text">
          <span className="whitespace-pre-wrap">{userGoal}</span>
        </MetaRow>
      ) : null}
    </div>
  );
}

/**
 * Rule-based / coordinator **interpreted_goal** (orchestration output) plus optional **LLM planning**
 * steps from `meta_json.ai_agents.planning` (what the planning agent proposed before MCP execution).
 */
export function PlannerOutputPanel({ orch, ai }: Props) {
  const llmSteps = ai?.planning?.steps;
  const intentGoal = ai?.intent?.interpreted_goal ?? orch?.interpreted_goal;

  return (
    <Section
      title="Planner output"
      description="Interpreted goal from orchestration output, and LLM planning steps (when intent/planning agents ran before execution)."
    >
      <div className="space-y-6">
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            Interpreted goal
          </h3>
          <p className="mb-2 text-xs text-[var(--muted)]">
            From <code className="text-[var(--foreground)]">OrchestrationOutput.interpreted_goal</code>
            {ai?.intent?.interpreted_goal ? (
              <>
                {" "}
                — intent agent snapshot in{" "}
                <code className="text-[var(--foreground)]">meta_json.ai_agents.intent</code> when
                present.
              </>
            ) : null}
          </p>
          {intentGoal ? (
            interpretedGoalSummary(intentGoal)
          ) : (
            <p className="text-sm text-[var(--muted)]">No interpreted goal in output yet.</p>
          )}
        </div>

        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            LLM planning steps
          </h3>
          {!llmSteps?.length ? (
            <p className="text-sm text-[var(--muted)]">
              No <code className="text-[var(--foreground)]">ai_agents.planning.steps</code> on this
              run. The in-process rule planner may still build the MCP plan without a separate LLM
              planning call.
            </p>
          ) : (
            <>
              {ai?.planning?.model_call_id ? (
                <p className="mb-2 font-mono text-[10px] text-[var(--muted)]">
                  planning model_call_id: {ai.planning.model_call_id}
                </p>
              ) : null}
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                      <th className="py-1.5 pr-2 font-medium">Order</th>
                      <th className="py-1.5 pr-2 font-medium">tool_name</th>
                      <th className="py-1.5 pr-2 font-medium">label</th>
                      <th className="py-1.5 font-medium">tool_input</th>
                    </tr>
                  </thead>
                  <tbody>
                    {llmSteps.map((s) => (
                      <tr key={`${s.order}-${s.tool_name}`} className="border-b border-[var(--border)]">
                        <td className="py-1.5 pr-2 font-mono">{s.order}</td>
                        <td className="py-1.5 pr-2 font-mono">{s.tool_name}</td>
                        <td className="py-1.5 pr-2 text-[var(--muted)]">{s.label ?? "—"}</td>
                        <td className="max-w-md py-1.5 font-mono text-[10px]">
                          {s.tool_input ? (
                            <pre className="max-h-24 overflow-auto whitespace-pre-wrap break-all rounded bg-neutral-100 p-1 dark:bg-neutral-900">
                              {JSON.stringify(s.tool_input)}
                            </pre>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </Section>
  );
}
