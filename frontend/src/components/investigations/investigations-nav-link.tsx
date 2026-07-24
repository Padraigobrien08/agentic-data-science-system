"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Path-aware discovery link: shows "Investigations" in the header whenever the
 * user is inside a project route, so the read surface is reachable without
 * restructuring the (server-rendered) header or the chat shell.
 */
export function InvestigationsNavLink() {
  const pathname = usePathname() ?? "";
  const match = /^\/projects\/([^/]+)/.exec(pathname);
  if (!match) return null;
  const projectId = match[1];
  const active = pathname.includes(`/projects/${projectId}/investigations`);
  return (
    <Link
      href={`/projects/${projectId}/investigations`}
      aria-current={active ? "page" : undefined}
      className={`hidden rounded-full border border-[var(--border)] px-4 py-2 font-medium transition hover:-translate-y-0.5 hover:bg-white sm:inline-flex ${
        active ? "bg-white text-[var(--foreground)]" : "bg-white/80 text-[var(--foreground)]"
      }`}
    >
      Investigations
    </Link>
  );
}
