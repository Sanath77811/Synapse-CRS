import type { Page } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const DEFAULT_TIMEOUT_MS = 12_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function sanitizeBody(text: string): { code: string; message: string } {
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed && typeof parsed === "object") {
      const record = parsed as Record<string, unknown>;
      const code = typeof record.code === "string" ? record.code : "http_error";
      const message = typeof record.message === "string" ? record.message : `HTTP error`;
      return { code, message: message.slice(0, 180) };
    }
  } catch {
    /* not json */
  }
  return { code: "http_error", message: `HTTP error` };
}

export async function apiRequest<T>(
  path: string,
  options: {
    token?: string | null;
    method?: "GET" | "POST";
    body?: unknown;
    signal?: AbortSignal;
    timeoutMs?: number;
  } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  if (options.signal) {
    options.signal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });
    const text = await response.text();
    if (!response.ok) {
      const parsed = sanitizeBody(text);
      const mapped =
        response.status === 401
          ? "authentication_failed"
          : response.status === 403
            ? "authorization_failed"
            : response.status === 404
              ? "not_found"
              : response.status === 422
                ? "validation_failed"
                : parsed.code;
      throw new ApiError(response.status, mapped, parsed.message);
    }
    if (!text) {
      return {} as T;
    }
    return JSON.parse(text) as T;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "aborted", "Request timed out or was cancelled.");
    }
    throw new ApiError(0, "network", "Control plane is unreachable.");
  } finally {
    clearTimeout(timer);
  }
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
