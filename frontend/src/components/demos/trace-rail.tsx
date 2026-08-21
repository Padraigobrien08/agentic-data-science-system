import Link from "next/link";

import type { InvestigationDetail } from "@/lib/api/types";
import { formatConfidence } from "@/lib/investigation-view";
import { decisionGlyph, decisionLabel, groupDecisionsByIteration, traceSections } from "@/lib/trace-view";

/**
 * The trace, docked beside the answer.
 *
 * A supplement, not the headline: the answer is what the reader came for, and the trace is
 * what lets them disbelieve it. Compact enough to read alongside — the full record lives one
 * link away rather than being crammed in here.
 */

const MONO = "font-mono text-[11px]";
const RULE = "border-[var(--border)]";

export function TraceRail({
  detail,
  fullTraceHref,
}: Readonly<{ detail: InvestigationDetail; fullTraceHref: string }>) {
  const iterations = groupDecisionsByIteration(detail.decisions, detail.hypotheses);
  const sections = traceSections(detail);

  return (
    <aside className="space-y-4">
      <div className={`flex items-baseline justify-between gap-3 border-b ${RULE} pb-3`}>
        <div>
          <p className="text-sm font-semibold tracking-[-0.01em] text-[var(--foreground)]">
            The trace
          </p>
          <p className={`mt-0.5 ${MONO} text-[var(--chat-faint)]`}>
            {detail.counts.decisions} decisions · {iterations.length} iteration
            {iterations.length === 1 ? "" : "s"}
          </p>
        </div>
        <Link href={fullTraceHref} className={`${MONO} text-[var(--accent)] hover:underline`}>
          full record →
        </Link>
      </div>

      <ol className="space-y-0">
        {iterations.map((it) => (
          <li key={it.iteration} className={`relative border-l ${RULE} pb-4 pl-4`}>
            <span
              className="absolute -left-[3px] top-1.5 h-1.5 w-1.5 rounded-full bg-[var(--chat-faint)]"
              aria-hidden
            />
            <p className={`${MONO} font-medium text-[var(--foreground)]`}>
              {it.label}
              <span className="font-normal text-[var(--chat-faint)]">
                {" · "}
                {it.decisionCount} decision{it.decisionCount === 1 ? "" : "s"}
                {it.hasContradiction ? " · contradiction" : ""}
              </span>
            </p>
            <div className="mt-2 space-y-2">
              {it.rows.map((row) =>
                row.kind === "contradiction" ? (
                  <div
                    key={row.decisions[0].id}
                    className={`rounded-md border ${RULE} bg-[var(--chat-accent-soft)] p-2.5`}
                  >
                    <p className={`${MONO} uppercase tracking-[0.08em] text-[var(--status-info-ink)]`}>
                      One event · {row.decisions.length} revisions
                    </p>
                    <p className="mt-1 text-[12.5px] leading-snug text-[var(--foreground)]">
                      Both claims weakened: they cannot hold at the same time as each other.
                    </p>
                  </div>
                ) : (
                  <div key={row.decision.id} className="flex gap-2">
                    <span className={`${MONO} select-none text-[var(--chat-faint)]`} aria-hidden>
                      {decisionGlyph(row.decision.decision_type)}
                    </span>
                    <div className="min-w-0">
                      <p className="text-[12.5px] leading-snug text-[var(--foreground)]">
                        {decisionLabel(row.decision.decision_type)}
                        {row.decision.chosen_option ? (
                          <span className={`${MONO} ml-1.5 text-[var(--accent)]`}>
                            {row.decision.chosen_option}
                          </span>
                        ) : null}
                      </p>
                      <p className="mt-0.5 text-[11.5px] leading-snug text-[var(--muted)]">
                        {row.decision.rationale}
                      </p>
                    </div>
                  </div>
                ),
              )}
            </div>
          </li>
        ))}
      </ol>

      {/* Counts, as the way into the full record rather than as decoration. */}
      <div className={`divide-y overflow-hidden rounded-lg border ${RULE} divide-[var(--border)]`}>
        {sections
          .filter((s) => s.id !== "decisions" && s.count > 0)
          .map((s) => (
            <Link
              key={s.id}
              href={`${fullTraceHref}#trace-${s.id}`}
              className="flex items-baseline justify-between gap-3 bg-[var(--chat-raise)] px-3 py-2.5 transition-colors hover:bg-[var(--chat-hover)]"
            >
              <span className="text-[12.5px] text-[var(--foreground)]">{s.label}</span>
              <span className={`${MONO} text-[var(--chat-faint)]`}>
                {s.count}
                {s.note ? ` · ${s.note}` : ""} →
              </span>
            </Link>
          ))}
      </div>

      <p className={`${MONO} text-[var(--chat-faint)]`}>
        confidence {formatConfidence(detail.confidence)}
        {detail.adapter_id ? ` · ${detail.adapter_id}` : ""}
      </p>
    </aside>
  );
}
