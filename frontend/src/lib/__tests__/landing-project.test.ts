import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectRead } from "@/lib/api/types";

const listProjects = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/projects", () => ({ listProjects }));

const { resolveLandingProjectId, resolveRunnableProjectId } = await import(
  "@/lib/landing-project"
);

const user = { email: "a@b.c" } as never;
const project = (id: string, tickers: string[] | null): ProjectRead =>
  ({ id, tickers }) as ProjectRead;

describe("resolveRunnableProjectId", () => {
  beforeEach(() => {
    listProjects.mockReset();
    delete process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID;
  });

  it("skips a scope-less workspace in favour of one that can run", async () => {
    // The case that was actually observed: the first project was a recording workspace with
    // no tickers, so a question carried in from a demo was refused on arrival.
    listProjects.mockResolvedValue([project("recordings", []), project("configured", ["NVDA"])]);

    expect(await resolveRunnableProjectId(user)).toBe("configured");
    expect(await resolveLandingProjectId(user)).toBe("recordings");
  });

  it("treats a null ticker list as no scope", async () => {
    listProjects.mockResolvedValue([project("empty", null), project("configured", ["AAPL"])]);

    expect(await resolveRunnableProjectId(user)).toBe("configured");
  });

  it("honours the configured default when it has scope", async () => {
    process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID = "pinned";
    listProjects.mockResolvedValue([project("first", ["AAPL"]), project("pinned", ["MSFT"])]);

    expect(await resolveRunnableProjectId(user)).toBe("pinned");
  });

  it("passes over the configured default when it cannot run", async () => {
    process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID = "pinned";
    listProjects.mockResolvedValue([project("pinned", []), project("other", ["MSFT"])]);

    expect(await resolveRunnableProjectId(user)).toBe("other");
  });

  it("still lands somewhere real when nothing has scope", async () => {
    // Better a workspace with the scope editor in it than no destination at all.
    listProjects.mockResolvedValue([project("only", [])]);

    expect(await resolveRunnableProjectId(user)).toBe("only");
  });

  it("has nowhere to send an anonymous caller", async () => {
    expect(await resolveRunnableProjectId(null)).toBeNull();
    expect(listProjects).not.toHaveBeenCalled();
  });
});
