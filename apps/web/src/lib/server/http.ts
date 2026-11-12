import "server-only";
import { createHash, randomUUID } from "node:crypto";
import type { ZodError } from "zod";
import { sql } from "./db";
import { ConfigurationError, serverEnv } from "./env";

export const NCU_NOTICE = "Hypothetical normalised cost units (NCU); simulated differences are not realised savings.";
const IMMUTABLE = "public, max-age=300, s-maxage=86400, stale-while-revalidate=604800";

export class HttpError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string,
              public readonly fields?: { field: string; message: string }[]) {
    super(message);
  }
}

export function requestId(request: Request): string {
  const supplied = request.headers.get("x-request-id") ?? "";
  return /^[A-Za-z0-9-]{8,64}$/.test(supplied) ? supplied : randomUUID();
}

/** Salted SHA-256 of the client address: raw IPs are never stored. */
export function clientBucket(request: Request, scope: string): string {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const address = forwarded || request.headers.get("x-real-ip") || "local";
  return createHash("sha256").update(`${serverEnv().rateLimitSalt}|${scope}|${address}`).digest("hex");
}

export async function rateLimit(request: Request, scope: string, limit: number, windowSeconds: number) {
  const bucket = clientBucket(request, `${scope}:${windowSeconds}`);
  const [row] = await sql()`select ops.rate_limit_hit(${bucket}, ${limit}, ${windowSeconds}) as allowed`;
  if (!row?.allowed) {
    throw new HttpError(429, "rate_limited", "Too many requests; please retry later");
  }
}

export function json(body: unknown, init: { status?: number; cache?: "immutable" | "none"; id: string }) {
  return Response.json(body, {
    status: init.status ?? 200,
    headers: {
      "cache-control": init.cache === "immutable" ? IMMUTABLE : "no-store",
      "x-request-id": init.id,
      "x-content-type-options": "nosniff",
    },
  });
}

export function zodFields(error: ZodError) {
  return error.issues.map((issue) => ({ field: issue.path.join("."), message: issue.message }));
}

/** Every handler runs inside this wrapper: generic errors, request id, no internals in responses. */
export async function handle(request: Request, run: (id: string) => Promise<Response>): Promise<Response> {
  const id = requestId(request);
  try {
    return await run(id);
  } catch (error) {
    if (error instanceof HttpError) {
      const headers: Record<string, string> = { "cache-control": "no-store", "x-request-id": id };
      if (error.status === 429) headers["retry-after"] = "60";
      return Response.json({ error: error.code, message: error.message, fields: error.fields, requestId: id },
                           { status: error.status, headers });
    }
    const configuration = error instanceof ConfigurationError;
    console.error(JSON.stringify({ requestId: id, path: new URL(request.url).pathname,
                                   error: configuration ? "configuration" : "unhandled",
                                   detail: error instanceof Error ? error.message : String(error) }));
    return Response.json({ error: configuration ? "not_configured" : "internal_error",
                           message: "The request could not be completed", requestId: id },
                         { status: configuration ? 503 : 500, headers: { "cache-control": "no-store", "x-request-id": id } });
  }
}

export function query(request: Request): URLSearchParams {
  return new URL(request.url).searchParams;
}
