import { redirect } from "next/navigation";

import { AuthEntryGuidance } from "@/components/auth/auth-entry-guidance";
import { LoginForm } from "@/components/auth/login-form";
import { getCurrentUser } from "@/lib/auth/session";
import { getAuthCapabilities } from "@/lib/api/runs";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<{ next?: string }>;
}>) {
  const { next } = await searchParams;
  const nextPath = next?.startsWith("/") && !next.startsWith("//") ? next : "/projects";
  const user = await getCurrentUser();
  if (user) {
    redirect(nextPath);
  }
  const capabilities = await getAuthCapabilities().catch(() => ({
    allow_open_registration: false,
    bootstrap_required: false,
    bootstrap_completed: true,
  }));

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Sign in</h1>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Uses <code className="text-[var(--foreground)]">POST /v1/auth/login</code> — JWT stored in an
          HttpOnly cookie for server-side API calls.
        </p>
      </div>
      <LoginForm nextPath={nextPath} />
      <AuthEntryGuidance capabilities={capabilities} nextPath={nextPath} />
    </div>
  );
}
