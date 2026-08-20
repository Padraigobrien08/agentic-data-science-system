import { describe, expect, it } from "vitest";

import {
  assistantText,
  callRole,
  formatDuration,
  formatUsd,
  prettyJson,
  systemPrompt,
  userPayload,
} from "@/lib/capture-view";
import type { DemoModelCall } from "@/lib/demo-static/capture-types";

function call(over: Partial<DemoModelCall> = {}): DemoModelCall {
  return {
    sequence: 0,
    id: "mc-1",
    provider: "openai",
    model_name: "gpt-5.4-mini",
    prompt_id: "agentic.policy",
    prompt_version: "1.0.3",
    status: "success",
    prompt_tokens: 100,
    completion_tokens: 20,
    latency_ms: 900,
    est_cost_usd: 0.0012,
    started_at: null,
    finished_at: null,
    request_payload_json: {
      messages: [
        { role: "system", content: "**Critic** for an adaptive data investigation loop." },
        { role: "user", content: '{"claim":null}' },
      ],
    },
    response_payload_json: { assistant_text: '{"should_challenge":false}' },
    error_detail: null,
    ...over,
  };
}

describe("callRole", () => {
  it("recovers the component from the prompt's own opening", () => {
    // Every agentic call is persisted under the same prompt_id, so that field cannot tell
    // them apart — the bolded lead is what distinguishes a critic call from a selector call.
    expect(callRole(call())).toBe("Critic");
  });

  it("reads each of the four policy roles", () => {
    const roles = ["Goal interpreter", "Hypothesis generator", "Experiment selector", "Critic"];
    for (const role of roles) {
      const c = call({
        request_payload_json: { messages: [{ role: "system", content: `**${role}** for a loop.` }] },
      });
      expect(callRole(c)).toBe(role);
    }
  });

  it("falls back to prompt_id when the prompt does not name a role", () => {
    const c = call({
      request_payload_json: { messages: [{ role: "system", content: "no bold lead here" }] },
    });
    expect(callRole(c)).toBe("agentic.policy");
  });

  it("survives a payload that is missing or the wrong shape", () => {
    expect(callRole(call({ request_payload_json: null }))).toBe("agentic.policy");
    expect(callRole(call({ request_payload_json: "not an object" }))).toBe("agentic.policy");
    expect(callRole(call({ request_payload_json: { messages: "nope" } }))).toBe("agentic.policy");
  });
});

describe("payload extraction", () => {
  it("separates the system prompt from what the component was asked", () => {
    expect(systemPrompt(call())).toContain("**Critic**");
    expect(userPayload(call())).toBe('{"claim":null}');
  });

  it("returns the assistant's raw JSON reply", () => {
    expect(assistantText(call())).toBe('{"should_challenge":false}');
  });

  it("returns empty strings rather than throwing on a redacted payload", () => {
    const redacted = call({ request_payload_json: null, response_payload_json: null });
    expect(systemPrompt(redacted)).toBe("");
    expect(userPayload(redacted)).toBe("");
    expect(assistantText(redacted)).toBe("");
  });
});

describe("prettyJson", () => {
  it("expands JSON so a reply is readable", () => {
    expect(prettyJson('{"a":1}')).toBe('{\n  "a": 1\n}');
  });

  it("leaves non-JSON and malformed JSON untouched", () => {
    expect(prettyJson("just prose")).toBe("just prose");
    expect(prettyJson('{"broken":')).toBe('{"broken":');
  });
});

describe("formatting", () => {
  it("keeps sub-cent costs visible instead of rounding them to zero", () => {
    // Two decimals would render every one of these runs as "$0.00", which reads as free.
    expect(formatUsd(0.0091, true)).toBe("$0.0091");
  });

  it("says unpriced rather than implying a run was free", () => {
    expect(formatUsd(null, false)).toBe("unpriced");
    expect(formatUsd(0, false)).toBe("unpriced");
  });

  it("switches to seconds past a thousand milliseconds", () => {
    expect(formatDuration(900)).toBe("900ms");
    expect(formatDuration(2625)).toBe("2.6s");
  });
});
