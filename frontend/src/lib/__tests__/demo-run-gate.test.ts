import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * The lock on a recorded run's composer has to be a fact about the deployment. If it were a
 * constant, a clone with its own backend and keys would still meet a dead composer and no
 * way to tell why — so these pin that each input flips it, and that nothing is claimed to be
 * runnable that is not.
 */
const staticShowcase = vi.hoisted(() => vi.fn());
const getCurrentUser = vi.hoisted(() => vi.fn());
const resolveLandingProjectId = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/demos", () => ({ staticShowcase }));
vi.mock("@/lib/auth/session", () => ({ getCurrentUser }));
vi.mock("@/lib/landing-project", () => ({ resolveLandingProjectId }));

const { resolveDemoRunGate } = await import("@/lib/demo-run-gate");

describe("resolveDemoRunGate", () => {
  beforeEach(() => {
    staticShowcase.mockReset();
    getCurrentUser.mockReset();
    resolveLandingProjectId.mockReset();
  });

  it("locks the static export, without asking who is reading", async () => {
    staticShowcase.mockReturnValue(true);

    expect(await resolveDemoRunGate()).toEqual({ kind: "no_backend" });
    // No backend means no session endpoint either; asking would be a wasted failing call.
    expect(getCurrentUser).not.toHaveBeenCalled();
  });

  it("locks an anonymous reader even when a backend is attached", async () => {
    staticShowcase.mockReturnValue(false);
    getCurrentUser.mockResolvedValue(null);

    expect(await resolveDemoRunGate()).toEqual({ kind: "signed_out" });
  });

  it("locks a signed-in reader who has nowhere to run", async () => {
    staticShowcase.mockReturnValue(false);
    getCurrentUser.mockResolvedValue({ email: "a@b.c" });
    resolveLandingProjectId.mockResolvedValue(null);

    expect(await resolveDemoRunGate()).toEqual({ kind: "no_workspace" });
  });

  it("opens once a backend, an account and a workspace all exist", async () => {
    staticShowcase.mockReturnValue(false);
    getCurrentUser.mockResolvedValue({ email: "a@b.c" });
    resolveLandingProjectId.mockResolvedValue("project-1");

    expect(await resolveDemoRunGate()).toEqual({ kind: "ready" });
  });
});
