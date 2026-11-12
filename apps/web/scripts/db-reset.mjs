// Recreate the local test database "webapp": emulate Supabase's built-in roles, apply every migration in
// supabase/migrations in order, and give the login roles LOCAL-ONLY passwords. Never point this at Supabase.
import postgres from "postgres";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const owner = { host: "127.0.0.1", port: 54329, username: "postgres", password: "local-owner-only" };
export const LOCAL_ROLES = { webapp_api: "local-webapp-only", engine_api: "local-engine-only" };

if (owner.host !== "127.0.0.1") throw new Error("db-reset only targets the local test server");

const admin = postgres({ ...owner, database: "postgres", onnotice: () => {} });
await admin.unsafe("drop database if exists webapp with (force)");
await admin.unsafe("create database webapp");
for (const role of ["anon", "authenticated", "service_role"]) {
  await admin.unsafe(`do $$ begin if not exists (select 1 from pg_roles where rolname = '${role}') then create role ${role} nologin; end if; end $$`);
}
await admin.end();

const db = postgres({ ...owner, database: "webapp", onnotice: () => {} });
// Supabase grants anon/authenticated usage on public; mirror that so the tests prove app/ops stay closed anyway.
await db.unsafe("grant usage on schema public to anon, authenticated");
const migrations = readdirSync(join(root, "supabase", "migrations")).filter((f) => f.endsWith(".sql")).sort();
for (const file of migrations) {
  await db.unsafe(readFileSync(join(root, "supabase", "migrations", file), "utf8"));
  console.log(`applied ${file}`);
}
for (const [role, password] of Object.entries(LOCAL_ROLES)) {
  await db.unsafe(`alter role ${role} with password '${password}'`);
}
await db.end();
console.log("local database webapp ready");
