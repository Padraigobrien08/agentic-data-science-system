import Link from "next/link";

import { logoutAction } from "@/actions/auth";
import type { CurrentUser } from "@/lib/api/types";

type Props = {
  user: CurrentUser | null;
};

export function SiteHeader({ user }: Props) {
  return (
    <header className="sticky top-0 z-40 border-b border-[rgba(23,32,51,0.08)] bg-[color:rgba(248,250,255,0.82)] backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[90rem] items-center justify-between gap-4 px-3 sm:px-5 lg:px-6">
        <Link href="/" className="inline-flex items-center gap-3">
          <span className="h-4 w-4 rounded-full bg-[linear-gradient(135deg,var(--accent),var(--accent-warm))] shadow-[0_0_24px_rgba(31,111,255,0.24)]" />
          <span className="text-[1rem] font-semibold tracking-[-0.04em] text-[var(--foreground)]">EDGAR Analysis</span>
        </Link>
        <div className="flex items-center gap-3 text-xs">
          {user ? (
            <>
              <span
                className="hidden max-w-[18rem] truncate rounded-full border border-[var(--border)] bg-white/82 px-3 py-2 text-[11px] text-[var(--muted)] sm:inline-flex"
                title={user.email}
              >
                {user.email}
              </span>
              <form action={logoutAction}>
                <button
                  type="submit"
                  className="rounded-full border border-[var(--border)] bg-white/80 px-4 py-2 font-medium text-[var(--foreground)] transition hover:-translate-y-0.5 hover:bg-white"
                >
                  Sign out
                </button>
              </form>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-full border border-[var(--border)] bg-white/85 px-4 py-2 font-medium text-[var(--foreground)] transition hover:-translate-y-0.5 hover:bg-white"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
