import "server-only";

import { getApiBaseUrl } from "./config";
import { ApiError } from "./errors";

type RequestBody = Record<string, unknown> | unknown[] | null;

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>("GET", path, undefined, init);
}

export async function apiPost<T>(
  path: string,
  body: object | unknown[] | null,
  init?: RequestInit,
): Promise<T> {
  return request<T>("POST", path, body as RequestBody, init);
}

async function request<T>(
  method: string,
  path: string,
  body: RequestBody | undefined,
  init?: RequestInit,
): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const headers: HeadersInit = {
    Accept: "application/json",
    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...init?.headers,
  };
  const res = await fetch(url, {
    ...init,
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const text = await res.text();
  if (!res.ok) {
    throw new ApiError(res.status, text || res.statusText);
  }
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}
