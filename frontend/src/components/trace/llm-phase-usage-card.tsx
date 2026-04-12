import type { LlmRunUsageSummaryWire } from "@/lib/api/types";

function formatUsd(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(n);
}

function formatLatencyMs(ms: number): string {
  if (ms >= 10_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms} ms`;
}

type Props = {
  usage: LlmRunUsageSummaryWire;
};

/**
 * Compact per-phase LLM token, latency, and optional cost table for run transparency.
 */
export function LlmPhaseUsageCard({ usage }: Props) {
  const { phases, totals, pricing_complete, pricing_configured } = usage;
  const showCostColumn = pricing_configured;

  return (
    <div className="space-y-2 border-t border-[var(--border)] pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          LLM usage by phase
        </h3>
        {pricing_configured && !pricing_complete ? (
          <p className="max-w-prose text-[10px] leading-snug text-amber-800 dark:text-amber-200">
            Cost is partial: some calls use models missing from{" "}
            <code className="font-mono text-[var(--foreground)]">EDGAR_BACKEND_AGENT_LLM_PRICING_JSON</code>.
          </p>
        ) : null}
      </div>
      {phases.length === 0 ? (
        <p className="text-[var(--muted)]">No phased model calls with token counts for this run.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[28rem] border-collapse text-left font-mono text-[11px]">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th className="py-1 pr-2 font-medium">Phase</th>
                <th className="py-1 pr-2 font-medium">Calls</th>
                <th className="py-1 pr-2 font-medium">Prompt</th>
                <th className="py-1 pr-2 font-medium">Completion</th>
                <th className="py-1 pr-2 font-medium">Latency</th>
                {showCostColumn ? (
                  <th className="py-1 pr-2 font-medium">Est. cost</th>
                ) : null}
                <th className="py-1 font-medium">Models</th>
              </tr>
            </thead>
            <tbody>
              {phases.map((row) => (
                <tr key={row.phase} className="border-b border-[var(--border)]">
                  <td className="py-1 pr-2">{row.phase}</td>
                  <td className="py-1 pr-2">{row.call_count}</td>
                  <td className="py-1 pr-2">{row.prompt_tokens.toLocaleString()}</td>
                  <td className="py-1 pr-2">{row.completion_tokens.toLocaleString()}</td>
                  <td className="py-1 pr-2">{formatLatencyMs(row.latency_ms_total)}</td>
                  {showCostColumn ? (
                    <td className="py-1 pr-2">
                      {row.estimated_cost_usd != null ? formatUsd(row.estimated_cost_usd) : "—"}
                    </td>
                  ) : null}
                  <td className="max-w-[12rem] truncate py-1 text-[10px] text-[var(--muted)]">
                    {row.model_names.length ? row.model_names.join(", ") : "—"}
                  </td>
                </tr>
              ))}
              <tr className="border-t-2 border-[var(--border)] font-medium text-[var(--foreground)]">
                <td className="py-1 pr-2">Total</td>
                <td className="py-1 pr-2">{totals.call_count}</td>
                <td className="py-1 pr-2">{totals.prompt_tokens.toLocaleString()}</td>
                <td className="py-1 pr-2">{totals.completion_tokens.toLocaleString()}</td>
                <td className="py-1 pr-2">{formatLatencyMs(totals.latency_ms_total)}</td>
                {showCostColumn ? (
                  <td className="py-1 pr-2">
                    {totals.estimated_cost_usd != null ? formatUsd(totals.estimated_cost_usd) : "—"}
                  </td>
                ) : null}
                <td className="py-1"> </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
      {!pricing_configured ? (
        <p className="text-[10px] text-[var(--muted)]">
          Set{" "}
          <code className="font-mono text-[var(--foreground)]">EDGAR_BACKEND_AGENT_LLM_PRICING_JSON</code>{" "}
          on the API to enable per-model USD estimates (see <code className="font-mono">.env.example</code>
          ).
        </p>
      ) : null}
    </div>
  );
}
