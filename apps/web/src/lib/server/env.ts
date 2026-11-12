import "server-only";

/**
 * Server-only configuration. None of these names carries the NEXT_PUBLIC_ prefix, so Next.js never
 * inlines them into client bundles. Values are read lazily so `next build` needs no secrets.
 */
export interface ServerEnv {
  databaseUrl: string; // webapp_api role (read-only + rate-limit function), never the service-role key
  engineUrl: string;
  engineKey: string;
  /** Vercel "Protection Bypass for Automation" secret for the protected engine deployment; null only for a loopback engine. */
  engineBypassSecret: string | null;
  rateLimitSalt: string;
  simulatePerMinute: number;
  simulatePerDay: number;
  readPerMinute: number;
}

function required(name: string, minimumLength = 1): string {
  const value = process.env[name];
  if (!value || value.length < minimumLength) {
    throw new ConfigurationError(name);
  }
  return value;
}

function positiveInteger(name: string, fallback: number): number {
  const raw = process.env[name];
  const value = raw === undefined ? fallback : Number(raw);
  return Number.isInteger(value) && value > 0 ? value : fallback;
}

export class ConfigurationError extends Error {
  constructor(public readonly variable: string) {
    super(`Missing or invalid server configuration: ${variable}`);
  }
}

const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]"]);

/**
 * A remote engine must be HTTPS (both secrets travel in headers) and must have the Vercel protection bypass secret,
 * because the engine deployment is protected for All Deployments. Only a loopback engine (local tests) may omit it.
 */
function engineTarget(): { engineUrl: string; engineBypassSecret: string | null } {
  const engineUrl = required("ENGINE_URL");
  let url: URL;
  try {
    url = new URL(engineUrl);
  } catch {
    throw new ConfigurationError("ENGINE_URL");
  }
  const loopback = LOOPBACK.has(url.hostname);
  if (url.username || url.password || url.search || url.hash || !(url.protocol === "https:" || (loopback && url.protocol === "http:"))) {
    throw new ConfigurationError("ENGINE_URL");
  }
  const bypass = process.env.VERCEL_PROTECTION_BYPASS_SECRET ?? "";
  if (!loopback && bypass.length < 16) throw new ConfigurationError("VERCEL_PROTECTION_BYPASS_SECRET");
  return { engineUrl, engineBypassSecret: bypass.length > 0 ? bypass : null };
}

export function serverEnv(): ServerEnv {
  return {
    databaseUrl: required("WEBAPP_DATABASE_URL"),
    ...engineTarget(),
    engineKey: required("ENGINE_SHARED_KEY", 32),
    rateLimitSalt: required("RATE_LIMIT_SALT", 32),
    simulatePerMinute: positiveInteger("RATE_LIMIT_SIMULATE_PER_MINUTE", 30),
    simulatePerDay: positiveInteger("RATE_LIMIT_SIMULATE_PER_DAY", 300),
    readPerMinute: positiveInteger("RATE_LIMIT_READ_PER_MINUTE", 120),
  };
}
