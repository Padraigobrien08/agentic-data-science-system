import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ModelCallSummaryCard } from "@/components/transparency/model-call-summary-card";
import type { ModelCallApiItem } from "@/lib/api/types";

const baseCall: ModelCallApiItem = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  analysis_run_id: "run-1",
  evaluation_run_id: null,
  tool_call_id: null,
  provider: "stub",
  model_name: "test-model",
  prompt_id: "edgar.agent.report",
  prompt_version: "1.2.3",
  status: "success",
  prompt_tokens: 10,
  completion_tokens: 20,
  latency_ms: 99,
  error_detail: null,
  started_at: null,
  finished_at: null,
  created_at: "2020-01-01T00:00:00Z",
  updated_at: "2020-01-01T00:00:00Z",
  request_payload_json: null,
  response_payload_json: null,
};

describe("ModelCallSummaryCard", () => {
  it("renders model, provider, prompt_version, tokens, and latency", () => {
    render(<ModelCallSummaryCard call={baseCall} />);
    expect(screen.getByText("test-model")).toBeTruthy();
    expect(screen.getByText("stub")).toBeTruthy();
    expect(screen.getByText("edgar.agent.report")).toBeTruthy();
    expect(screen.getByText("1.2.3")).toBeTruthy();
    expect(screen.getByText(/prompt 10/)).toBeTruthy();
    expect(screen.getByText(/completion 20/)).toBeTruthy();
    expect(screen.getByText("99")).toBeTruthy();
  });

  it("shows payload omission note when JSON not loaded", () => {
    render(<ModelCallSummaryCard call={baseCall} />);
    expect(screen.getByText(/Payloads omitted/i)).toBeTruthy();
    expect(screen.getByText("Inspect model call")).toBeTruthy();
    expect(screen.getAllByText(/Open raw payload/i).length).toBeGreaterThan(0);
  });

  it("surfaces failed model call status in the card header", () => {
    render(
      <ModelCallSummaryCard
        call={{
          ...baseCall,
          status: "error",
          error_detail: "context length exceeded",
        }}
      />,
    );
    expect(screen.getByText("failed")).toBeTruthy();
    expect(screen.getByText(/context length exceeded/)).toBeTruthy();
  });

  it("keeps raw payloads bounded behind the explicit raw toggle when they are present", () => {
    render(
      <ModelCallSummaryCard
        call={{
          ...baseCall,
          request_payload_json: { prompt: "hello" },
          response_payload_json: { output: "world" },
        }}
      />,
    );

    expect(screen.getAllByText(/Open raw payload/i).length).toBeGreaterThan(0);
    expect(screen.getByText("request_payload_json")).toBeTruthy();
    expect(screen.getByText("response_payload_json")).toBeTruthy();
  });
});
