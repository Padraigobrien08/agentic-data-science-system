/**
 * The assistant turn of a recorded run, assembled from persisted state.
 *
 * The stored assistant message is only a preview line — in the live product the answer is
 * rebuilt from the run at display time. It is rebuilt here too, but *composed* rather than
 * written: every part below is a field of the recorded investigation. Nothing is generated,
 * and no sentence is put in the loop's mouth that its own record does not support.
 *
 * That constraint is the point. A recorded run whose answer was prose written after the fact
 * would be a reconstruction, and the whole replay tier rests on it not being one.
 */

import type { InvestigationDetail } from "@/lib/api/types";
import { outcomeSummary } from "@/lib/investigation-view";

export type AnswerClaim = {
  id: string;
  statement: string;
  status: string;
  confidence: number;
};

export type ComposedAnswer = {
  /** One line naming what the run established, from the outcome classification. */
  headline: string;
  /** The recorded conclusion, when the run reached one. */
  conclusion: string | null;
  claims: AnswerClaim[];
  /** Questions the run deliberately left open. */
  openQuestions: string[];
  /** Provenance line: what was run, over what, and where it stopped. */
  footnote: string;
};

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

export function composeAnswer(detail: InvestigationDetail): ComposedAnswer {
  const counts = detail.counts;
  const parts = [
    plural(counts.decisions, "decision"),
    plural(counts.experiments, "experiment"),
    plural(counts.evidence, "evidence item"),
  ];

  const dataset = detail.datasets[0]?.name;
  const rows = detail.datasets[0]?.row_count;
  const over = dataset ? ` over ${dataset}${rows ? ` (n=${rows})` : ""}` : "";
  const stopped = detail.termination?.reason ? `, stopping at ${detail.termination.reason}` : "";

  return {
    headline: outcomeSummary(detail.outcome),
    conclusion: detail.conclusion_detail?.statement ?? detail.conclusion ?? null,
    claims: detail.hypotheses.map((h) => ({
      id: h.id,
      statement: h.statement,
      status: h.status,
      confidence: h.confidence,
    })),
    openQuestions: detail.open_questions.map((q) => q.question),
    footnote: `${parts.join(", ")}${over}${stopped}.`,
  };
}
