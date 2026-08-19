"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { SiteHeader } from "@/components/layout/site-header";
import type { CurrentUser } from "@/lib/api/types";

/**
 * Chrome switch across four surfaces:
 * - Chat: full-viewport app; opts out of the header + padded main entirely.
 * - Landing: ships its own dark header and edge-to-edge rules, so it opts out
 *   of the shared header + padded main for the same reason chat does.
 * - Authenticated app (projects, artifacts): the zinc `.app-skin` shell, so leaving
 *   the chat to inspect runs/trace stays one visual system.
 * - Marketing (auth): the standard warm shell.
 */
export function AppChrome({ user, children }: { user: CurrentUser | null; children: ReactNode }) {
  const pathname = usePathname() ?? "";

  if (/\/chat(\/|$)/.test(pathname) || pathname === "/") {
    return <>{children}</>;
  }

  const shell = (
    <>
      <SiteHeader user={user} />
      <main className="mx-auto w-full max-w-[90rem] px-3 py-8 sm:px-5 lg:px-6">{children}</main>
    </>
  );

  if (pathname.startsWith("/projects") || pathname.startsWith("/artifacts")) {
    return (
      <div className="app-skin min-h-screen bg-[var(--background)] text-[var(--foreground)]">{shell}</div>
    );
  }

  return shell;
}
