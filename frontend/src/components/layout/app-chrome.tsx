"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { SiteHeader } from "@/components/layout/site-header";
import type { CurrentUser } from "@/lib/api/types";

/**
 * Chrome switch across three surfaces:
 * - Chat: full-viewport app; opts out of the header + padded main entirely.
 * - Authenticated app (projects, artifacts): the zinc `.app-skin` shell, so leaving
 *   the chat to inspect runs/trace stays one visual system.
 * - Marketing (landing, auth): the standard warm shell.
 */
export function AppChrome({ user, children }: { user: CurrentUser | null; children: ReactNode }) {
  const pathname = usePathname() ?? "";

  if (/\/chat(\/|$)/.test(pathname)) {
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
