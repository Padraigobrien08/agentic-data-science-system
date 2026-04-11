import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReportEvidencePanel } from "@/components/transparency/report-evidence-panel";

vi.mock("next/link", () => ({
  default({ children, href }: { children: ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  },
}));

describe("ReportEvidencePanel", () => {
  it("renders artifact links when phase_output refs match registered roles", () => {
    render(
      <ReportEvidencePanel
        lps={{ phase_status: "success" }}
        phaseStatus="success"
        trace={undefined}
        phaseOutput={{
          artifact_refs: [{ role: "panel_csv", basename: "panel.csv" }],
          key_takeaways: ["One"],
        }}
        artifacts={[
          {
            id: "artifact-uuid-1",
            analysis_run_id: "run-1",
            evaluation_run_id: null,
            run_step_id: null,
            role_key: "panel_csv",
            kind: "tabular",
            mime_type: null,
            byte_size: 100,
            content_sha256: "ab",
            storage_uri: "local:x",
            created_at: "2020-01-01T00:00:00Z",
            updated_at: "2020-01-01T00:00:00Z",
          },
        ]}
        reportModelCall={null}
      />,
    );
    const link = screen.getByRole("link", { name: "panel_csv" });
    expect(link.getAttribute("href")).toBe("/artifacts/artifact-uuid-1");
    expect(link.closest("li")?.textContent).toContain("panel.csv");
  });
});
