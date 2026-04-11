import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type { ModelCallApiItem } from "@/lib/api/types";
import type { PlanRow } from "@/lib/run-trace-derive";
import { JsonPanel, MetaRow } from "@/components/ui/technical";
import { ModelCallInlineSummary } from "@/components/transparency/model-call-summary-card";

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

type Props = {
  ai: ParsedAiAgents | null;
  planRows: PlanRow[];
  planningModelCall: ModelCallApiItem | null;
};

/**
 * Planning phase: ordered tools, source, optional embedded model call card.
 */
export function PlanningOutputCard({ ai, planRows, planningModelCall }: Props) {
  const planning = ai?.planning;
  const po =
    planning && isRecord(planning.phase_output)
      ? (planning.phase_output as Record<string, unknown>)
      : null;
  const llmSteps = planning?.steps;
  const tr = ai?.traceability?.planning;

  const rows =
    llmSteps && llmSteps.length > 0
      ? llmSteps.map((s) => ({
          order: s.order,
          tool: s.tool_name,
          label: s.label ?? "—",
        }))
      : planRows.map((r) => ({
          order: r.order,
          tool: r.tool_name,
          label: r.label ?? "—",
        }));

  const toolChain = rows.map((r) => r.tool).filter(Boolean);
  const hasContent =
    rows.length > 0 ||
    po ||
    tr?.decision_summary ||
    planningModelCall ||
    planning?.model_call_id;

  if (!hasContent) {
    return (
      <div className="rounded border border-dashed border-[var(--border)] p-3 text-sm text-[var(--muted)]">
        No planning metadata (deterministic run without LLM planning snapshot).
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded border border-[var(--border)] p-3">
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--foreground)]">
          Planning
        </h3>
        {tr?.decision_summary ? (
          <p className="mt-2 max-w-prose whitespace-pre-wrap text-sm">{tr.decision_summary}</p>
        ) : null}
        {tr?.rationale_summary ? (
          <p className="mt-2 max-w-prose text-xs text-[var(--muted)]">{tr.rationale_summary}</p>
        ) : null}
      </div>

      {po ? (
        <div className="space-y-0 border-t border-[var(--border)] pt-2">
          {typeof po.source === "string" ? <MetaRow label="source">{po.source}</MetaRow> : null}
          {typeof po.step_count === "number" ? (
            <MetaRow label="step_count">{po.step_count}</MetaRow>
          ) : null}
          {typeof po.rationale === "string" ? (
            <MetaRow label="rationale">{po.rationale}</MetaRow>
          ) : null}
        </div>
      ) : null}

      {toolChain.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Tool chain
          </p>
          <p className="font-mono text-xs">{toolChain.join(" → ")}</p>
        </div>
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th className="py-1 pr-2 font-medium">#</th>
                <th className="py-1 pr-2 font-medium">tool_name</th>
                <th className="py-1 font-medium">label</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.order}-${r.tool}`} className="border-b border-[var(--border)]">
                  <td className="py-1 pr-2 font-mono">{r.order}</td>
                  <td className="py-1 pr-2 font-mono">{r.tool}</td>
                  <td className="py-1 text-[var(--muted)]">{r.label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {planningModelCall ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase text-[var(--muted)]">
            Planning model call
          </p>
          <ModelCallInlineSummary call={planningModelCall} />
        </div>
      ) : planning?.model_call_id ? (
        <p className="font-mono text-[10px] text-[var(--muted)]">
          model_call_id {planning.model_call_id} (no matching ModelCall row in API response)
        </p>
      ) : null}

      <details>
        <summary className="cursor-pointer font-mono text-[10px] text-[var(--muted)]">
          Raw planning.phase_output
        </summary>
        <div className="mt-2">
          {po ? <JsonPanel value={po} /> : <p className="text-xs text-[var(--muted)]">—</p>}
        </div>
      </details>
    </div>
  );
}
