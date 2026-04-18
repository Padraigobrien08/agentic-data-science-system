import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthEntryGuidance } from "@/components/auth/auth-entry-guidance";

vi.mock("next/link", () => ({
  default({ children, href }: { children: ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  },
}));

describe("AuthEntryGuidance", () => {
  it("renders create-account guidance when open registration is enabled", () => {
    render(
      <AuthEntryGuidance
        capabilities={{
          allow_open_registration: true,
          bootstrap_required: false,
          bootstrap_completed: false,
        }}
        nextPath="/projects/demo"
      />,
    );

    expect(screen.getAllByText("Create account")[0]).toBeTruthy();
    expect(screen.getByRole("link", { name: "Create account" }).getAttribute("href")).toBe(
      "/register?next=%2Fprojects%2Fdemo",
    );
    expect(screen.getByRole("link", { name: "Sign in" }).getAttribute("href")).toBe(
      "/login?next=%2Fprojects%2Fdemo",
    );
  });

  it("renders bootstrap-required guidance before the first admin exists", () => {
    render(
      <AuthEntryGuidance
        capabilities={{
          allow_open_registration: false,
          bootstrap_required: true,
          bootstrap_completed: false,
        }}
        nextPath="/projects"
      />,
    );

    expect(screen.getByText("Bootstrap required")).toBeTruthy();
    expect(screen.getByText(/POST \/v1\/auth\/bootstrap/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign in" }).getAttribute("href")).toBe("/login");
  });

  it("renders sign-in-only guidance after bootstrap is complete", () => {
    render(
      <AuthEntryGuidance
        capabilities={{
          allow_open_registration: false,
          bootstrap_required: false,
          bootstrap_completed: true,
        }}
        nextPath="/projects"
      />,
    );

    expect(screen.getAllByText("Sign in").length).toBeGreaterThan(0);
    expect(screen.getByText(/bootstrap is already complete/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign in" }).getAttribute("href")).toBe("/login");
    expect(screen.queryByRole("link", { name: "Create account" })).toBeNull();
  });
});
