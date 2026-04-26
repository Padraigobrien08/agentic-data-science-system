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

import { deleteChatAction } from "@/actions/projects";

function buildDeleteFormData(projectId: string) {
  const formData = new FormData();
  formData.set("projectId", projectId);
  return formData;
}

describe("deleteChatAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
