import Link from "next/link";

import { ClaimTrackList } from "@/components/trace/claim-track-list";
import type { InvestigationDetail } from "@/lib/api/types";
import { formatConfidence } from "@/lib/investigation-view";
import { claimTrace } from "@/lib/trace-claims";
import { traceSections } from "@/lib/trace-view";

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
  const trace = claimTrace(detail);
  const sections = traceSections(detail);

  return (
    <aside className="space-y-4">
      <div className={`flex items-baseline justify-between gap-3 border-b ${RULE} pb-3`}>
        <div>
          <p className="text-sm font-semibold tracking-[-0.01em] text-[var(--foreground)]">
            The trace
          </p>
          <p className={`mt-0.5 ${MONO} text-[var(--chat-faint)]`}>
            {trace.claims.length} claim{trace.claims.length === 1 ? "" : "s"} ·{" "}
            {detail.counts.decisions} decisions
          </p>
        </div>
        <Link href={fullTraceHref} className={`${MONO} text-[var(--accent)] hover:underline`}>
          full record →
        </Link>
      </div>

      <ClaimTrackList trace={trace} />

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
