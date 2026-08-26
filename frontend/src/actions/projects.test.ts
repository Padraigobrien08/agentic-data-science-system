import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  revalidatePathMock,
  redirectMock,
  archiveProjectMock,
  createProjectMock,
  listProjectsMock,
  updateProjectMock,
} = vi.hoisted(() => ({
  revalidatePathMock: vi.fn(),
  redirectMock: vi.fn(),
  archiveProjectMock: vi.fn(),
  createProjectMock: vi.fn(),
  listProjectsMock: vi.fn(),
  updateProjectMock: vi.fn(),
}));

vi.mock("next/cache", () => ({
  revalidatePath: revalidatePathMock,
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

vi.mock("@/lib/api/projects", () => ({
  archiveProject: archiveProjectMock,
  createProject: createProjectMock,
  listProjects: listProjectsMock,
  updateProject: updateProjectMock,
}));

import { createProjectAction, deleteChatAction } from "@/actions/projects";

function buildDeleteFormData(projectId: string) {
  const formData = new FormData();
  formData.set("projectId", projectId);
  return formData;
}

function buildCreateFormData(tickers: string, name = "") {
  const formData = new FormData();
  formData.set("tickers", tickers);
  formData.set("name", name);
  return formData;
}

/**
 * Make `redirect` behave like the real one: it signals by throwing.
 *
 * The default `vi.fn()` returns undefined, which is why an action that caught its own
 * redirect still passed every test here while rendering `NEXT_REDIRECT` as a form error
 * in the browser.
 */
function throwingRedirect() {
  redirectMock.mockImplementation((url: string) => {
    const error = new Error("NEXT_REDIRECT");
    (error as Error & { digest: string }).digest = `NEXT_REDIRECT;replace;${url};307;`;
    throw error;
  });
}

describe("createProjectAction", () => {
  // `resetAllMocks`, not `clearAllMocks`: this block installs a throwing `redirect`, and
  // clearing only wipes recorded calls, so the implementation would leak into every later test.
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("lets the redirect escape instead of reporting it as a form error", async () => {
    createProjectMock.mockResolvedValue({ id: "project-9" });
    throwingRedirect();

    await expect(
      createProjectAction({}, buildCreateFormData("AAPL, MSFT")),
    ).rejects.toThrow("NEXT_REDIRECT");

    expect(createProjectMock).toHaveBeenCalledWith({
      name: "AAPL + MSFT chat",
      tickers: ["AAPL", "MSFT"],
    });
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects");
    expect(redirectMock).toHaveBeenCalledWith("/projects/project-9/chat");
  });

  it("still reports a failed create as a form error", async () => {
    createProjectMock.mockRejectedValue(new Error("boom"));
    throwingRedirect();

    await expect(createProjectAction({}, buildCreateFormData("AAPL"))).resolves.toEqual({
      error: "boom",
    });
    expect(redirectMock).not.toHaveBeenCalled();
  });

  it("rejects an empty ticker list without calling the API", async () => {
    await expect(createProjectAction({}, buildCreateFormData("  "))).resolves.toEqual({
      error: "Add at least one ticker (comma or newline separated).",
    });
    expect(createProjectMock).not.toHaveBeenCalled();
  });
});

describe("deleteChatAction", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("archives the current chat and redirects to the next remaining chat", async () => {
    archiveProjectMock.mockResolvedValue({ id: "project-1" });
    listProjectsMock.mockResolvedValue([
      {
        id: "project-2",
        owner_user_id: "user-1",
        name: "AAPL chat",
        slug: null,
        description: null,
        settings_json: null,
        tickers: ["AAPL"],
        archived_at: null,
        created_at: "2026-04-20T10:00:00Z",
        updated_at: "2026-04-20T10:00:00Z",
      },
    ]);

    await deleteChatAction("project-1", buildDeleteFormData("project-1"));

    expect(archiveProjectMock).toHaveBeenCalledWith("project-1", expect.any(String));
    expect(listProjectsMock).toHaveBeenCalled();
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects");
    expect(redirectMock).toHaveBeenCalledWith("/projects/project-2/chat");
  });

  it("archives a non-active chat and keeps the current chat open", async () => {
    archiveProjectMock.mockResolvedValue({ id: "project-2" });

    await deleteChatAction("project-1", buildDeleteFormData("project-2"));

    expect(archiveProjectMock).toHaveBeenCalledWith("project-2", expect.any(String));
    expect(listProjectsMock).not.toHaveBeenCalled();
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/project-2/chat");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/project-2/runs");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/project-1/chat");
    expect(redirectMock).toHaveBeenCalledWith("/projects/project-1/chat");
  });
});
