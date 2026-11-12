import "server-only";
import type { SimulateBody } from "../schemas";
import { serverEnv } from "./env";
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

/** Server-to-server call; the engine key never leaves the server and engine errors are never echoed. */
export async function runEngine(body: SimulateBody, id: string): Promise<EngineResult> {
  const env = serverEnv();
  let response: Response;
  try {
    response = await fetch(new URL("/simulate", env.engineUrl), {
      method: "POST",
      headers: { "content-type": "application/json", "x-engine-key": env.engineKey, "x-request-id": id },
      body: JSON.stringify({ seriesKey: body.seriesKey, originKey: body.originKey, policies: body.policies,
                             scenario: body.scenario, requestId: id }),
      signal: AbortSignal.timeout(20_000),
      cache: "no-store",
    });
  } catch {
    throw new HttpError(502, "engine_unavailable",
                        "The simulation engine is unavailable; precomputed Phase 5 results remain available");
  }
  if (response.status === 404) throw new HttpError(404, "not_found", "Unknown series or origin");
  if (response.status === 400) throw new HttpError(400, "invalid_request", "Scenario rejected by the engine");
  if (!response.ok) {
    throw new HttpError(502, "engine_unavailable",
                        "The simulation engine is unavailable; precomputed Phase 5 results remain available");
  }
  return (await response.json()) as EngineResult;
}

export async function engineHealth(): Promise<{ reachable: boolean; engineVersion?: string }> {
  try {
    const response = await fetch(new URL("/health", serverEnv().engineUrl),
                                 { signal: AbortSignal.timeout(3_000), cache: "no-store" });
    if (!response.ok) return { reachable: false };
    const body = (await response.json()) as { engineVersion?: string; keyConfigured?: boolean };
    return { reachable: Boolean(body.keyConfigured), engineVersion: body.engineVersion };
  } catch {
    return { reachable: false };
  }
}
