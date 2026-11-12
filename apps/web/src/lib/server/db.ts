import "server-only";
import postgres from "postgres";
import { ConfigurationError, serverEnv } from "./env";

type Sql = ReturnType<typeof postgres>;
export type ReadSql = postgres.TransactionSql;
const globalForDb = globalThis as unknown as { __webappSql?: Sql };

const TLS_MODES = new Set(["require", "verify-ca", "verify-full"]);
const TLS_VERSIONS = new Set(["TLSv1.2", "TLSv1.3"]);

/**
 * postgres.js forwards every URL query parameter it does not recognise to the server as a startup parameter.
 * `ssl_min_protocol_version` is a libpq client option (and a server SIGHUP setting), so passing it through makes
 * PostgreSQL reject the connection (55P02). TLS options are therefore read here and applied as Node TLS options;
 * the remaining parameters pass through unchanged. Remote hosts always use TLS 1.2 or newer.
 */
export function connectionOptions(databaseUrl: string): { url: string; ssl: false | { rejectUnauthorized: boolean; minVersion: "TLSv1.2" | "TLSv1.3" } } {
  let url: URL;
  try {
    url = new URL(databaseUrl);
  } catch {
    throw new ConfigurationError("WEBAPP_DATABASE_URL");
  }
  const local = url.hostname === "127.0.0.1" || url.hostname === "localhost";
  const mode = url.searchParams.get("sslmode");
  const minimum = url.searchParams.get("ssl_min_protocol_version") ?? "TLSv1.2";
  url.searchParams.delete("sslmode");
  url.searchParams.delete("ssl_min_protocol_version");
  if (local) return { url: url.toString(), ssl: false };
  if ((mode !== null && !TLS_MODES.has(mode)) || !TLS_VERSIONS.has(minimum)) {
    throw new ConfigurationError("WEBAPP_DATABASE_URL");
  }
  // `require` semantics (encrypted, certificate not pinned), matching the engine's sslmode=require; verify-* verify.
  return {
    url: url.toString(),
    ssl: { rejectUnauthorized: mode === "verify-ca" || mode === "verify-full", minVersion: minimum as "TLSv1.2" | "TLSv1.3" },
  };
}

/**
 * One small pool per serverless instance. `prepare: false` keeps the client compatible with Supabase's
 * transaction pooler; queries are always parameterised through tagged templates (no string-built SQL).
 */
export function sql(): Sql {
  if (!globalForDb.__webappSql) {
    const { url, ssl } = connectionOptions(serverEnv().databaseUrl);
    globalForDb.__webappSql = postgres(url, {
      max: 3,
      prepare: false,
      idle_timeout: 20,
      connect_timeout: 5,
      ssl,
      onnotice: () => {},
      transform: { ...postgres.camel, undefined: null },
    });
  }
  return globalForDb.__webappSql;
}

/**
 * Lossless float reads. postgres.js always requests TEXT results (no binary result format), and Supabase's server
 * configuration sets extra_float_digits = 0, which rounds every double precision value to 15 significant digits.
 * Each read therefore runs in a READ ONLY transaction that first sets extra_float_digits = 3 with
 * set_config(..., is_local => true): PostgreSQL >= 12 then emits the shortest exact round-trip text for every
 * float8, which JavaScript parses back to the identical IEEE-754 double. The setting is transaction-scoped, so it
 * never leaks into pooled sessions, and it needs no role- or database-wide change.
 */
export async function readExact<T>(run: (q: ReadSql) => Promise<T>): Promise<T> {
  return sql().begin("read only", async (q) => {
    await q`select set_config('extra_float_digits', '3', true)`;
    return run(q);
  }) as Promise<T>;
}

export async function closeDb(): Promise<void> {
  if (globalForDb.__webappSql) {
    await globalForDb.__webappSql.end({ timeout: 5 });
    globalForDb.__webappSql = undefined;
  }
}
