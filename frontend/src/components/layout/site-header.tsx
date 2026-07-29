import Link from "next/link";

import { logoutAction } from "@/actions/auth";
import { InvestigationsNavLink } from "@/components/investigations/investigations-nav-link";
import type { CurrentUser } from "@/lib/api/types";

type Props = {
  user: CurrentUser | null;
};

export function SiteHeader({ user }: Props) {
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--surface)] backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[90rem] items-center justify-between gap-4 px-3 sm:px-5 lg:px-6">
        <Link href="/" className="inline-flex items-center gap-3">
          <span className="h-4 w-4 rounded-full bg-[linear-gradient(135deg,var(--accent),var(--accent-warm))] shadow-[0_0_24px_rgba(31,111,255,0.24)]" />
          <span className="text-[1rem] font-semibold tracking-[-0.04em] text-[var(--foreground)]">EDGAR Analysis</span>
        </Link>
        <div className="flex items-center gap-3 text-xs">
          {user ? (
            <>
              <InvestigationsNavLink />
              <span
                className="hidden max-w-[18rem] truncate rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[11px] text-[var(--muted)] sm:inline-flex"
                title={user.email}
              >
                {user.email}
              </span>
              <form action={logoutAction}>
                <button
                  type="submit"
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 font-medium text-[var(--foreground)] transition hover:-translate-y-0.5 hover:border-[var(--accent)]"
                >
                  Sign out
                </button>
              </form>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 font-medium text-[var(--foreground)] transition hover:-translate-y-0.5 hover:border-[var(--accent)]"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
