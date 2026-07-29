import { stringArrayFromUnknown } from "@/lib/agent-transparency";
import { humanizeWeakEvidenceSignal } from "@/components/structured-answer/signal-labels";
import { parsePhaseAudits } from "@/lib/context-transparency";
import type { ParsedAiAgents } from "@/lib/ai-agents-meta";

type Props = {
  ai: ParsedAiAgents | null;
};

function phaseOutput(meta: unknown): Record<string, unknown> | null {
  if (typeof meta !== "object" || meta === null || Array.isArray(meta)) return null;
  const po = (meta as Record<string, unknown>).phase_output;
  if (typeof po !== "object" || po === null || Array.isArray(po)) return null;
  return po as Record<string, unknown>;
}

/**
 * Dense audit block: per-phase context budget / truncation flags and critic weak-evidence ids.
 * Anchor ``#run-context-transparency`` — linked from the primary “Context” chip.
 */
export function ContextTransparencyPanel({ ai }: Props) {
  const phases = parsePhaseAudits(ai);
  const criticPo = phaseOutput(ai?.critic);
  const weak = stringArrayFromUnknown(criticPo?.weak_evidence_signals, 20);
  const hasAny = phases.length > 0 || weak.length > 0;

  if (!hasAny) {
    return (
      <div
        id="run-context-transparency"
        className="scroll-mt-20 border-b border-[var(--border)] pb-3 text-[11px] text-[var(--muted)]"
      >
        <h3 className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--foreground)]">
          Model context &amp; sampling
        </h3>
        <p>No ``llm_context_audit`` or weak-evidence flags on this run — models likely saw full bundled context.</p>
      </div>
    );
  }

  return (
    <div
      id="run-context-transparency"
      className="scroll-mt-20 border-b border-[var(--border)] pb-3 text-[11px]"
    >
      <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--foreground)]">
        Model context &amp; sampling
      </h3>
      <p className="mb-2 leading-snug text-[var(--muted)]">
        When the pipeline trimmed or sampled inputs, flags are recorded on the critic/report phases. This does not
        mean the run failed — read certainty as proportional to evidence quality and context scope.
      </p>
      {phases.map(({ phase, rows }) => (
        <div key={phase} className="mb-3 last:mb-0">
          <p className="mb-1 font-mono text-[10px] uppercase text-[var(--muted)]">{phase} phase</p>
          <div className="overflow-x-auto rounded border border-[var(--border)] bg-[var(--surface)]">
            <table className="w-full border-collapse text-left text-[10px]">
              <tbody className="divide-y divide-[var(--border)]">
                {rows.map((r) => (
                  <tr key={`${phase}-${r.key}`}>
                    <th className="w-[40%] px-2 py-1.5 align-top font-medium text-[var(--foreground)]">{r.shortLabel}</th>
                    <td className="px-2 py-1.5 text-[var(--muted)]" title={r.tooltip}>
                      {r.tooltip}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      {weak.length > 0 ? (
        <div className="mt-2">
          <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">Weak evidence (critic)</p>
          <ul className="list-inside list-disc text-[var(--muted)]">
            {weak.map((id) => (
              <li key={id} className="font-mono text-[10px]">
                <span title={id}>{humanizeWeakEvidenceSignal(id)}</span>
                <span className="ml-1 opacity-80">({id})</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
