import "server-only";
import type { z } from "zod";
import { params } from "../schemas";
import { serverEnv } from "./env";
import { HttpError, query, rateLimit, zodFields } from "./http";

/** Shared read-endpoint prelude: rate limit, then strict query validation. */
export async function readRequest<T extends z.ZodType>(request: Request, schema: T): Promise<z.infer<T>> {
  await rateLimit(request, "read", serverEnv().readPerMinute, 60);
  const parsed = schema.safeParse(params(query(request)));
  if (!parsed.success) throw new HttpError(400, "invalid_request", "Invalid query", zodFields(parsed.error));
  return parsed.data;
}

export async function simulateLimits(request: Request) {
  const env = serverEnv();
  await rateLimit(request, "simulate", env.simulatePerMinute, 60);
  await rateLimit(request, "simulate-day", env.simulatePerDay, 86_400);
}
