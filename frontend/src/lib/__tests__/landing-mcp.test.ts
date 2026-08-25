import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * The landing page's MCP transcript must show calls the server can answer.
 *
 * It showed two that it could not. `resources/read hypotheses` and `resources/read
 * evidence/7` appear nowhere in `backend/mcp/server.py` — hypotheses and evidence are
 * *tools*, and the server registers exactly two resources, `artifact://{id}` and
 * `investigation://{id}/conclusion`. A reader who took the panel at face value and tried it
 * against the hosted server would have got a method-not-found on both lines.
 *
 * That is a worse failure than a typo on a marketing page. The section it sits under argues
 * that everything goes through one contract with no privileged back door, and it made that
 * argument with a transcript that does not typecheck against the contract.
 *
 * Parsed from the server source rather than mirrored into a fixture: a fixture is one more
 * hand-maintained restatement, which is the class of problem this test exists to catch.
 */

const SERVER = join(process.cwd(), "..", "backend", "mcp", "server.py");
const PANEL = join(process.cwd(), "src", "components", "landing", "landing-page.tsx");

function serverSource(): string {
  return readFileSync(SERVER, "utf8");
}

/**
 * The panel with JSX plumbing flattened out, so the assertions can match what a *reader*
 * sees rather than how the file happens to be wrapped. `{" "}` separators and `{"{id}"}`
 * escapes are formatting, and a test that has to know about them breaks on `prettier`.
 */
function panelText(): string {
  return readFileSync(PANEL, "utf8")
    .replace(/\{" "\}/g, " ")
    .replace(/\{"([^"]*)"\}/g, "$1")
    .replace(/\s+/g, " ");
}

function registeredTools(): Set<string> {
  const source = serverSource();
  const names = new Set<string>();
  const pattern = /@mcp\.tool\(\)\s*\ndef\s+(\w+)/g;
  for (const match of source.matchAll(pattern)) names.add(match[1]);
  return names;
}

/** Resource URIs the panel shows a client reading. */
function resourcesRead(): string[] {
  return [...panelText().matchAll(/resources\/read\s*<span[^>]*>([^<]+)</g)].map((m) =>
    m[1].trim(),
  );
}

function registeredResourceUris(): string[] {
  const source = serverSource();
  return [...source.matchAll(/@mcp\.resource\("([^"]+)"\)/g)].map((m) => m[1]);
}

describe("landing MCP panel", () => {
  it("can read the server it describes", () => {
    expect(registeredTools().size).toBeGreaterThan(0);
    expect(registeredResourceUris().length).toBeGreaterThan(0);
  });

  it("only calls tools the server registers", () => {
    const tools = registeredTools();
    const called = [...panelText().matchAll(/tools\/call\s*<span[^>]*>([\w-]+)</g)].map(
      (m) => m[1],
    );

    expect(called.length).toBeGreaterThan(0);
    for (const name of called) {
      expect(tools, `panel calls tools/call ${name}, which the server does not register`).toContain(
        name,
      );
    }
  });

  it("only reads resources the server registers", () => {
    const schemes = registeredResourceUris().map((uri) => uri.split("://")[0]);
    const read = resourcesRead();

    expect(read.length).toBeGreaterThan(0);
    for (const uri of read) {
      const scheme = uri.split("://")[0];
      expect(
        schemes,
        `panel reads ${uri}, but the server registers no ${scheme}:// resource`,
      ).toContain(scheme);
    }
  });

  it("does not present a tool as a resource", () => {
    const tools = registeredTools();
    const read = resourcesRead();

    for (const uri of read) {
      expect(tools, `${uri} is a tool, not a resource`).not.toContain(uri);
    }
  });
});
