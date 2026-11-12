import "server-only";
import postgres from "postgres";
import { serverEnv } from "./env";

type Sql = ReturnType<typeof postgres>;
const globalForDb = globalThis as unknown as { __webappSql?: Sql };

/**
 * One small pool per serverless instance. `prepare: false` keeps the client compatible with Supabase's
 * transaction pooler; queries are always parameterised through tagged templates (no string-built SQL).
 */
export function sql(): Sql {
  if (!globalForDb.__webappSql) {
    const url = serverEnv().databaseUrl;
    const local = /@(127\.0\.0\.1|localhost)[:/]/.test(url);
    globalForDb.__webappSql = postgres(url, {
      max: 3,
      prepare: false,
      idle_timeout: 20,
      connect_timeout: 5,
      ssl: local ? false : "require",
      onnotice: () => {},
      transform: { ...postgres.camel, undefined: null },
    });
  }
  return globalForDb.__webappSql;
}

export async function closeDb(): Promise<void> {
  if (globalForDb.__webappSql) {
    await globalForDb.__webappSql.end({ timeout: 5 });
    globalForDb.__webappSql = undefined;
  }
}
