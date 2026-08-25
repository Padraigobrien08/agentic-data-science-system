import { Pill } from "@/components/investigations/pill";
import type { ComposedAnswer } from "@/lib/demo-answer";
import { formatConfidence, hypothesisStatusTone } from "@/lib/investigation-view";

/**
 * The assistant turn of a *recorded* run.
 *
 * Plain prose on the page, the way every chat interface renders an assistant reply — no
 * card, no border, no panel. It was boxed before, and a box says "widget" when the thing
 * inside it is just an answer to a question.
 *
 * The claim-by-claim breakdown that used to sit here is gone rather than restyled: the trace
 * rail already lists every claim with the same status and the same confidence, and the prose
 * already names what happened to each. Three renderings of one fact is two too many.
 *
 * What survives beside the prose is the provenance line — what ran, over what, and where it
 * stopped — because that is the part a reader cannot get from the sentences.
 */

const MONO = "font-mono text-[11px]";

export function ChatRecordedAnswer({ answer }: Readonly<{ answer: ComposedAnswer }>) {
  return (
    <div className="mx-auto max-w-[52rem] text-[15px] leading-7 text-[var(--foreground)]">
      {answer.narrative ? (
        <div className="space-y-4">
          {/* Index keys: a recorded narrative is fixed text that never reorders, and two
              paragraphs can legitimately begin with the same words. */}
          {answer.narrative.split(/\n{2,}/).map((para, i) => (
            <p key={i}>{para.trim()}</p>
          ))}
        </div>
      ) : (
        // No narrative survived verification, so the structured record *is* the answer here
        // and has to carry it. Still unboxed — same turn, less to say.
        <div className="space-y-3">
          <p>{answer.headline}</p>
          {answer.conclusion ? <p className="text-[var(--muted)]">{answer.conclusion}</p> : null}
          {answer.claims.length ? (
            <ul className="space-y-1.5 pt-1">
              {answer.claims.map((c) => (
                <li key={c.id} className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <Pill tone={hypothesisStatusTone(c.status)} />
                  <span className="min-w-0 flex-1 text-[14px] leading-6">{c.statement}</span>
                  <span className={`${MONO} text-[var(--chat-faint)]`}>
                    {formatConfidence(c.confidence)}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
          {/* Only in the fallback. A narrative states what was left open in its own words;
              repeating it as a list beneath would say the same thing twice. */}
          {answer.openQuestions.length ? (
            <div className="pt-1">
              <p className={`${MONO} uppercase tracking-[0.08em] text-[var(--chat-faint)]`}>
                Left open on purpose
              </p>
              <ul className="mt-1.5 space-y-1">
                {answer.openQuestions.map((q) => (
                  <li key={q} className="text-[14px] leading-6 text-[var(--muted)]">
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}

      <p className={`mt-4 ${MONO} text-[var(--chat-faint)]`}>{answer.footnote}</p>
    </div>
  );
}
