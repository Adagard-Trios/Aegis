/**
 * frontend/app/lib/api.ts
 *
 * Shared HTTP + SSE client for the MedVerse backend.
 *
 * - Base URL from `NEXT_PUBLIC_API_URL` (default http://localhost:8000
 *   so dev-server usage keeps working without a .env file).
 * - Transparent bearer-token injection from localStorage.medverse_token.
 * - Typed helpers for GET / POST / POST-FormData.
 * - SSE URL builder that attaches the token as a query param because
 *   EventSource can't carry custom headers.
 */

export const API_URL =
  (typeof process !== "undefined" && process.env && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export const TOKEN_STORAGE_KEY = "medverse_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    /* noop */
  }
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* noop */
  }
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function apiGet<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(init.headers || {}), ...authHeaders() },
  });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: form,
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

/**
 * Build the EventSource URL for /stream. EventSource can't attach
 * Authorization headers, so when a token is present we append it as a
 * query parameter — the backend's /stream handler honors ?token=.
 */
export function buildStreamUrl(path = "/stream", extra: Record<string, string> = {}): string {
  const url = new URL(`${API_URL}${path}`);
  const token = getToken();
  if (token) url.searchParams.set("token", token);
  for (const [k, v] of Object.entries(extra)) {
    if (v) url.searchParams.set(k, v);
  }
  return url.toString();
}

// ─── Auth helpers ─────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  auth_enabled: boolean;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await apiPost<LoginResponse>("/api/auth/login", { username, password });
  if (res?.access_token) setToken(res.access_token);
  return res;
}

export async function logout(): Promise<void> {
  clearToken();
}

// ─── History series (for /history page) ───────────────────────────

export interface HistoryPoint {
  ts: string;
  hr: number | null;
  spo2: number | null;
  br: number | null;
  hrv: number | null;
}

export function fetchHistory(
  params: { resolution?: "1m" | "1h"; patient_id?: string; limit?: number } = {}
): Promise<HistoryPoint[]> {
  const qs = new URLSearchParams();
  if (params.resolution) qs.set("resolution", params.resolution);
  if (params.patient_id) qs.set("patient_id", params.patient_id);
  if (params.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiGet<HistoryPoint[]>(`/api/history${q ? `?${q}` : ""}`);
}
