import type { Alert, AlertConfig, Finding, FindingsPage, SearchHit, Source, User, Watchlist } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("dwm_token");
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}/v1${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const form = new URLSearchParams({ username: email, password });
  const res = await fetch(`${BASE_URL}/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) throw new Error("Incorrect email or password");
  return res.json();
}

export async function getMe(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

// ── Findings ──────────────────────────────────────────────────────────────────

export async function getFindings(params?: {
  page?: number;
  page_size?: number;
  source_id?: number;
  keyword?: string;
  severity?: string;
  since?: string;
}): Promise<FindingsPage> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.source_id) qs.set("source_id", String(params.source_id));
  if (params?.keyword) qs.set("keyword", params.keyword);
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.since) qs.set("since", params.since);
  return apiFetch<FindingsPage>(`/findings?${qs}`);
}

export async function getFinding(id: number): Promise<Finding> {
  return apiFetch<Finding>(`/findings/${id}`);
}

export async function searchFindings(q: string, size = 20, from_ = 0): Promise<SearchHit[]> {
  const qs = new URLSearchParams({ q, size: String(size), from: String(from_) });
  return apiFetch<SearchHit[]>(`/findings/search?${qs}`);
}

// ── Sources ───────────────────────────────────────────────────────────────────

export async function getSources(activeOnly = true): Promise<Source[]> {
  return apiFetch<Source[]>(`/sources?active_only=${activeOnly}`);
}

export async function createSource(payload: {
  name: string;
  onion_url: string;
  crawl_frequency_hours: number;
}): Promise<Source> {
  return apiFetch<Source>("/sources", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateSource(
  id: number,
  payload: { name: string; onion_url: string; crawl_frequency_hours: number }
): Promise<Source> {
  return apiFetch<Source>(`/sources/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteSource(id: number): Promise<void> {
  return apiFetch<void>(`/sources/${id}`, { method: "DELETE" });
}

export async function triggerCrawl(sourceId: number): Promise<{ detail: string }> {
  return apiFetch<{ detail: string }>(`/sources/${sourceId}/crawl`, { method: "POST" });
}

// ── Watchlists ────────────────────────────────────────────────────────────────

export async function getWatchlists(): Promise<Watchlist[]> {
  return apiFetch<Watchlist[]>("/watchlists");
}

export async function createWatchlist(payload: {
  name: string;
  keywords: string[];
  domains: string[];
  emails: string[];
  category: string;
}): Promise<Watchlist> {
  return apiFetch<Watchlist>("/watchlists", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateWatchlist(
  id: number,
  payload: { name: string; keywords: string[]; domains: string[]; emails: string[]; category: string }
): Promise<Watchlist> {
  return apiFetch<Watchlist>(`/watchlists/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteWatchlist(id: number): Promise<void> {
  return apiFetch<void>(`/watchlists/${id}`, { method: "DELETE" });
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export async function getAlertHistory(params?: {
  page?: number;
  watchlist_id?: number;
  delivered?: boolean;
  acknowledged?: boolean;
}): Promise<Alert[]> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.watchlist_id) qs.set("watchlist_id", String(params.watchlist_id));
  if (params?.delivered !== undefined) qs.set("delivered", String(params.delivered));
  if (params?.acknowledged !== undefined) qs.set("acknowledged", String(params.acknowledged));
  return apiFetch<Alert[]>(`/alerts/history?${qs}`);
}

export async function acknowledgeAlert(id: number): Promise<Alert> {
  return apiFetch<Alert>(`/alerts/history/${id}/acknowledge`, { method: "POST" });
}

export async function getAlertConfigs(): Promise<AlertConfig[]> {
  return apiFetch<AlertConfig[]>("/alerts/config");
}

export async function createAlertConfig(payload: {
  watchlist_id: number;
  channel: string;
  destination: string;
}): Promise<AlertConfig> {
  return apiFetch<AlertConfig>("/alerts/config", { method: "POST", body: JSON.stringify(payload) });
}

export async function deleteAlertConfig(id: number): Promise<void> {
  return apiFetch<void>(`/alerts/config/${id}`, { method: "DELETE" });
}
