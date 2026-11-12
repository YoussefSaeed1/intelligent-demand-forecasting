import { handle, json, NCU_NOTICE } from "@/lib/server/http";
import { exportVersion, inventoryStudy, policies, type StudyRow } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";
import { studyQuerySchema } from "@/lib/schemas";

type Row = StudyRow;
const ratio = (a: number, b: number) => (b > 0 ? a / b : null);

function measures(r: { seriesEpisodes: number; totalCost: number; holdingCost: number; shortageCost: number;
                       orderingCost: number; terminalCost: number; demandUnits: number; fulfilledUnits: number;
                       stockoutDays: number; orders: number; averageOnHandSum: number }) {
  return {
    seriesEpisodes: r.seriesEpisodes,
    meanCostNcu: ratio(r.totalCost, r.seriesEpisodes),
    holdingCostNcu: ratio(r.holdingCost, r.seriesEpisodes),
    unmetPenaltyNcu: ratio(r.shortageCost, r.seriesEpisodes),
    orderingCostNcu: ratio(r.orderingCost, r.seriesEpisodes),
    terminalCostNcu: ratio(r.terminalCost, r.seriesEpisodes),
    fillRate: ratio(r.fulfilledUnits, r.demandUnits),
    stockoutDaysPerEpisode: ratio(r.stockoutDays, r.seriesEpisodes),
    averageOnHand: ratio(r.averageOnHandSum, r.seriesEpisodes),
    ordersPerEpisode: ratio(r.orders, r.seriesEpisodes),
    costPerDemandedUnitNcu: ratio(r.totalCost, r.demandUnits),
  };
}

/** The frozen 544-case Phase 5 study (full populations), per origin and pooled over origins. */
export async function GET(request: Request) {
  return handle(request, async (id) => {
    const q = await readRequest(request, studyQuerySchema);
    const rows = (await inventoryStudy(q.dataset, q.scenario, q.origin, q.policy, q.pattern)) as Row[];
    const pooled = new Map<string, Row & { origins: number }>();
    for (const r of rows) {
      const key = `${r.scenarioKey}|${r.policyKey}`;
      const current = pooled.get(key);
      if (!current) {
        pooled.set(key, { ...r, origins: 1 });
        continue;
      }
      for (const field of ["seriesEpisodes", "totalCost", "holdingCost", "shortageCost", "orderingCost",
                           "terminalCost", "demandUnits", "fulfilledUnits", "stockoutDays", "orders",
                           "averageOnHandSum"] as const) {
        (current[field] as number) += r[field] as number;
      }
      current.origins += 1;
    }
    return json({
      meta: { exportVersion: await exportVersion(), evidence: "validation", scope: "full research population",
              ncuNotice: NCU_NOTICE,
              scenarioNote: "The 17 scenarios reuse the same four validation origins and forecasts; they are not independent replications." },
      policies: await policies(),
      perOrigin: rows.map((r) => ({ originKey: r.originKey, fold: r.fold, scenarioKey: r.scenarioKey,
                                    scenario: r.scenario, scenarioGroup: r.scenarioGroup, policyKey: r.policyKey,
                                    policy: r.policy, ...measures(r) })),
      pooled: [...pooled.values()].map((r) => ({ scenarioKey: r.scenarioKey, scenario: r.scenario,
                                                 scenarioGroup: r.scenarioGroup, policyKey: r.policyKey,
                                                 policy: r.policy, origins: r.origins, ...measures(r) })),
    }, { id, cache: "immutable" });
  });
}
