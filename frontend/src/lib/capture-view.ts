/**
 * Reading a captured model call for display.
 *
 * The bundle stores provider request/response payloads verbatim, which is the right thing to
 * persist and the wrong thing to render: a 4 KB system prompt and a `raw_response` envelope
 * tell a reader nothing at a glance. These helpers pull out the parts worth showing and leave
 * the rest behind a disclosure.
 */

import type { DemoModelCall } from "@/lib/demo-static/capture-types";

type Message = { role?: string; content?: string };

function messages(call: DemoModelCall): Message[] {
  const req = call.request_payload_json;
  if (!req || typeof req !== "object") return [];
  const raw = (req as { messages?: unknown }).messages;
  return Array.isArray(raw) ? (raw as Message[]) : [];
}

export function systemPrompt(call: DemoModelCall): string {
  return messages(call).find((m) => m.role === "system")?.content ?? "";
}

/** What the component was actually asked — the small, interesting half of the request. */
export function userPayload(call: DemoModelCall): string {
  const user = messages(call).filter((m) => m.role !== "system").pop();
  return user?.content ?? "";
}

export function assistantText(call: DemoModelCall): string {
  const res = call.response_payload_json;
  if (!res || typeof res !== "object") return "";
  const text = (res as { assistant_text?: unknown }).assistant_text;
  return typeof text === "string" ? text : "";
}

/**
 * Which loop component made the call: "Goal interpreter", "Critic", and so on.
 *
 * Every agentic call is persisted under the same `prompt_id` (`agentic.policy`), so that
 * field cannot distinguish them — but each prompt opens by naming its own role in bold. The
 * sequence this recovers is the run's shape: interpret, hypothesise, then select/critic
 * repeating once per iteration.
 */
export function callRole(call: DemoModelCall): string {
  const lead = /^\s*\*\*([^*]{2,40})\*\*/.exec(systemPrompt(call));
  if (lead) return lead[1].trim();
  return call.prompt_id ?? "model call";
}

/** Pretty-print JSON when it is JSON, otherwise return the text unchanged. */
export function prettyJson(text: string): string {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return text;
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2);
  } catch {
    return text;
  }
}

export function formatTokens(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Cost to four decimals, because these runs cost fractions of a cent and rounding to two
 * would render every one of them as "$0.00" — which reads as free rather than as cheap.
 */
export function formatUsd(usd: number | null, priced: boolean): string {
  if (!priced || usd === null) return "unpriced";
  return `$${usd.toFixed(4)}`;
}
