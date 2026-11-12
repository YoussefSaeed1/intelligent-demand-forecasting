/**
 * Typed browser client for the Phase 7B `/api/v1` routes. It is the only way pages read data: there is no
 * database or engine access from the browser, no secret in the bundle, and no endpoint beyond the 7B contract.
 */
import type { ApiErrorBody, SimulateRequest, SimulateResponse } from "./types";

export const API_BASE = "/api/v1";
const READ_TIMEOUT_MS = 15_000;
/** Slightly above the server's 20 s engine timeout so the server's own 502 normally arrives first. */
export const SIMULATE_TIMEOUT_MS = 25_000;
const CACHE_LIMIT = 120;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly fields: { field: string; message: string }[] = [],
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get retryable(): boolean {
    return this.status === 0 || this.status === 408 || this.status === 429 || this.status >= 500;
  }
}

/** Deterministic path: keys sorted, empty values dropped, values URL-encoded (cache keys are stable). */
export function apiPath(route: string, query: Record<string, string | number | undefined | null> = {}): string {
  const entries = Object.entries(query)
    .filter((entry): entry is [string, string | number] => entry[1] !== undefined && entry[1] !== null && entry[1] !== "")
    .sort(([a], [b]) => a.localeCompare(b));
  const search = new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
  return `${API_BASE}${route}${search ? `?${search}` : ""}`;
}

function linkedSignal(timeoutMs: number, outer?: AbortSignal): AbortSignal {
  const timeout = AbortSignal.timeout(timeoutMs);
  return outer ? AbortSignal.any([outer, timeout]) : timeout;
}

async function toError(response: Response): Promise<ApiError> {
  let body: Partial<ApiErrorBody> = {};
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    // Non-JSON error bodies are not shown to users.
  }
  return new ApiError(response.status, body.error ?? "http_error",
                      body.message ?? "The request could not be completed", body.fields ?? [], body.requestId);
}

function networkError(error: unknown, outer?: AbortSignal): ApiError {
  if (outer?.aborted) return new ApiError(0, "aborted", "Request cancelled");
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return new ApiError(408, "timeout", "The request timed out; please retry");
  }
  return new ApiError(0, "network_error", "The service could not be reached; check the connection and retry");
}

async function request<T>(path: string, init: RequestInit, timeoutMs: number, outer?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, signal: linkedSignal(timeoutMs, outer) });
  } catch (error) {
    throw networkError(error, outer);
  }
  if (!response.ok) throw await toError(response);
  return (await response.json()) as T;
}

/* Read responses are immutable per export version, so successful GETs are memoised for the session. */
const cache = new Map<string, Promise<unknown>>();

export function apiGet<T>(path: string, options: { signal?: AbortSignal } = {}): Promise<T> {
  const hit = cache.get(path);
  if (hit) return hit as Promise<T>;
  const pending = request<T>(path, { method: "GET", headers: { accept: "application/json" } }, READ_TIMEOUT_MS);
  cache.set(path, pending);
  if (cache.size > CACHE_LIMIT) cache.delete(cache.keys().next().value as string);
  pending.catch(() => cache.delete(path));
  if (!options.signal) return pending;
  const signal = options.signal;
  // The shared request is not cancelled (others may await it); the caller simply stops listening.
  return new Promise<T>((resolve, reject) => {
    const abort = () => reject(new ApiError(0, "aborted", "Request cancelled"));
    if (signal.aborted) return abort();
    signal.addEventListener("abort", abort, { once: true });
    pending.then(resolve, reject).finally(() => signal.removeEventListener("abort", abort));
  });
}

export function clearApiCache() {
  cache.clear();
}

export function simulate(body: SimulateRequest, signal?: AbortSignal): Promise<SimulateResponse> {
  return request<SimulateResponse>(`${API_BASE}/planner/simulate`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(body),
  }, SIMULATE_TIMEOUT_MS, signal);
}

/** Bounded CSV of one run (at most 4 policies x 28 days); the server re-runs the engine, nothing is stored. */
export async function exportPlannerCsv(body: SimulateRequest, signal?: AbortSignal): Promise<{ blob: Blob; filename: string }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/planner/export`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: linkedSignal(SIMULATE_TIMEOUT_MS, signal),
    });
  } catch (error) {
    throw networkError(error, signal);
  }
  if (!response.ok) throw await toError(response);
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "planner_run.csv";
  return { blob: await response.blob(), filename };
}
