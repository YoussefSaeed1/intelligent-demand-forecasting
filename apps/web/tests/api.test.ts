/**
 * Phase 7B application API gates (A-01..A-08) against the local Postgres and the local engine service.
 * References come from saved scientific evidence (registry metrics, post-audit reconciliation, Phase 5),
 * not from the API code.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import { closeDb } from "@/lib/server/db";
import { PLANNER_BOUNDS } from "@/lib/schemas";
import { LOCAL_SECRETS } from "./setup";
import * as datasets from "@/app/api/v1/datasets/route";
import * as exportCsv from "@/app/api/v1/planner/export/route";
import * as forecasts from "@/app/api/v1/forecasts/route";
import * as health from "@/app/api/v1/health/route";
import * as aggregate from "@/app/api/v1/metrics/aggregate/route";
import * as research from "@/app/api/v1/research/route";
import * as seriesBase from "@/app/api/v1/inventory/series-base/route";
import * as seriesDetail from "@/app/api/v1/series/[seriesKey]/route";
import * as seriesList from "@/app/api/v1/series/route";
import * as simulate from "@/app/api/v1/planner/simulate/route";
import * as study from "@/app/api/v1/inventory/study/route";

const REPO = join(__dirname, "..", "..", "..");
const BODIES: string[] = [];
let ipCounter = 0;
const ip = () => `10.0.${Math.floor(++ipCounter / 250)}.${ipCounter % 250}`;
const readJson = (path: string) => JSON.parse(readFileSync(join(REPO, path), "utf8"));
const close = (a: number, b: number, rtol = 1e-9) => Math.abs(a - b) <= rtol * Math.max(Math.abs(b), 1e-12);

async function get(handler: (r: Request) => Promise<Response>, path: string, address = ip()) {
  const response = await handler(new Request(`http://localhost${path}`, { headers: { "x-forwarded-for": address } }));
  const text = await response.text();
  BODIES.push(text);
  return { status: response.status, headers: response.headers, body: text.startsWith("{") ? JSON.parse(text) : text };
}

async function post(handler: (r: Request) => Promise<Response>, path: string, body: unknown, address = ip()) {
  const response = await handler(new Request(`http://localhost${path}`, {
    method: "POST", headers: { "content-type": "application/json", "x-forwarded-for": address },
    body: typeof body === "string" ? body : JSON.stringify(body),
  }));
  const text = await response.text();
  BODIES.push(text);
  return { status: response.status, headers: response.headers, body: text.startsWith("{") ? JSON.parse(text) : text };
}

const BASE = { seriesKey: "store_item|1:11", originKey: "store_item|1" };

afterAll(async () => {
  // A-02 / security: no response anywhere leaked a secret, SQL, a stack trace or a local path.
  const all = BODIES.join("\n");
  for (const secret of Object.values(LOCAL_SECRETS).filter((s) => !s.startsWith("http"))) {
    expect(all.includes(secret)).toBe(false);
  }
  expect(all).not.toMatch(/local-webapp-only|local-engine-only|Traceback|at Object\.|select \*|C:\\Users/);
  await closeDb();
});

describe("A-01 schemas and bounds", () => {
  it("planner bounds equal configs/webapp.yaml", () => {
    const yaml = readFileSync(join(REPO, "configs/webapp.yaml"), "utf8");
    const declared = Object.fromEntries([...yaml.matchAll(/^\s{2}(\w+): \[([\d.]+), ([\d.]+)\]/gm)]
      .map((m) => [m[1].replace(/_([a-z])/g, (_, c: string) => c.toUpperCase()), [Number(m[2]), Number(m[3])]]));
    expect(declared).toEqual(PLANNER_BOUNDS);
  });
});

describe("read endpoints", () => {
  it("study pattern filtering preserves additive totals and rejects unsupported patterns", async () => {
    const all = await get(study.GET, "/api/v1/inventory/study?dataset=m5&scenario=base");
    expect(all.status).toBe(200);
    const parts = [];
    for (const pattern of ["smooth", "erratic", "intermittent", "lumpy", "all_zero", "insufficient_positive_history"]) {
      const r = await get(study.GET, `/api/v1/inventory/study?dataset=m5&scenario=base&pattern=${pattern}`);
      expect(r.status).toBe(200);
      parts.push(...r.body.perOrigin);
    }
    for (const row of all.body.perOrigin) {
      const rows = parts.filter((r) => r.originKey === row.originKey && r.policyKey === row.policyKey);
      expect(rows.reduce((n, r) => n + r.seriesEpisodes, 0)).toBe(row.seriesEpisodes);
      const cost = rows.reduce((n, r) => n + r.meanCostNcu * r.seriesEpisodes, 0);
      expect(close(cost, row.meanCostNcu * row.seriesEpisodes)).toBe(true);
    }
    expect((await get(study.GET, "/api/v1/inventory/study?dataset=m5&pattern=unknown")).status).toBe(400);
  });
  it("health reports export and engine versions", async () => {
    const r = await get(health.GET, "/api/v1/health");
    expect(r.status).toBe(200);
    expect(r.body.status).toBe("ok");
    expect(r.body.exportVersion).toBe(readJson("reports/webapp/export_manifest.json").export_version);
    expect(r.body.engine.engineVersion).toMatch(/^[0-9a-f]{16}$/);
  });

  it("datasets distinguish curated demo coverage from the research population", async () => {
    const r = await get(datasets.GET, "/api/v1/datasets");
    const m5 = r.body.datasets.find((d: { datasetKey: string }) => d.datasetKey === "m5");
    expect(r.body.datasets).toHaveLength(2);
    expect([m5.seriesCount, m5.curatedSeries]).toEqual([30490, 300]);
    expect(m5.coverageNote).toContain("300 curated demo series of 30490");
    expect(r.headers.get("cache-control")).toContain("s-maxage");
  });

  it("series list validates, caps and paginates", async () => {
    for (const bad of ["", "?dataset=x", "?dataset=m5&limit=51", "?dataset=m5&q=%25", "?dataset=m5&extra=1",
                       `?dataset=m5&q=${"a".repeat(33)}`]) {
      expect((await get(seriesList.GET, `/api/v1/series${bad}`)).status).toBe(400);
    }
    const seen = new Set<string>();
    let cursor: string | null = "";
    while (cursor !== null) {
      const page = await get(seriesList.GET, `/api/v1/series?dataset=m5&limit=50${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`);
      expect(page.status).toBe(200);
      page.body.items.forEach((s: { seriesKey: string }) => seen.add(s.seriesKey));
      expect(page.body.total).toBe(300);
      cursor = page.body.nextCursor;
    }
    expect(seen.size).toBe(300);
    const lumpy = await get(seriesList.GET, "/api/v1/series?dataset=m5&pattern=lumpy&limit=1");
    expect(lumpy.body.total).toBe(60);
  });

  it("series detail handles encoded, invalid and unknown keys", async () => {
    const ok = await seriesDetail.GET(new Request("http://localhost/x", { headers: { "x-forwarded-for": ip() } }),
                                      { params: Promise.resolve({ seriesKey: encodeURIComponent("m5|4:CA_1FOODS_1_001") }) });
    expect(ok.status).toBe(200);
    const body = await ok.json();
    expect(body.origins).toHaveLength(4);
    const unknown = await seriesDetail.GET(new Request("http://localhost/x", { headers: { "x-forwarded-for": ip() } }),
                                           { params: Promise.resolve({ seriesKey: "m5|nope" }) });
    expect(unknown.status).toBe(404);
    const invalid = await seriesDetail.GET(new Request("http://localhost/x", { headers: { "x-forwarded-for": ip() } }),
                                           { params: Promise.resolve({ seriesKey: "m5|a;drop" }) });
    expect(invalid.status).toBe(400);
  });

  it("forecasts: origin-bounded history, validation window, three models, consistent metrics", async () => {
    const r = await get(forecasts.GET, `/api/v1/forecasts?series=${encodeURIComponent(BASE.seriesKey)}&origin=${encodeURIComponent(BASE.originKey)}`);
    expect(r.status).toBe(200);
    const { history, actuals, models, origin, meta } = r.body;
    expect(meta.evidence).toBe("validation");
    expect(history).toHaveLength(84);
    expect(history.at(-1).date).toBe(origin.originDate);
    expect(actuals[0].date).toBe(origin.validationStart);
    expect(models.map((m: { role: string }) => m.role)).toEqual(["selected_ml", "moving_average_28", "seasonal_naive"]);
    for (const model of models) {
      const mae = model.forecast.reduce((s: number, f: { value: number }, i: number) =>
        s + Math.abs(f.value - actuals[i].units), 0) / 28;
      expect(close(model.metrics.mae, mae)).toBe(true);
    }
    expect(actuals.every((a: { date: string }) => a.date < "2017-12-04")).toBe(true);
    expect((await get(forecasts.GET, "/api/v1/forecasts?series=store_item%7C1%3A11&origin=m5%7C1")).status).toBe(400);
    expect((await get(forecasts.GET, "/api/v1/forecasts?series=store_item%7C9%3A99&origin=store_item%7C1")).status).toBe(404);
  });

  it("aggregate metrics reproduce the saved registry metrics for every run (full population)", async () => {
    const plan = readJson("artifacts/inventory/phase5/plan.json");
    let compared = 0;
    for (const dataset of ["store_item", "m5"]) {
      const r = await get(aggregate.GET, `/api/v1/metrics/aggregate?dataset=${dataset}`);
      expect(r.body.meta.scope).toBe("full research population");
      for (const cohort of plan.cohorts.filter((c: { dataset: string }) => c.dataset === dataset)) {
        for (const [role, source] of Object.entries(cohort.sources) as [string, { specification: { path: string } }][]) {
          const dir = join(REPO, source.specification.path, "..");
          const status = JSON.parse(readFileSync(join(dir, "status.json"), "utf8"));
          const saved = JSON.parse(readFileSync(join(dir, status.outputs.metrics.path.replace(/\\/g, "/")), "utf8")).all;
          const row = r.body.rows.find((x: { originKey: string; role: string }) =>
            x.originKey === `${dataset}|${cohort.fold.number}` && x.role === role);
          expect(close(row.metrics.mae, saved.pooled.mae)).toBe(true);
          expect(close(row.metrics.rmse, saved.pooled.rmse)).toBe(true);
          expect(close(row.metrics.wape * 100, saved.pooled.wape_percent)).toBe(true);
          expect(close(row.metrics.macroMase, saved.macro.mase)).toBe(true);
          compared += 1;
        }
      }
    }
    expect(compared).toBe(24);
  });

  it("inventory study reproduces the post-audit pooled base results and labels scenarios honestly", async () => {
    const reference = readJson("reports/inventory/post_audit_reconciliation.json").base_pooled;
    for (const dataset of ["store_item", "m5"]) {
      const r = await get(study.GET, `/api/v1/inventory/study?dataset=${dataset}&scenario=base`);
      expect(r.body.meta.scenarioNote).toContain("not independent replications");
      expect(r.body.meta.ncuNotice).toContain("not realised savings");
      for (const row of r.body.pooled) {
        expect(close(row.meanCostNcu, reference[dataset][row.policyKey].mean_cost)).toBe(true);
        expect(close(row.fillRate, reference[dataset][row.policyKey].pooled_fill_rate)).toBe(true);
      }
      expect(r.body.pooled).toHaveLength(4);
    }
    const rop = (await get(study.GET, "/api/v1/inventory/study?dataset=m5&scenario=base")).body.policies
      .find((p: { policyKey: string }) => p.policyKey === "fixed_reorder_point");
    expect(rop.isLowStockComparator).toBe("Yes");
  });

  it("series-base returns the saved Phase 5 base rows for a curated series", async () => {
    const r = await get(seriesBase.GET, `/api/v1/inventory/series-base?series=${encodeURIComponent(BASE.seriesKey)}`);
    expect(r.body.rows).toHaveLength(16);
  });

  it("research separates reported final-holdout rows from validation evidence", async () => {
    const r = await get(research.GET, "/api/v1/research");
    expect(r.body.finalHoldout.evidence).toBe("reported_final_holdout");
    expect(r.body.finalHoldout.rows).toHaveLength(8);
    expect(r.body.limitations).toHaveLength(8);
    expect(r.body.auditFindings).toHaveLength(12);
    expect(r.body.provenance.finalHoldoutTargetsRead).toBe(false);
  });
});

describe("planner (engine via the API)", () => {
  it("A-08: base scenario through the full stack equals the saved Phase 5 totals", async () => {
    const r = await post(simulate.POST, "/api/v1/planner/simulate", { ...BASE });
    expect(r.status).toBe(200);
    expect(r.body.meta.evidence).toBe("validation");
    expect(r.body.studyReference.scenarioMatched).toBe("base");
    for (const policy of r.body.policies) {
      expect(close(policy.summary.totalCost, r.body.studyReference.phase5TotalCostNcu[policy.policyKey])).toBe(true);
      expect(policy.daily).toHaveLength(28);
    }
    expect(r.body.comparison.baseline).toBe("moving_average_28");
    expect(r.headers.get("cache-control")).toBe("no-store");
  });

  it("custom hypothetical scenarios run and are not presented as published results", async () => {
    const r = await post(simulate.POST, "/api/v1/planner/simulate",
                         { ...BASE, policies: ["selected_ml", "fixed_reorder_point"], scenario: { leadDays: 3, shortageCost: 25 } });
    expect(r.status).toBe(200);
    expect(r.body.studyReference).toBeNull();
    expect(r.body.policies).toHaveLength(2);
  });

  it("A-02/A-03: invalid, oversized and cross-dataset requests are rejected without internals", async () => {
    const bad = [
      { ...BASE, scenario: { leadDays: 15 } }, { ...BASE, scenario: { leadDays: 1.5 } },
      { ...BASE, scenario: { holdingCost: 0 } }, { ...BASE, scenario: { variabilityMultiplier: 2 } },
      { ...BASE, scenario: { extra: 1 } }, { ...BASE, policies: [] }, { ...BASE, policies: ["selected_ml", "selected_ml"] },
      { ...BASE, policies: ["oracle"] }, { ...BASE, originKey: "m5|1" }, { ...BASE, demand: Array(28).fill(0) },
      { seriesKey: "store_item|1:11" }, "not json",
    ];
    for (const body of bad) {
      const r = await post(simulate.POST, "/api/v1/planner/simulate", body);
      expect(r.status, JSON.stringify(body)).toBe(400);
      expect(r.body.error).toBe("invalid_request");
    }
    const big = await post(simulate.POST, "/api/v1/planner/simulate", JSON.stringify({ ...BASE, pad: "x".repeat(9000) }));
    expect(big.status).toBe(413);
    const unknown = await post(simulate.POST, "/api/v1/planner/simulate", { ...BASE, seriesKey: "store_item|9:99" });
    expect(unknown.status).toBe(404);
  });

  it("A-07: simulate rate limit returns 429 with Retry-After", async () => {
    const address = "10.99.99.99";
    const statuses: number[] = [];
    for (let i = 0; i < 9; i += 1) statuses.push((await post(simulate.POST, "/api/v1/planner/simulate", BASE, address)).status);
    expect(statuses.slice(0, 8).every((s) => s === 200)).toBe(true);
    const limited = await post(simulate.POST, "/api/v1/planner/simulate", BASE, address);
    expect(limited.status).toBe(429);
    expect(limited.headers.get("retry-after")).toBe("60");
  });

  it("degraded mode: an unreachable engine yields 502 pointing at precomputed results", async () => {
    const original = process.env.ENGINE_URL;
    process.env.ENGINE_URL = "http://127.0.0.1:9";
    try {
      const r = await post(simulate.POST, "/api/v1/planner/simulate", BASE);
      expect(r.status).toBe(502);
      expect(r.body.message).toContain("precomputed Phase 5 results");
    } finally {
      process.env.ENGINE_URL = original;
    }
  });

  it("CSV export is bounded and labels costs as NCU", async () => {
    const r = await post(exportCsv.POST, "/api/v1/planner/export", BASE);
    expect(r.status).toBe(200);
    expect(r.headers.get("content-type")).toContain("text/csv");
    const lines = (r.body as string).trim().split("\n");
    expect(lines[0]).toContain("not realised savings");
    expect(lines[1]).toContain("holdingCost_ncu");
    expect(lines).toHaveLength(2 + 4 * 28);
  });
});

describe("wording", () => {
  it("no response calls simulated differences savings except to deny it", () => {
    for (const body of BODIES) {
      for (const match of body.matchAll(/[^."]*\bsavings?\b[^."]*/gi)) {
        expect(match[0], match[0]).toMatch(/\bnot\b|\bnever\b/i);
      }
    }
  });
});

it("evidence directories referenced by the tests exist", () => {
  expect(readdirSync(join(REPO, "artifacts/inventory/phase5/runs")).length).toBe(544);
});
