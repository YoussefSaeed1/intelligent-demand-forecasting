import { aggregateMetrics } from "@/lib/metrics";
import { handle, json } from "@/lib/server/http";
import { aggregates, exportVersion } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";
import { aggregateQuerySchema } from "@/lib/schemas";

/** Full research population (not the curated subset): pooled and macro accuracy per origin and model. */
export async function GET(request: Request) {
  return handle(request, async (id) => {
    const q = await readRequest(request, aggregateQuerySchema);
    const rows = await aggregates(q.dataset, q.origin, q.pattern);
    return json({
      meta: { exportVersion: await exportVersion(), evidence: "validation", scope: "full research population" },
      rows: rows.map((r) => ({
        originKey: r.originKey, fold: r.fold, modelKey: r.modelKey, role: r.modelRoleKey, label: r.modelRole,
        pattern: r.patternKey,
        metrics: aggregateMetrics({ observations: r.observations, sumAbsError: r.sumAbsError,
                                    sumSquaredError: r.sumSquaredError, sumError: r.sumError, sumActual: r.sumActual,
                                    series: r.series, maseSum: r.maseSum, maseCount: r.maseCount,
                                    rmsseSum: r.rmsseSum, rmsseCount: r.rmsseCount }),
      })),
    }, { id, cache: "immutable" });
  });
}
