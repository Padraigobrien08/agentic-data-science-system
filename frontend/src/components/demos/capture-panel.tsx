import {
  assistantText,
  callRole,
  formatDuration,
  formatTokens,
  formatUsd,
  prettyJson,
  systemPrompt,
  userPayload,
} from "@/lib/capture-view";
import type { DemoCapture, DemoModelCall } from "@/lib/demo-static/capture-types";

/**
 * The model calls and chat turn behind a recorded run.
 *
 * The rest of the page is the claim that no number came from a language model. This is the
 * other half of that claim: every place a model *was* consulted, with the exact prompt it
 * received and the exact JSON it returned. A reader can check that the model chose which
 * experiment to run and never produced a figure.
 *
 * Deliberately not part of `InvestigationDetailView`: that component also renders live runs,
 * where these payloads are admin-gated. This ships only with the static export.
 */

const MONO = "font-mono text-[11px] leading-relaxed";

function Block({ label, body, chars }: { label: string; body: string; chars?: boolean }) {
  if (!body) return null;
  return (
    <details className="group mt-2">
      <summary className="cursor-pointer select-none text-[11px] text-neutral-500 hover:text-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-200">
        <span className="inline-block w-3 transition-transform group-open:rotate-90">▸</span>
        {label}
        {chars ? ` (${formatTokens(body.length)} chars)` : null}
      </summary>
      <pre
        className={`${MONO} mt-1 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded border border-neutral-200 bg-neutral-50 p-3 text-neutral-700 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-300`}
      >
        {body}
      </pre>
    </details>
  );
}

function Call({ call, priced }: { call: DemoModelCall; priced: boolean }) {
  const prompt = systemPrompt(call);
  const input = userPayload(call);
  const output = assistantText(call);

  return (
    <li className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          <span className="mr-2 font-mono text-xs text-neutral-400">{call.sequence}</span>
          {callRole(call)}
        </p>
        <p className="font-mono text-[11px] text-neutral-500 dark:text-neutral-400">
          {formatTokens(call.prompt_tokens ?? 0)} → {formatTokens(call.completion_tokens ?? 0)} tok
          {call.latency_ms !== null ? ` · ${formatDuration(call.latency_ms)}` : ""}
          {` · ${formatUsd(call.est_cost_usd, priced)}`}
        </p>
      </div>
      <p className="mt-0.5 font-mono text-[11px] text-neutral-400">
        {call.model_name}
        {call.prompt_version ? ` · prompt ${call.prompt_version}` : ""}
        {call.status !== "success" ? ` · ${call.status}` : ""}
      </p>

      <Block label=" system prompt" body={prompt} chars />
      <Block label=" what it was asked" body={prettyJson(input)} />
      <Block label=" what it returned" body={prettyJson(output)} />
      {call.error_detail ? (
        <p className="mt-2 text-[11px] text-red-700 dark:text-red-400">{call.error_detail}</p>
      ) : null}
    </li>
  );
}

export function CapturePanel({ capture }: { capture: DemoCapture }) {
  const { totals, model_calls: calls, chat } = capture;
  if (!calls.length && !chat.length) return null;

  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
          Model calls
        </h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-300">
          Every point where a language model was consulted, with the prompt it received and the
          JSON it returned. The model chose intent, hypotheses and which experiment to run next;
          no figure on this page came from it.
        </p>
        <p className="font-mono text-xs text-neutral-500 dark:text-neutral-400">
          {totals.model_calls} call{totals.model_calls === 1 ? "" : "s"} ·{" "}
          {formatTokens(totals.total_tokens)} tokens · {formatDuration(totals.latency_ms)} ·{" "}
          {formatUsd(totals.est_cost_usd, totals.priced)}
        </p>
      </div>

      {chat.length ? (
        <div className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
          <p className="text-[11px] uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
            Recorded chat turn
          </p>
          <div className="mt-2 space-y-2">
            {chat.flatMap((thread) =>
              thread.messages.map((m) => (
                <div key={m.id}>
                  <p className="font-mono text-[11px] text-neutral-400">{m.role}</p>
                  <p className="text-sm text-neutral-700 dark:text-neutral-200">{m.content}</p>
                </div>
              )),
            )}
          </div>
        </div>
      ) : null}

      <ol className="space-y-2">
        {calls.map((c) => (
          <Call key={c.id} call={c} priced={totals.priced} />
        ))}
      </ol>
    </section>
  );
}
