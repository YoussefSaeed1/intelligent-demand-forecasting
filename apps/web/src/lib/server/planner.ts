import "server-only";
import { simulateSchema, type SimulateBody } from "../schemas";
import { runEngine } from "./engine";
import { HttpError, NCU_NOTICE, zodFields } from "./http";
import { exportVersion, scenarios, seriesBase, seriesDetail } from "./repository";

const SCENARIO_COLUMNS = {
  leadDays: "leadDays", reviewDays: "reviewDays", bufferDays: "bufferDays", initialCoverDays: "initialCoverDays",
  holdingCost: "holdingCost", shortageCost: "shortageCost", fixedOrderCost: "fixedOrderCost",
  variableOrderCost: "variableOrderCost", terminalCost: "terminalCost", variabilityMultiplier: "variabilityMultiplier",
} as const;

const camel = (key: string) => key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());

export async function parseSimulateBody(request: Request): Promise<SimulateBody> {
  const text = await request.text();
  if (text.length > 8 * 1024) throw new HttpError(413, "payload_too_large", "Request body too large");
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new HttpError(400, "invalid_request", "Body must be JSON");
  }
  const parsed = simulateSchema.safeParse(raw);
  if (!parsed.success) throw new HttpError(400, "invalid_request", "Invalid simulation request", zodFields(parsed.error));
  return parsed.data;
}

/** Runs one bounded simulation and attaches comparison context; never returns engine internals. */
export async function simulate(body: SimulateBody, id: string) {
  const series = await seriesDetail(body.seriesKey);
  if (!series) throw new HttpError(404, "not_found", "Unknown series");
  const result = await runEngine(body, id);
  const policies = result.policies.map((p) => ({
    policyKey: p.policy,
    summary: Object.fromEntries(Object.entries(p.summary).map(([k, v]) => [camel(k), v])),
    daily: p.daily.map((d) => Object.fromEntries(Object.entries(d).map(([k, v]) => [camel(k), v]))),
  }));
  const baseline = policies.find((p) => p.policyKey === "moving_average_28");
  const comparison = baseline ? {
    baseline: "moving_average_28",
    deltas: policies.filter((p) => p !== baseline).map((p) => ({
      policyKey: p.policyKey,
      totalCostNcu: (p.summary.totalCost as number) - (baseline.summary.totalCost as number),
      fillRatePoints: p.summary.fillRate === null || baseline.summary.fillRate === null ? null
        : 100 * ((p.summary.fillRate as number) - (baseline.summary.fillRate as number)),
    })),
  } : null;

  const frozen = (await scenarios()).find((s) =>
    (Object.keys(SCENARIO_COLUMNS) as (keyof typeof SCENARIO_COLUMNS)[]).every(
      (key) => Number(s[SCENARIO_COLUMNS[key]]) === body.scenario[key]));
  let studyReference = null;
  if (frozen) {
    const reference = frozen.scenarioKey === "base" ? await seriesBase(body.seriesKey, body.originKey) : [];
    studyReference = {
      scenarioMatched: frozen.scenarioKey,
      note: frozen.scenarioKey === "base"
        ? "Inputs equal the published base scenario; Phase 5 saved totals for this series are shown for comparison."
        : "Inputs equal a published Phase 5 scenario; per-series saved results are only published for the base scenario.",
      phase5TotalCostNcu: Object.fromEntries(reference.map((r) => [r.policyKey, r.totalCost])),
    };
  }
  return {
    meta: { exportVersion: await exportVersion(), engineVersion: result.engineVersion, evidence: "validation",
            ncuNotice: NCU_NOTICE, requestId: id },
    inputs: { seriesKey: body.seriesKey, originKey: body.originKey, policies: body.policies, scenario: body.scenario,
              historicalMean56: result.historicalMean56, dates: result.dates, demand: result.demand,
              demandSource: "saved validation-window sales (server-side; fixed-origin forecasts, not refreshed)" },
    policies,
    comparison,
    studyReference,
  };
}

export function toCsv(result: Awaited<ReturnType<typeof simulate>>): string {
  const columns = ["date", "demand", "openingStock", "receipts", "fulfilled", "unmet", "closingStock",
                   "pipelineAfter", "inventoryPosition", "orderQuantity", "holdingCost", "shortageCost", "orderingCost"];
  const header = ["policy", ...columns.map((c) => (c.endsWith("Cost") ? `${c}_ncu` : c))].join(",");
  const lines = result.policies.flatMap((p) =>
    p.daily.map((d) => [p.policyKey, ...columns.map((c) => String(d[c] ?? ""))].join(",")));
  return [`# ${NCU_NOTICE} Export ${result.meta.exportVersion}; engine ${result.meta.engineVersion}.`, header, ...lines]
    .join("\n") + "\n";
}
