"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { SESSION_COOKIE_NAME } from "@/lib/auth/constants";
import { getApiBaseUrl } from "@/lib/api/config";
import type { AuthCapabilitiesResponse } from "@/lib/api/types";

function safeNextPath(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) {
    return "/projects";
  }
  return raw;
}

function parseDetail(text: string): string {
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    const d = j.detail;
    if (typeof d === "string") return d;
  } catch {
    /* ignore */
  }
  return text.slice(0, 200) || "Request failed";
}

const FALLBACK_AUTH_CAPABILITIES: AuthCapabilitiesResponse = {
  allow_open_registration: false,
  bootstrap_required: false,
  bootstrap_completed: true,
};

async function fetchAuthCapabilities(): Promise<AuthCapabilitiesResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/v1/auth/capabilities`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    return FALLBACK_AUTH_CAPABILITIES;
  }
  try {
    return (await res.json()) as AuthCapabilitiesResponse;
  } catch {
    return FALLBACK_AUTH_CAPABILITIES;
  }
}

function registrationDisabledMessage(capabilities: AuthCapabilitiesResponse): string {
  if (capabilities.bootstrap_required) {
    return "Registration is disabled until an operator completes bootstrap with the configured bootstrap token.";
  }
  if (capabilities.bootstrap_completed) {
    return "Registration is disabled for this environment. Bootstrap is already complete, so use Sign in or ask an operator to explicitly enable open registration.";
  }
  return "Registration is disabled. Ask an operator to complete bootstrap or explicitly enable open registration.";
}

export type LoginState = { error?: string };

export type RegisterState = { error?: string };

async function completeLoginSession(
  email: string,
  password: string,
  next: string,
): Promise<LoginState> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });
  const text = await res.text();
  if (!res.ok) {
    return { error: parseDetail(text) };
  }
  let data: { access_token: string; expires_in: number };
  try {
    data = JSON.parse(text) as { access_token: string; expires_in: number };
  } catch {
    return { error: "Invalid response from server." };
  }

  const jar = await cookies();
  jar.set(SESSION_COOKIE_NAME, data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: data.expires_in,
    path: "/",
  });

  redirect(next);
}

export async function loginAction(_prev: LoginState, formData: FormData): Promise<LoginState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const nextRaw = String(formData.get("next") ?? "").trim();
  const next = safeNextPath(nextRaw || null);

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  return completeLoginSession(email, password, next);
}

export async function registerAction(
  _prev: RegisterState,
  formData: FormData,
): Promise<RegisterState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const displayName = String(formData.get("display_name") ?? "").trim() || null;
  const nextRaw = String(formData.get("next") ?? "").trim();
  const next = safeNextPath(nextRaw || null);

  if (!email || !password) {
    return { error: "Email and password are required." };
  }
  if (password.length < 10) {
    return { error: "Password must be at least 10 characters (backend requirement)." };
  }

  const base = getApiBaseUrl();
  const reg = await fetch(`${base}/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
    }),
    cache: "no-store",
  });
  const regText = await reg.text();
  if (!reg.ok) {
    const detail = parseDetail(regText);
    if (detail === "Registration is disabled") {
      return { error: registrationDisabledMessage(await fetchAuthCapabilities()) };
    }
    return { error: detail };
  }

  return completeLoginSession(email, password, next);
}

export async function logoutAction(): Promise<void> {
  const jar = await cookies();
  jar.delete(SESSION_COOKIE_NAME);
  redirect("/login");
}

export type InterestState = { ok?: boolean; error?: string };

/** Optional landing-page email capture — a signal of interest, not a sign-up. */
export async function submitInterestAction(
  _prev: InterestState,
  formData: FormData,
): Promise<InterestState> {
  const email = String(formData.get("email") ?? "").trim();
  if (!email) {
    return { error: "Enter an email address." };
  }

  const base = getApiBaseUrl();
  try {
    const res = await fetch(`${base}/v1/interest`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email, source: "landing" }),
      cache: "no-store",
    });
    if (!res.ok) {
      return { error: parseDetail(await res.text()) };
    }
  } catch {
    return { error: "Could not submit right now — try again." };
  }
  return { ok: true };
}
