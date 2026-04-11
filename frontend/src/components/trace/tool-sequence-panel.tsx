import { OrchestrationWireTable } from "@/components/runs/orchestration-wire-table";
import { JsonPanel, MetaRow, Section } from "@/components/ui/technical";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";

type Props = {
  orch: ParsedOrchestrationOutput | null;
};

/**
 * **Planned** step outcomes (`step_statuses`), **executed** MCP chain (`tool_call_sequence`), and
 * per-tool summaries (`tool_results_summary`) from the orchestration snapshot.
 */
export function ToolSequencePanel({ orch }: Props) {
  if (!orch) {
    return (
      <Section
        title="Tool sequence"
        description="MCP tools as planned, executed, and summarized."
      >
        <p className="text-sm text-[var(--muted)]">No orchestration output persisted.</p>
      </Section>
    );
  }

  const hasAny =
    (orch.step_statuses && orch.step_statuses.length > 0) ||
    (orch.tool_call_sequence && orch.tool_call_sequence.length > 0) ||
    (orch.tool_results_summary && orch.tool_results_summary.length > 0);

  return (
    <Section
      title="Tool sequence"
      description="Planned steps (all orders), tools actually executed, and row-count summaries from MCP envelopes."
    >
      {!hasAny ? (
        <p className="text-sm text-[var(--muted)]">No tool steps recorded yet.</p>
      ) : (
        <div className="space-y-6">
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--muted)]">
              Orchestration summary
            </h3>
            <div className="border-t border-[var(--border)]">
              {orch.status ? (
                <MetaRow label="orchestration.status">{orch.status}</MetaRow>
              ) : null}
              {orch.message ? (
                <MetaRow label="message">{orch.message}</MetaRow>
              ) : null}
              {orch.final_summary ? (
                <MetaRow label="final_summary">
                  <span className="whitespace-pre-wrap font-mono text-[11px]">
                    {orch.final_summary}
                  </span>
                </MetaRow>
              ) : null}
              {orch.final_report_path ? (
                <MetaRow label="final_report_path">{orch.final_report_path}</MetaRow>
              ) : null}
            </div>
          </div>

          {orch.step_statuses && orch.step_statuses.length > 0 ? (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--muted)]">
                Planned steps (step_statuses)
              </h3>
              <p className="mb-2 text-xs text-[var(--muted)]">
                Full plan with per-order MCP outcome or <code>skipped</code>.
              </p>
              <OrchestrationWireTable rows={orch.step_statuses} />
            </div>
          ) : null}

          {orch.tool_call_sequence && orch.tool_call_sequence.length > 0 ? (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--muted)]">
                Executed MCP tools (tool_call_sequence)
              </h3>
              <p className="mb-2 text-xs text-[var(--muted)]">
                Subset actually dispatched (may be shorter than the plan if stopped early).
              </p>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                      <th className="py-1.5 pr-2 font-medium">Order</th>
                      <th className="py-1.5 pr-2 font-medium">tool_name</th>
                      <th className="py-1.5 font-medium">params</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orch.tool_call_sequence.map((t) => (
                      <tr key={`${t.order}-${t.tool_name}`} className="border-b border-[var(--border)]">
                        <td className="py-1.5 pr-2 font-mono">{t.order}</td>
                        <td className="py-1.5 pr-2 font-mono">{t.tool_name}</td>
                        <td className="max-w-lg py-1.5">
                          <pre className="max-h-28 overflow-auto whitespace-pre-wrap break-all font-mono text-[10px]">
                            {JSON.stringify(t.params ?? {}, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p className="text-xs text-[var(--muted)]">
              No <code>tool_call_sequence</code> in output (run not executed or empty execution).
            </p>
          )}

          {orch.tool_results_summary && orch.tool_results_summary.length > 0 ? (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--muted)]">
                Tool result summaries
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[32rem] border-collapse text-left text-[10px]">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                      <th className="py-1.5 pr-2 font-medium">Ord</th>
                      <th className="py-1.5 pr-2 font-medium">Tool</th>
                      <th className="py-1.5 pr-2 font-medium">MCP</th>
                      <th className="py-1.5 pr-2 font-medium">Panel</th>
                      <th className="py-1.5 pr-2 font-medium">Features</th>
                      <th className="py-1.5 pr-2 font-medium">Anom</th>
                      <th className="py-1.5 font-medium">Report chars</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orch.tool_results_summary.map((r) => (
                      <tr key={`${r.order}-${r.tool_name}`} className="border-b border-[var(--border)]">
                        <td className="py-1.5 pr-2 font-mono">{r.order}</td>
                        <td className="py-1.5 pr-2 font-mono">{r.tool_name}</td>
                        <td className="py-1.5 pr-2 font-mono">{r.mcp_status}</td>
                        <td className="py-1.5 pr-2 font-mono">{r.panel_row_count ?? "—"}</td>
                        <td className="py-1.5 pr-2 font-mono">{r.feature_row_count ?? "—"}</td>
                        <td className="py-1.5 pr-2 font-mono">{r.anomaly_count ?? "—"}</td>
                        <td className="py-1.5 font-mono">{r.report_character_count ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-[var(--muted)]">
                  Per-step artifact_paths / provenance_keys (JSON)
                </summary>
                <JsonPanel value={orch.tool_results_summary} />
              </details>
            </div>
          ) : null}

          {orch.errors && orch.errors.length > 0 ? (
            <JsonPanel title="errors[]" value={orch.errors} />
          ) : null}
          {orch.warnings && orch.warnings.length > 0 ? (
            <JsonPanel title="warnings[]" value={orch.warnings} />
          ) : null}
        </div>
      )}
    </Section>
  );
}
