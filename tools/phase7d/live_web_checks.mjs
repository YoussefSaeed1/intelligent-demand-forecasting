// Phase 7D-4 production checks for the public idf-web deployment (no secrets needed: the web app is public).
//
//   node tools/phase7d/live_web_checks.mjs <production base URL> <local reference base URL>
//
// The local reference is `next start` of the same commit on the exact local reference database and the verified
// local engine. Every comparison is byte-for-byte on the response body with an identical request id (no tolerance).
// Writes reports/webapp/phase7d/live_web_checks.json (statuses, timings, hashes; no bodies, no secrets).
import { createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const [PROD, LOCAL] = process.argv.slice(2).map((u) => u?.replace(/\/$/, ""));
if (!PROD?.startsWith("https://") || !LOCAL?.startsWith("http://127.0.0.1")) {
  throw new Error("usage: node live_web_checks.mjs https://<prod> http://127.0.0.1:<port>");
}
const OUT = resolve(import.meta.dirname, "../../reports/webapp/phase7d/live_web_checks.json");
const RID = "phase7d4-parity-0001";
const BASE = { seriesKey: "store_item|1:11", originKey: "store_item|1" };
const M5 = { seriesKey: "m5|4:CA_1FOODS_3_764", originKey: "m5|3" };
const PHASE5 = { selected_ml: 2555, moving_average_28: 2772, seasonal_naive: 2900, fixed_reorder_point: 1309 };
const enc = encodeURIComponent;
const sha = (s) => createHash("sha256").update(s).digest("hex").slice(0, 16);
const gates = {};
const bodies = [];

async function call(base, path, { body, headers = {}, method } = {}) {
  const started = performance.now();
  const response = await fetch(base + path, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers: { "x-request-id": RID, accept: "application/json", ...(body === undefined ? {} : { "content-type": "application/json" }), ...headers },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
    redirect: "manual",
  });
  const text = await response.text();
  if (base === PROD) bodies.push(text, [...response.headers.entries()].map(([k, v]) => `${k}: ${v}`).join("\n"));
  return { status: response.status, headers: response.headers, text, ms: Math.round(performance.now() - started) };
}

// W-1 numeric parity: production == local reference, byte for byte.
const READS = [
  "/api/v1/datasets",
  "/api/v1/series?dataset=m5&limit=50",
  "/api/v1/series?dataset=store_item&limit=50",
  `/api/v1/series/${enc(enc(M5.seriesKey))}`,
  ...[BASE, M5].map((s) => `/api/v1/forecasts?series=${enc(s.seriesKey)}&origin=${enc(s.originKey)}`),
  ...["store_item", "m5"].flatMap((d) => [
    `/api/v1/metrics/aggregate?dataset=${d}`, `/api/v1/metrics/aggregate?dataset=${d}&pattern=lumpy`,
    `/api/v1/inventory/study?dataset=${d}`, `/api/v1/inventory/study?dataset=${d}&scenario=base&pattern=smooth`,
  ]),
  ...[BASE, M5].map((s) => `/api/v1/inventory/series-base?series=${enc(s.seriesKey)}`),
  "/api/v1/research",
];
const POSTS = [
  ["/api/v1/planner/simulate", BASE],
  ["/api/v1/planner/simulate", M5],
  ["/api/v1/planner/simulate", { ...BASE, policies: ["selected_ml", "fixed_reorder_point"], scenario: { leadDays: 3, shortageCost: 25 } }],
  ["/api/v1/planner/export", BASE],
];
const parity = {};
for (const path of READS) {
  const [p, l] = [await call(PROD, path), await call(LOCAL, path)];
  parity[`GET ${path}`] = { prod: p.status, local: l.status, identical: p.status === 200 && p.text === l.text, prodSha: sha(p.text), localSha: sha(l.text), ms: p.ms };
}
for (const [path, body] of POSTS) {
  const [p, l] = [await call(PROD, path, { body }), await call(LOCAL, path, { body })];
  parity[`POST ${path} ${JSON.stringify(body)}`] = { prod: p.status, local: l.status, identical: p.status === 200 && p.text === l.text, prodSha: sha(p.text), localSha: sha(l.text), ms: p.ms };
}
gates["W-1 byte-identical API vs local reference"] = { pass: Object.values(parity).every((r) => r.identical), compared: Object.keys(parity).length, results: parity };

// W-2 health, engine through bypass + key, and Phase 5 totals through the full production stack.
const health = JSON.parse((await call(PROD, "/api/v1/health")).text);
const sim = JSON.parse((await call(PROD, "/api/v1/planner/simulate", { body: BASE })).text);
const totals = Object.fromEntries(sim.policies.map((p) => [p.policyKey, p.summary.totalCost]));
gates["W-2 health and Phase 5 totals"] = {
  pass: health.status === "ok" && health.engine?.reachable === true && health.engine?.engineVersion === "cedc5a31533772fc"
    && JSON.stringify(totals) === JSON.stringify(PHASE5) && sim.studyReference?.scenarioMatched === "base"
    && Object.entries(PHASE5).every(([k, v]) => sim.studyReference.phase5TotalCostNcu[k] === v),
  health: { status: health.status, engine: health.engine, exportVersion: health.exportVersion, build: health.build },
  totals,
};

// W-3 validation and error handling.
const invalid = {
  lead_days_out_of_bounds: await call(PROD, "/api/v1/planner/simulate", { body: { ...BASE, scenario: { leadDays: 15 } } }),
  client_supplied_demand: await call(PROD, "/api/v1/planner/simulate", { body: { ...BASE, demand: Array(28).fill(0) } }),
  cross_dataset: await call(PROD, "/api/v1/planner/simulate", { body: { ...BASE, originKey: "m5|1" } }),
  not_json: await call(PROD, "/api/v1/planner/simulate", { body: "not json" }),
  oversized: await call(PROD, "/api/v1/planner/simulate", { body: JSON.stringify({ ...BASE, pad: "x".repeat(9000) }) }),
  unknown_series: await call(PROD, "/api/v1/planner/simulate", { body: { ...BASE, seriesKey: "store_item|9:99" } }),
  bad_query: await call(PROD, "/api/v1/series?dataset=x"),
  extra_query: await call(PROD, "/api/v1/series?dataset=m5&extra=1"),
  sql_like_key: await call(PROD, `/api/v1/series/${enc("m5|a;drop")}`),
};
const expected = { lead_days_out_of_bounds: 400, client_supplied_demand: 400, cross_dataset: 400, not_json: 400, oversized: 413,
                   unknown_series: 404, bad_query: 400, extra_query: 400, sql_like_key: 400 };
const observed = Object.fromEntries(Object.entries(invalid).map(([k, r]) => [k, r.status]));
gates["W-3 validation"] = { pass: JSON.stringify(observed) === JSON.stringify(expected), observed, expected };

// W-4 data scope: curated demo coverage only; final-holdout targets never exposed.
const ds = JSON.parse((await call(PROD, "/api/v1/datasets")).text);
const research = JSON.parse((await call(PROD, "/api/v1/research")).text);
const nonCurated = await call(PROD, `/api/v1/series/${enc(enc("m5|4:CA_1FOODS_1_002"))}`);
gates["W-4 data scope"] = {
  pass: ds.datasets.find((d) => d.datasetKey === "m5").curatedSeries === 300
    && research.provenance.finalHoldoutTargetsRead === false && research.finalHoldout.evidence === "reported_final_holdout"
    && [404, 400].includes(nonCurated.status),
  m5Curated: ds.datasets.find((d) => d.datasetKey === "m5").curatedSeries, finalHoldoutTargetsRead: research.provenance.finalHoldoutTargetsRead,
  nonCuratedSeriesStatus: nonCurated.status,
};

// S-1 security headers on a page and an API route; S-2 no methods beyond the contract.
const page = await call(PROD, "/planner", { headers: { accept: "text/html" } });
const want = ["content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy", "permissions-policy", "strict-transport-security"];
const api = await call(PROD, "/api/v1/datasets");
const methods = { delete_simulate: (await call(PROD, "/api/v1/planner/simulate", { method: "DELETE" })).status,
                  post_datasets: (await call(PROD, "/api/v1/datasets", { method: "POST", body: {} })).status };
gates["S-1 security headers"] = {
  pass: page.status === 200 && want.every((h) => page.headers.get(h)) && api.headers.get("x-content-type-options") === "nosniff"
    && page.headers.get("x-powered-by") === null,
  page: Object.fromEntries(want.map((h) => [h, page.headers.get(h)])),
};
gates["S-2 unsupported methods"] = { pass: Object.values(methods).every((s) => s === 405), observed: methods };

// S-3 secret exposure: responses, headers and every client asset.
const html = (await call(PROD, "/", { headers: { accept: "text/html" } })).text;
const assets = [...new Set([...html.matchAll(/\/_next\/static\/[^"'\s)]+\.(?:js|css)/g)].map((m) => m[0]))];
for (const asset of assets) bodies.push((await call(PROD, asset, { headers: { accept: "*/*" } })).text);
const leak = /x-engine-key|x-vercel-protection-bypass|VERCEL_PROTECTION_BYPASS_SECRET|ENGINE_SHARED_KEY|WEBAPP_DATABASE_URL|RATE_LIMIT_SALT|postgres(?:ql)?:\/\/|pooler\.supabase\.com|webapp_api\.|engine_api|idf-engine\.vercel\.app|Traceback|at Object\.|C:\\Users/i;
const hits = bodies.filter((b) => leak.test(b)).map((b) => b.match(leak)[0]);
gates["S-3 secret exposure"] = { pass: hits.length === 0 && assets.length > 0, scannedTexts: bodies.length, clientAssets: assets.length, hits };

// S-4 rate limit: simulate allows 30/min per client, the next is 429 with Retry-After.
const statuses = [];
let limited = null;
for (let i = 0; i < 35 && !limited; i += 1) {
  const r = await call(PROD, "/api/v1/planner/simulate", { body: { ...BASE, policies: ["fixed_reorder_point"] } });
  statuses.push(r.status);
  if (r.status === 429) limited = r;
}
gates["S-4 rate limit"] = {
  pass: limited !== null && limited.headers.get("retry-after") === "60" && JSON.parse(limited.text).error === "rate_limited"
    && statuses.slice(0, -1).every((s) => s === 200),
  allowedBefore429: statuses.length - 1, retryAfter: limited?.headers.get("retry-after") ?? null,
};

// P-1 latency (warm), per route type.
const lat = { read: [], simulate: [] };
for (let i = 0; i < 5; i += 1) lat.read.push((await call(PROD, "/api/v1/inventory/study?dataset=m5")).ms);
const median = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
gates["P-1 latency (client-side, warm)"] = { pass: true, readStudyMs: lat.read, readMedianMs: median(lat.read),
                                             firstParityCallMs: Object.values(parity)[0].ms,
                                             simulateParityMs: Object.entries(parity).filter(([k]) => k.includes("simulate")).map(([, v]) => v.ms) };

const overall = Object.values(gates).every((g) => g.pass) ? "PASS" : "FAIL";
await writeFile(OUT, JSON.stringify({ checkedUtc: new Date().toISOString(), production: PROD, overall, gates }, null, 2) + "\n");
for (const [name, g] of Object.entries(gates)) console.log(`${g.pass ? "PASS" : "FAIL"}  ${name}`);
console.log(`OVERALL ${overall} -> ${OUT}`);
