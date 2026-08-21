import { Pill } from "@/components/investigations/pill";
import type { ComposedAnswer } from "@/lib/demo-answer";
import { formatConfidence, hypothesisStatusTone } from "@/lib/investigation-view";

/**
 * The assistant turn of a *recorded* run.
 *
 * The live product renders `ChatRunAnswerCard` from a run's view model. A recorded run has
 * no such view model — the export carries the investigation, not the run's answer payload —
 * so its turn is composed from persisted investigation state instead (`composeAnswer`).
 *
 * Deliberately a third branch rather than a synthesised `ChatAnswerCardView`: filling that
 * shape from an investigation would mean inventing the fields it does not have, and the
 * replay tier rests on nothing here being invented.
 */

const MONO = "font-mono text-[11px]";
const RULE = "border-[var(--border)]";

export function ChatRecordedAnswer({ answer }: Readonly<{ answer: ComposedAnswer }>) {
  return (
    <div
      className={`mx-auto max-w-[52rem] rounded-card border ${RULE} bg-[var(--surface)] px-5 py-4 text-[15px] leading-7 text-[var(--foreground)]`}
    >
      <p className="font-medium">{answer.headline}</p>

      {answer.conclusion ? <p className="mt-3 text-[var(--muted)]">{answer.conclusion}</p> : null}

      {answer.claims.length ? (
        <ul className={`mt-4 space-y-2 border-t ${RULE} pt-4`}>
          {answer.claims.map((c) => (
            <li key={c.id} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="min-w-0 flex-1 text-[14px] leading-6">{c.statement}</span>
              <span className="flex shrink-0 items-center gap-2">
                <Pill tone={hypothesisStatusTone(c.status)} />
                <span className={`${MONO} text-[var(--chat-faint)]`}>
                  {formatConfidence(c.confidence)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {answer.openQuestions.length ? (
        <div className={`mt-4 border-t ${RULE} pt-4`}>
          <p className={`${MONO} uppercase tracking-[0.08em] text-[var(--chat-faint)]`}>
            Left open on purpose
          </p>
          <ul className="mt-2 space-y-1.5">
            {answer.openQuestions.map((q) => (
              <li key={q} className="text-[14px] leading-6 text-[var(--muted)]">
                {q}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className={`mt-4 border-t ${RULE} pt-3 ${MONO} text-[var(--chat-faint)]`}>
        {answer.footnote}
      </p>
    </div>
  );
}
