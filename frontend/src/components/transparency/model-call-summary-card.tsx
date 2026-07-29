import Link from "next/link";

import { JsonPanel, MetaRow } from "@/components/ui/technical";
import type { ModelCallApiItem } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { formatTokenTotal, modelCallLabel } from "@/lib/agent-transparency";

/** One line for embedding under a phase card (no JSON). */
export function ModelCallInlineSummary({ call }: { call: ModelCallApiItem }) {
  const tokens = formatTokenTotal(call);
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-1.5 font-mono text-[10px]">
      <span className="text-[var(--foreground)]">{modelCallLabel(call)}</span>
      <span className="text-[var(--muted)]"> · </span>
      <span>{call.model_name}</span>
      <span className="text-[var(--muted)]"> · {call.provider}</span>
      {call.prompt_version ? (
        <span className="text-[var(--muted)]"> · prompt {call.prompt_version}</span>
      ) : null}
      {call.latency_ms != null ? (
        <span className="text-[var(--muted)]"> · {call.latency_ms}ms</span>
      ) : null}
      {tokens ? <span className="text-[var(--muted)]"> · {tokens}</span> : null}
      <span className="block truncate text-[var(--muted)]">{call.id}</span>
    </div>
  );
}

type Props = {
  call: ModelCallApiItem;
  inspectHref?: string;
};

/**
 * One persisted LLM invocation: model, prompt version, tokens, latency — payloads behind a details toggle.
 */
export function ModelCallSummaryCard({ call, inspectHref }: Props) {
  const title = modelCallLabel(call);
  const tokens = formatTokenTotal(call);

  const failed = call.status === "error";

  return (
    <div
      className={`rounded border bg-[var(--surface)] ${
        failed
          ? "border-red-400 dark:border-red-700"
          : "border-[var(--border)]"
      }`}
    >
      <div className="border-b border-[var(--border)] px-3 py-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide">
            {title}
            {failed ? (
              <span className="rounded bg-red-100 px-1.5 py-0.5 font-mono text-[10px] font-normal normal-case text-red-900 dark:bg-red-950/80 dark:text-red-100">
                failed
              </span>
            ) : null}
          </h3>
          <span className="font-mono text-[10px] text-[var(--muted)]">{call.id}</span>
        </div>
        <p className="mt-1 font-mono text-[11px] text-[var(--foreground)]">
          <span className="text-[var(--muted)]">model</span> {call.model_name}{" "}
          <span className="text-[var(--muted)]">·</span>{" "}
          <span className="text-[var(--muted)]">{call.provider}</span>
        </p>
      </div>
      <div className="px-3 py-2">
        <div className="space-y-0 border-t border-[var(--border)]">
          <MetaRow label="status">{call.status}</MetaRow>
          {call.prompt_id ? <MetaRow label="prompt_id">{call.prompt_id}</MetaRow> : null}
          {call.prompt_version ? (
            <MetaRow label="prompt_version">{call.prompt_version}</MetaRow>
          ) : null}
          {tokens ? <MetaRow label="tokens">{tokens}</MetaRow> : null}
          {call.latency_ms != null ? (
            <MetaRow label="latency_ms">{call.latency_ms}</MetaRow>
          ) : null}
          {call.started_at ? (
            <MetaRow label="started_at">{formatDate(call.started_at)}</MetaRow>
          ) : null}
          {call.finished_at ? (
            <MetaRow label="finished_at">{formatDate(call.finished_at)}</MetaRow>
          ) : null}
          {call.error_detail ? (
            <MetaRow label="error_detail">
              <span className="whitespace-pre-wrap text-red-800 dark:text-red-200">
                {call.error_detail}
              </span>
            </MetaRow>
          ) : null}
        </div>
        <div className="mt-3 space-y-3 border-t border-[var(--border)] pt-3">
          <div className="flex flex-wrap items-center gap-3">
            {inspectHref ? (
              <Link
                href={inspectHref}
                className="text-xs font-medium text-[var(--foreground)] underline underline-offset-4"
              >
                Inspect model call
              </Link>
            ) : (
              <span className="text-xs font-medium text-[var(--foreground)]">Inspect model call</span>
            )}
            <p className="font-mono text-[10px] text-[var(--muted)]">Open raw payload only for this one call.</p>
          </div>

          {call.request_payload_json != null || call.response_payload_json != null ? (
            <details>
              <summary className="cursor-pointer font-mono text-[10px] text-[var(--muted)]">
                Open raw payload
              </summary>
              <div className="mt-2 space-y-2">
                {call.request_payload_json != null ? (
                  <JsonPanel title="request_payload_json" value={call.request_payload_json} />
                ) : null}
                {call.response_payload_json != null ? (
                  <JsonPanel title="response_payload_json" value={call.response_payload_json} />
                ) : null}
              </div>
            </details>
          ) : (
            <p className="font-mono text-[10px] text-[var(--muted)]">
              Payloads omitted. Open raw payload from the summary-first trace view when privileged access is available.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
