import "server-only";
import type { SimulateBody } from "../schemas";
import { serverEnv, type ServerEnv } from "./env";
import { HttpError } from "./http";

export interface EnginePolicy {
  policy: string;
  summary: Record<string, number | null>;
  daily: Record<string, number | boolean | string | null>[];
}

export interface EngineResult {
  engineVersion: string;
  seriesKey: string;
  originKey: string;
  historicalMean56: number;
  demand: number[];
  dates: string[];
  policies: EnginePolicy[];
}

export const ENGINE_TIMEOUT_MS = 20_000;
const FALLBACK = "precomputed Phase 5 results remain available";

/**
 * Server-to-server headers for the protected engine. `x-engine-key` authenticates to the FastAPI service;
 * `x-vercel-protection-bypass` passes the engine deployment's Vercel Authentication. Neither value is ever logged,
 * echoed in a response or sent anywhere but ENGINE_URL (redirects are refused, see `engineFetch`).
 */
export function engineHeaders(env: ServerEnv, options: { key: boolean }): Record<string, string> {
  const headers: Record<string, string> = { accept: "application/json" };
  if (options.key) headers["x-engine-key"] = env.engineKey;
  if (env.engineBypassSecret) headers["x-vercel-protection-bypass"] = env.engineBypassSecret;
  return headers;
}

/**
 * `redirect: "manual"`: Vercel answers unauthenticated requests with a redirect to its login service, and fetch
 * would otherwise follow it carrying the custom secret headers to another origin. Any 3xx is treated as a failure.
 */
function engineFetch(env: ServerEnv, path: string, init: RequestInit & { headers: Record<string, string> }, timeoutMs: number) {
  return fetch(new URL(path, env.engineUrl), {
    ...init,
    redirect: "manual",
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
}

/** One structured line without headers, URLs, bodies or secrets. */
function logEngineFailure(id: string, reason: string, status?: number) {
  console.warn(JSON.stringify({ requestId: id, event: "engine_failure", reason, engineStatus: status ?? null }));
}

/** Server-to-server call; the secrets never leave the server and engine error bodies are never echoed. */
export async function runEngine(body: SimulateBody, id: string): Promise<EngineResult> {
  const env = serverEnv();
  let response: Response;
  try {
    response = await engineFetch(env, "/simulate", {
      method: "POST",
      headers: { ...engineHeaders(env, { key: true }), "content-type": "application/json", "x-request-id": id },
      body: JSON.stringify({ seriesKey: body.seriesKey, originKey: body.originKey, policies: body.policies,
                             scenario: body.scenario, requestId: id }),
    }, ENGINE_TIMEOUT_MS);
  } catch (error) {
    const timeout = error instanceof DOMException && (error.name === "TimeoutError" || error.name === "AbortError");
    logEngineFailure(id, timeout ? "timeout" : "network");
    throw timeout
      ? new HttpError(504, "engine_unavailable", `The simulation engine timed out; ${FALLBACK}`)
      : new HttpError(502, "engine_unavailable", `The simulation engine is unavailable; ${FALLBACK}`);
  }
  if (response.ok) return (await response.json()) as EngineResult;
  await response.body?.cancel();
  if (response.status === 404) throw new HttpError(404, "not_found", "Unknown series or origin");
  if (response.status === 400) throw new HttpError(400, "invalid_request", "Scenario rejected by the engine");
  if (response.status === 401 || response.status === 403) {
    // Wrong engine key or Vercel protection rejected the bypass: a server misconfiguration, not the caller's fault.
    logEngineFailure(id, "engine_auth_rejected", response.status);
    throw new HttpError(502, "engine_unavailable", `The simulation engine is unavailable; ${FALLBACK}`);
  }
  if (response.status === 503) {
    logEngineFailure(id, "engine_temporarily_unavailable", 503);
    throw new HttpError(503, "engine_unavailable", `The simulation engine is temporarily unavailable; ${FALLBACK}`);
  }
  logEngineFailure(id, response.status >= 300 && response.status < 400 ? "engine_redirect_refused" : "engine_error",
                   response.status);
  throw new HttpError(502, "engine_unavailable", `The simulation engine is unavailable; ${FALLBACK}`);
}

export async function engineHealth(): Promise<{ reachable: boolean; engineVersion?: string }> {
  try {
    const env = serverEnv();
    const response = await engineFetch(env, "/health", { headers: engineHeaders(env, { key: false }) }, 3_000);
    if (!response.ok) {
      await response.body?.cancel();
      return { reachable: false };
    }
    const body = (await response.json()) as { engineVersion?: string; keyConfigured?: boolean };
    return { reachable: Boolean(body.keyConfigured), engineVersion: body.engineVersion };
  } catch {
    return { reachable: false };
  }
}
