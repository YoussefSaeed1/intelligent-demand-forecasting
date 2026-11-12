// Local Postgres 17.11 (same major/minor as the Supabase project) for development and tests only.
// Listens on 127.0.0.1:54329; data in apps/web/.local-postgres (git-ignored). Stops on Ctrl+C or SIGTERM.
// Credentials here are local-only and never used for Supabase.
import EmbeddedPostgres from "embedded-postgres";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const databaseDir = join(root, ".local-postgres", "data");
export const LOCAL = { host: "127.0.0.1", port: 54329, user: "postgres", password: "local-owner-only" };

const pg = new EmbeddedPostgres({
  databaseDir, user: LOCAL.user, password: LOCAL.password, port: LOCAL.port, persistent: true,
  postgresFlags: ["-c", "listen_addresses=127.0.0.1"],
});

if (!existsSync(join(databaseDir, "PG_VERSION"))) await pg.initialise();
await pg.start();
console.log(`READY postgresql://${LOCAL.user}@${LOCAL.host}:${LOCAL.port}/postgres`);

const stop = async () => { await pg.stop(); console.log("STOPPED"); process.exit(0); };
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
setInterval(() => {}, 1 << 30); // stay alive until a signal arrives
