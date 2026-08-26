import Link from "next/link";

/**
 * Rendered instead of an auth form when the deployment is the static replay showcase (D9):
 * there is no backend to sign in to, and an honest notice beats a form that 500s on submit.
 */
export function StaticShowcaseNotice() {
  return (
    <div className="mx-auto max-w-md space-y-4 rounded-lg border border-neutral-200 p-6 dark:border-neutral-800">
      <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
        This showcase has no live backend
      </h1>
      <p className="text-sm text-neutral-600 dark:text-neutral-300">
        You are looking at the static replay tier: real recorded investigations, served without
        an API. Accounts, guest sessions, and live runs exist in the full deployment.
      </p>
      <div className="flex flex-wrap gap-3 text-sm">
        <Link href="/demos" className="font-medium underline">
          Explore the recorded investigations
        </Link>
        <a
          href="https://github.com/Padraigobrien08/auditable-agent-loop"
          className="font-medium underline"
        >
          Run the full stack locally
        </a>
      </div>
    </div>
  );
}
