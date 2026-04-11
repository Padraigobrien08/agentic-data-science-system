import type { StepStatusWire } from "@/lib/orchestration-output";

type Props = {
  rows: StepStatusWire[];
};

/** Planner / executor step outcomes as returned in `OrchestrationOutput.step_statuses`. */
export function OrchestrationWireTable({ rows }: Props) {
  if (rows.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-[var(--border)] text-[var(--muted)]">
            <th className="py-1.5 pr-2 font-medium">Order</th>
            <th className="py-1.5 pr-2 font-medium">Tool</th>
            <th className="py-1.5 pr-2 font-medium">MCP status</th>
            <th className="py-1.5 font-medium">Detail</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.order}-${r.tool_name}`} className="border-b border-[var(--border)]">
              <td className="py-1.5 pr-2 font-mono">{r.order}</td>
              <td className="py-1.5 pr-2 font-mono">{r.tool_name}</td>
              <td className="py-1.5 pr-2 font-mono">{r.mcp_status}</td>
              <td className="py-1.5 text-[var(--muted)]">{r.detail ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
