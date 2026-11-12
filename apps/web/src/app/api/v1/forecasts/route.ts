import { handle, HttpError, json } from "@/lib/server/http";
import { seriesMetrics } from "@/lib/metrics";
import { exportVersion, forecastBundle, seriesDetail } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";
import { forecastQuerySchema } from "@/lib/schemas";

export async function GET(request: Request) {
  return handle(request, async (id) => {
    const q = await readRequest(request, forecastQuerySchema);
    const series = await seriesDetail(q.series);
    if (!series) throw new HttpError(404, "not_found", "Unknown series");
    const bundle = await forecastBundle(q.series, q.origin);
    if (!bundle.origin || bundle.actuals.length !== 28) throw new HttpError(404, "not_found", "Unknown origin");
    const models = bundle.metrics.map((m) => ({
      modelKey: m.modelKey, role: m.modelRoleKey, label: m.modelRole,
      forecast: bundle.forecasts.filter((f) => f.modelKey === m.modelKey)
        .map((f) => ({ date: f.date, horizonDay: f.horizonDay, value: f.forecast })),
      metrics: seriesMetrics({ observations: m.observations, sumAbsError: m.sumAbsError,
                               sumSquaredError: m.sumSquaredError, sumError: m.sumError, sumActual: m.sumActual,
                               scaleAbs: m.scaleAbs, scaleSquared: m.scaleSquared }),
    }));
    return json({
      meta: { exportVersion: await exportVersion(), evidence: "validation",
              note: "Saved fixed-origin 28-day forecasts from a validation origin; not daily refreshed and not the final holdout." },
      series: { seriesKey: series.seriesKey, seriesId: series.seriesId, pattern: series.demandPattern,
                datasetKey: series.datasetKey },
      origin: bundle.origin,
      history: bundle.history,
      actuals: bundle.actuals,
      models,
    }, { id, cache: "immutable" });
  });
}
