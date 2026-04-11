import type { ModelCallApiItem } from "@/lib/api/types";

const PROMPT_AGENT_LABEL: Record<string, string> = {
  "edgar.agent.intent": "Intent",
  "edgar.agent.planning": "Planning",
  "edgar.agent.critic": "Critic",
  "edgar.agent.report": "Report",
};

export function indexModelCallsById(
  calls: ModelCallApiItem[],
): Map<string, ModelCallApiItem> {
  const m = new Map<string, ModelCallApiItem>();
  for (const c of calls) {
    m.set(c.id, c);
  }
  return m;
}

export function modelCallLabel(call: ModelCallApiItem): string {
  if (call.prompt_id && PROMPT_AGENT_LABEL[call.prompt_id]) {
    return PROMPT_AGENT_LABEL[call.prompt_id];
  }
  if (call.prompt_id) return call.prompt_id;
  return "Model call";
}

export function formatTokenTotal(call: ModelCallApiItem): string | null {
  const p = call.prompt_tokens;
  const c = call.completion_tokens;
  if (p == null && c == null) return null;
  const parts: string[] = [];
  if (p != null) parts.push(`prompt ${p}`);
  if (c != null) parts.push(`completion ${c}`);
  return parts.join(" · ");
}

export function stringArrayFromUnknown(v: unknown, max = 50): string[] {
  if (!Array.isArray(v)) return [];
  const out: string[] = [];
  for (const x of v) {
    if (typeof x === "string" && x.trim()) out.push(x);
    if (out.length >= max) break;
  }
  return out;
}
