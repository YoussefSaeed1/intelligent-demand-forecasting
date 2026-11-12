/**
 * Phase 7D-3A lossless float transport for the web API (no tolerance anywhere in this file).
 *
 * Supabase's server configuration sets extra_float_digits = 0, so TEXT results (postgres.js has no binary result
 * format) round double precision to 15 significant digits. The local reference database uses the default (1). These
 * tests reproduce Supabase's setting by starting the session with extra_float_digits=0 and require:
 *   - the defect is reproduced on a raw lossy session;
 *   - every double precision value in schema app, read through `readExact` on that lossy session, has the identical
 *     IEEE-754 bits as float8send (binary, independent of any text setting);
 *   - every /api/v1 response is byte-identical between the exact and the lossy session;
 *   - API values equal the hash-verified export CSVs (the seed source) and metrics recomputed from them, bit for bit.
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import postgres from "postgres";
import { afterAll, describe, expect, it } from "vitest";
import { aggregateMetrics } from "@/lib/metrics";
import { closeDb, connectionOptions, readExact } from "@/lib/server/db";
import { LOCAL_SECRETS } from "./setup";
import * as datasets from "@/app/api/v1/datasets/route";
import * as forecasts from "@/app/api/v1/forecasts/route";
import * as aggregate from "@/app/api/v1/metrics/aggregate/route";
import * as research from "@/app/api/v1/research/route";
import * as seriesBase from "@/app/api/v1/inventory/series-base/route";
import * as seriesDetail from "@/app/api/v1/series/[seriesKey]/route";
import * as seriesList from "@/app/api/v1/series/route";
import * as simulate from "@/app/api/v1/planner/simulate/route";
import * as study from "@/app/api/v1/inventory/study/route";

const REPO = join(__dirname, "..", "..", "..");
const EXACT_URL = LOCAL_SECRETS.WEBAPP_DATABASE_URL;
const LOSSY_URL = `${EXACT_URL}?extra_float_digits=0`; // forwarded by postgres.js as a startup parameter
const BASE = { seriesKey: "store_item|1:11", originKey: "store_item|1" };
const M5 = { seriesKey: "m5|4:CA_1FOODS_3_764", originKey: "m5|3" };
let ipCounter = 0;

const bits = (x: number) => {
  const view = new DataView(new ArrayBuffer(8));
  view.setFloat64(0, x);
  return view.getBigUint64(0).toString(16);
};

afterAll(async () => {
  process.env.WEBAPP_DATABASE_URL = EXACT_URL;
  await closeDb();
});

async function usingDatabase<T>(url: string, run: () => Promise<T>): Promise<T> {
  await closeDb();
  process.env.WEBAPP_DATABASE_URL = url;
  try {
    return await run();
  } finally {
    await closeDb();
    process.env.WEBAPP_DATABASE_URL = EXACT_URL;
  }
}

/** Raw responses: the same request id for both sessions so bodies are comparable byte for byte. */
async function call(handler: (r: Request, c?: never) => Promise<Response>, path: string, body?: unknown, context?: unknown) {
  const headers = { "x-forwarded-for": `10.77.${Math.floor(++ipCounter / 250)}.${ipCounter % 250}`,
                    "x-request-id": "precision-check-0001", "content-type": "application/json" };
  const request = new Request(`http://localhost${path}`, body === undefined ? { headers }
    : { method: "POST", headers, body: JSON.stringify(body) });
  const response = await (handler as (r: Request, c?: unknown) => Promise<Response>)(request, context);
  return { status: response.status, text: await response.text() };
}

type Endpoint = readonly [string, () => Promise<{ status: number; text: string }>];
const ENDPOINTS: Endpoint[] = [
  ["datasets", () => call(datasets.GET, "/api/v1/datasets")],
  ["series list", () => call(seriesList.GET, "/api/v1/series?dataset=m5&limit=50")],
  ["series detail", () => call(seriesDetail.GET as never, "/x", undefined,
                               { params: Promise.resolve({ seriesKey: encodeURIComponent(M5.seriesKey) }) })],
  ...[BASE, M5].map((s) => [`forecasts ${s.seriesKey}`, () => call(forecasts.GET,
    `/api/v1/forecasts?series=${encodeURIComponent(s.seriesKey)}&origin=${encodeURIComponent(s.originKey)}`)] as const),
  ...["store_item", "m5"].flatMap((d) => [
    [`aggregate ${d}`, () => call(aggregate.GET, `/api/v1/metrics/aggregate?dataset=${d}`)] as const,
    [`aggregate ${d} lumpy`, () => call(aggregate.GET, `/api/v1/metrics/aggregate?dataset=${d}&pattern=lumpy`)] as const,
    [`study ${d}`, () => call(study.GET, `/api/v1/inventory/study?dataset=${d}`)] as const,
    [`study ${d} smooth`, () => call(study.GET, `/api/v1/inventory/study?dataset=${d}&scenario=base&pattern=smooth`)] as const,
  ]),
  ...[BASE, M5].map((s) => [`series-base ${s.seriesKey}`, () => call(seriesBase.GET,
    `/api/v1/inventory/series-base?series=${encodeURIComponent(s.seriesKey)}`)] as const),
  ["research", () => call(research.GET, "/api/v1/research")],
  ["simulate base (studyReference)", () => call(simulate.POST, "/api/v1/planner/simulate", BASE)],
];

/** Hash-verified export CSV (the exact seed source of the database; written with shortest round-trip floats). */
function exportTable(name: string, filter: (line: string) => boolean = () => true): Record<string, string>[] {
  const manifest = JSON.parse(readFileSync(join(REPO, "reports/webapp/export_manifest.json"), "utf8"));
  const entry = manifest.tables[name];
  const raw = readFileSync(join(REPO, entry.file));
  expect(createHash("sha256").update(raw).digest("hex"), `${name} export hash`).toBe(entry.sha256);
  const [header, ...lines] = raw.toString("utf8").trim().split(/\r?\n/);
  expect(raw.includes(0x22), `${name} has no quoted fields`).toBe(false);
  const columns = header.split(",");
  return lines.filter(filter).map((line) => Object.fromEntries(line.split(",").map((v, i) => [columns[i], v])));
}

describe("database layer on a Supabase-like session (extra_float_digits = 0)", () => {
  it("reproduces the defect on a raw lossy session and fixes it inside readExact without leaking the setting", async () => {
    const raw = postgres(LOSSY_URL, { prepare: false, max: 1, onnotice: () => {} });
    try {
      const query = `select historical_mean56 as m from app.series_origin_mean56 where series_key = $1 and origin_key = $2`;
      expect((await raw`show extra_float_digits`)[0].extra_float_digits).toBe("0");
      const [lossy] = await raw.unsafe(query, [BASE.seriesKey, BASE.originKey]);
      expect(lossy.m).toBe(27.9285714285714); // 15 significant digits: the Supabase defect
      const exact = await raw.begin("read only", async (q) => {
        await q`select set_config('extra_float_digits', '3', true)`;
        return [(await q`show extra_float_digits`)[0].extra_float_digits, (await q.unsafe(query, [BASE.seriesKey, BASE.originKey]))[0].m];
      });
      expect(exact).toEqual(["3", 27.928571428571427]);
      expect((await raw`show extra_float_digits`)[0].extra_float_digits).toBe("0"); // transaction-scoped: no leak
    } finally {
      await raw.end();
    }
  });

  it("every double precision value in schema app is bit-identical to float8send through readExact", async () => {
    await usingDatabase(LOSSY_URL, async () => {
      const columns = await readExact((q) => q`
        select table_name, column_name from information_schema.columns
        where table_schema = 'app' and data_type = 'double precision' order by table_name, ordinal_position`);
      expect(columns.length).toBe(68);
      const raw = postgres(LOSSY_URL, { prepare: false, max: 1, onnotice: () => {} });
      let values = 0, lossyAltered = 0;
      try {
        for (const { tableName, columnName } of columns as unknown as { tableName: string; columnName: string }[]) {
          const table = `app.${tableName}`;
          const rows = await readExact((q) => q`
            select ${q(columnName)} as v, float8send(${q(columnName)}) as b from ${q(table)}
            where ${q(columnName)} is not null order by ctid`);
          const lossyRows = await raw`select ${raw(columnName)} as v from ${raw(table)}
                                      where ${raw(columnName)} is not null order by ctid`;
          expect(lossyRows.length).toBe(rows.length);
          for (let i = 0; i < rows.length; i += 1) {
            const stored = (rows[i].b as Buffer).readDoubleBE(0);
            if (bits(rows[i].v as number) !== bits(stored)) {
              throw new Error(`${table}.${columnName} row ${i}: ${rows[i].v} != ${stored}`);
            }
            if (bits(lossyRows[i].v as number) !== bits(stored)) lossyAltered += 1;
          }
          values += rows.length;
        }
      } finally {
        await raw.end();
      }
      expect(values).toBeGreaterThan(500_000);
      expect(lossyAltered).toBeGreaterThan(10_000); // the raw text transport really alters stored values
    });
  }, 300_000);
});

describe("API responses are byte-identical on exact and lossy sessions", () => {
  it.each(ENDPOINTS)("%s", async (_label, run) => {
    const exact = await usingDatabase(EXACT_URL, run);
    const lossy = await usingDatabase(LOSSY_URL, run);
    expect(exact.status).toBe(200);
    expect(lossy.status).toBe(200);
    expect(lossy.text).toBe(exact.text);
  });
});

describe("API values equal the hash-verified export and metrics recomputed from it (lossy session)", () => {
  it("forecasts, actuals and history for the base series equal the export bit for bit", async () => {
    const r = await usingDatabase(LOSSY_URL, () => call(forecasts.GET,
      `/api/v1/forecasts?series=${encodeURIComponent(BASE.seriesKey)}&origin=${encodeURIComponent(BASE.originKey)}`));
    const body = JSON.parse(r.text);
    const key = `${BASE.seriesKey},${BASE.originKey},`;
    const saved = exportTable("forecasts", (l) => l.startsWith(key));
    let compared = 0;
    for (const model of body.models) {
      for (const point of model.forecast) {
        const row = saved.find((s) => s.ModelKey === model.modelKey && Number(s.HorizonDay) === point.horizonDay);
        expect(bits(point.value), `${model.modelKey} h${point.horizonDay}`).toBe(bits(Number(row!.Forecast)));
        compared += 1;
      }
    }
    expect(compared).toBe(84);
    const actuals = exportTable("validation_actuals", (l) => l.startsWith(key));
    expect(body.actuals.map((a: { units: number }) => bits(a.units))).toEqual(actuals.map((a) => bits(Number(a.Units))));
    const history = exportTable("series_history", (l) => l.startsWith(key));
    expect(body.history.map((h: { units: number }) => bits(h.units))).toEqual(history.map((h) => bits(Number(h.Units))));
  });

  it("aggregate metrics equal aggregateMetrics() of the exported additive components for every row", async () => {
    const saved = exportTable("forecast_metrics_aggregate");
    let compared = 0;
    for (const dataset of ["store_item", "m5"]) {
      const body = JSON.parse((await usingDatabase(LOSSY_URL, () =>
        call(aggregate.GET, `/api/v1/metrics/aggregate?dataset=${dataset}`))).text);
      for (const row of body.rows) {
        const s = saved.find((x) => x.OriginKey === row.originKey && x.ModelKey === row.modelKey && x.PatternKey === "all")!;
        const expected = aggregateMetrics({
          observations: Number(s.Observations), sumAbsError: Number(s.SumAbsError), sumSquaredError: Number(s.SumSquaredError),
          sumError: Number(s.SumError), sumActual: Number(s.SumActual), series: Number(s.Series), maseSum: Number(s.MaseSum),
          maseCount: Number(s.MaseCount), rmsseSum: Number(s.RmsseSum), rmsseCount: Number(s.RmsseCount),
        });
        expect(JSON.stringify(row.metrics), `${row.originKey} ${row.modelKey}`).toBe(JSON.stringify(expected));
        compared += 1;
      }
    }
    expect(compared).toBe(24);
  });

  it("series-base rows and the planner's historicalMean56 / Phase 5 reference equal the export bit for bit", async () => {
    const savedBase = exportTable("inventory_series_base", (l) => l.startsWith(`${BASE.seriesKey},`));
    const r = JSON.parse((await usingDatabase(LOSSY_URL, () => call(seriesBase.GET,
      `/api/v1/inventory/series-base?series=${encodeURIComponent(BASE.seriesKey)}`))).text);
    expect(r.rows).toHaveLength(16);
    const fields = ["totalCost", "holdingCost", "shortageCost", "orderingCost", "terminalCost", "demandUnits",
                    "fulfilledUnits", "unmetUnits", "stockoutDays", "orders", "averageOnHand", "finalOnHand",
                    "finalPipeline", "initialOnHand"];
    for (const row of r.rows) {
      const s = savedBase.find((x) => x.OriginKey === row.originKey && x.PolicyKey === row.policyKey)!;
      for (const f of fields) {
        expect(bits(row[f]), `${row.originKey} ${row.policyKey} ${f}`).toBe(bits(Number(s[f[0].toUpperCase() + f.slice(1)])));
      }
    }
    const sim = JSON.parse((await usingDatabase(LOSSY_URL, () => call(simulate.POST, "/api/v1/planner/simulate", BASE))).text);
    const mean = exportTable("series_origin_mean56", (l) => l.startsWith(`${BASE.seriesKey},${BASE.originKey},`))[0];
    expect(bits(sim.inputs.historicalMean56)).toBe(bits(Number(mean.HistoricalMean56)));
    for (const [policy, total] of Object.entries(sim.studyReference.phase5TotalCostNcu)) {
      const s = savedBase.find((x) => x.OriginKey === BASE.originKey && x.PolicyKey === policy)!;
      expect(bits(total as number), policy).toBe(bits(Number(s.TotalCost)));
    }
  });
});

describe("database URL handling", () => {
  it("applies libpq TLS options as Node TLS options instead of forwarding them as startup parameters", () => {
    const remote = connectionOptions(
      "postgresql://webapp_api.ref:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require&ssl_min_protocol_version=TLSv1.2");
    expect(remote.url).not.toContain("ssl_min_protocol_version");
    expect(remote.url).not.toContain("sslmode");
    expect(remote.ssl).toEqual({ rejectUnauthorized: false, minVersion: "TLSv1.2" });
    // The startup parameters postgres.js will actually send (no connection is opened by constructing the client).
    const client = postgres(remote.url, { prepare: false, ssl: remote.ssl });
    expect(Object.keys(client.options.connection).sort()).toEqual(["application_name"]);
    expect(client.options.user).toBe("webapp_api.ref");
    expect([client.options.host, client.options.port, client.options.database])
      .toEqual([["aws-0-eu-central-1.pooler.supabase.com"], [6543], "postgres"]);
    expect(connectionOptions("postgresql://u:p@db.example.com:6543/postgres").ssl).toEqual(
      { rejectUnauthorized: false, minVersion: "TLSv1.2" }); // remote hosts always use TLS
    expect(connectionOptions(EXACT_URL).ssl).toBe(false);
    for (const bad of ["postgresql://u:p@db.example.com/postgres?sslmode=disable",
                       "postgresql://u:p@db.example.com/postgres?sslmode=prefer",
                       "postgresql://u:p@db.example.com/postgres?sslmode=require&ssl_min_protocol_version=TLSv1",
                       "not a url"]) {
      expect(() => connectionOptions(bad), bad).toThrow(/WEBAPP_DATABASE_URL/);
    }
  });

  it("a URL carrying ssl_min_protocol_version connects (the raw driver would be rejected with 55P02)", async () => {
    const url = `${EXACT_URL}?sslmode=require&ssl_min_protocol_version=TLSv1.2`;
    const raw = postgres(url.replace("sslmode=require&", ""), { prepare: false, max: 1, onnotice: () => {} });
    await expect(raw`select 1`).rejects.toMatchObject({ code: "55P02" });
    await raw.end();
    const version = await usingDatabase(url, () => readExact((q) => q`select current_setting('extra_float_digits') as v`));
    expect(version[0].v).toBe("3");
  });
});
