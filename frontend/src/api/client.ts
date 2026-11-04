import type { Page } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly body: string;

  constructor(status: number, body: string) {
    super(`HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

export async function apiRequest<T>(
  path: string,
  options: {
    token?: string | null;
    method?: "GET" | "POST";
    body?: unknown;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
  const text = await response.text();
  if (!response.ok) {
    throw new ApiError(response.status, text.slice(0, 400));
  }
  if (!text) {
    return {} as T;
  }
  return JSON.parse(text) as T;
}

export async function listAll<T>(
  path: string,
  token: string,
  signal?: AbortSignal,
): Promise<T[]> {
  const first = await apiRequest<Page<T>>(path.includes("?") ? path : `${path}?limit=100&offset=0`, {
    token,
    signal,
  });
  return first.items;
}
