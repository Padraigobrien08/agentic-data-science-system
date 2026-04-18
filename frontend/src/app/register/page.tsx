import Link from "next/link";
import { redirect } from "next/navigation";

import { AuthEntryGuidance } from "@/components/auth/auth-entry-guidance";
import { RegisterForm } from "@/components/auth/register-form";
import { getAuthCapabilities } from "@/lib/api/runs";
import { getCurrentUser } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export default async function RegisterPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<{ next?: string }>;
}>) {
  const { next } = await searchParams;
  const user = await getCurrentUser();
  if (user) {
    redirect(next?.startsWith("/") && !next.startsWith("//") ? next : "/projects");
  }

  const nextPath = next?.startsWith("/") && !next.startsWith("//") ? next : "/projects";
  const capabilities = await getAuthCapabilities().catch(() => ({
    allow_open_registration: false,
    bootstrap_required: false,
    bootstrap_completed: true,
  }));

  if (!capabilities.allow_open_registration) {
    return (
      <div className="mx-auto max-w-md space-y-6">
        <div>
          <h1 className="text-lg font-semibold">
            {capabilities.bootstrap_required ? "Bootstrap required" : "Registration closed"}
          </h1>
          <p className="mt-1 text-xs text-[var(--muted)]">
            This environment is not accepting ordinary self-registration right now.
          </p>
        </div>
        <AuthEntryGuidance capabilities={capabilities} nextPath={nextPath} />
        <Link href="/login" className="block font-mono text-xs underline">
          ← Sign in instead
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Create account</h1>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Calls <code className="text-[var(--foreground)]">POST /v1/auth/register</code>, then signs you
          in with the same credentials. This form is only shown when open registration is enabled
          for the current environment (
          <code className="text-[var(--foreground)]">EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=true</code>
          ).
        </p>
      </div>
      <RegisterForm nextPath={nextPath} />
      <Link href="/login" className="block font-mono text-xs underline">
        ← Sign in instead
      </Link>
    </div>
  );
}
