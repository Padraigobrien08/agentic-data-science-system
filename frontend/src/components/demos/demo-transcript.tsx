import type { InvestigationDetail } from "@/lib/api/types";
import type { DemoCapture } from "@/lib/demo-static/capture-types";
import { composeAnswer } from "@/lib/demo-answer";
import { formatConfidence, hypothesisStatusTone, outcomeTone } from "@/lib/investigation-view";

import { Pill } from "@/components/investigations/pill";

/**
 * A recorded run, shown the way the product shows one: as a conversation.
 *
 * Read-only by construction — there is nothing to send and no backend behind it — so the
 * composer, the progress polling and the command palette of the live chat are all absent
 * rather than disabled. What remains is the shape a reader recognises: the question that was
 * asked, and the answer that came back.
 *
 * The question is the recorded user message when one exists. Two published runs predate
 * `record_demo.py --chat` and have no turn at all; those fall back to the investigation's
 * objective, labelled as the goal rather than dressed up as a message nobody sent.
 */

const RULE = "border-[var(--border)]";
const MONO = "font-mono text-[11px]";

function Bubble({ text }: Readonly<{ text: string }>) {
  return (
    <div className="flex justify-end">
      <div
        className={`max-w-[min(100%,44rem)] whitespace-pre-wrap break-words rounded-card border ${RULE} bg-[var(--chat-user)] px-4 py-3 text-[15px] leading-7 text-[var(--foreground)]`}
      >
        {text}
      </div>
    </div>
  );
}

export function DemoTranscript({
  detail,
  capture,
}: Readonly<{ detail: InvestigationDetail; capture: DemoCapture | null }>) {
  const answer = composeAnswer(detail);
  const thread = capture?.chat[0];
  const asked = thread?.messages.find((m) => m.role === "user")?.content ?? null;
  const question = asked ?? detail.objective ?? "Investigation";

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <p className={`${MONO} text-right text-[var(--chat-faint)]`}>
          {asked ? "asked" : "goal · this run predates recorded chat turns"}
        </p>
        <Bubble text={question} />
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="h-3.5 w-3.5 rounded-[3px] bg-[linear-gradient(135deg,#7dd3fc,#818cf8)]"
            aria-hidden
          />
          <span className={`${MONO} text-[var(--chat-faint)]`}>auditable-loop</span>
          <Pill tone={outcomeTone(detail.outcome.kind)} />
          <span className={`${MONO} text-[var(--chat-faint)]`}>
            confidence {formatConfidence(detail.confidence)}
          </span>
        </div>

        <div
          className={`rounded-card border ${RULE} bg-[var(--surface)] px-5 py-4 text-[15px] leading-7 text-[var(--foreground)]`}
        >
          <p className="font-medium">{answer.headline}</p>

          {answer.conclusion ? (
            <p className="mt-3 text-[var(--muted)]">{answer.conclusion}</p>
          ) : null}

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

        <p className="text-[13px] text-[var(--muted)]">
          Every figure above is read from the recorded run. The trace beside it is the record
          they were read from.
        </p>
      </div>
    </div>
  );
}
