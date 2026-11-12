import "server-only";

/**
 * Server-only configuration. None of these names carries the NEXT_PUBLIC_ prefix, so Next.js never
 * inlines them into client bundles. Values are read lazily so `next build` needs no secrets.
 */
export interface ServerEnv {
  databaseUrl: string; // webapp_api role (read-only + rate-limit function), never the service-role key
  engineUrl: string;
  engineKey: string;
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

export function serverEnv(): ServerEnv {
  return {
    databaseUrl: required("WEBAPP_DATABASE_URL"),
    engineUrl: required("ENGINE_URL"),
    engineKey: required("ENGINE_SHARED_KEY", 32),
    rateLimitSalt: required("RATE_LIMIT_SALT", 32),
    simulatePerMinute: positiveInteger("RATE_LIMIT_SIMULATE_PER_MINUTE", 30),
    simulatePerDay: positiveInteger("RATE_LIMIT_SIMULATE_PER_DAY", 300),
    readPerMinute: positiveInteger("RATE_LIMIT_READ_PER_MINUTE", 120),
  };
}
