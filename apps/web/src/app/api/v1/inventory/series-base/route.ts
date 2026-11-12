import { handle, HttpError, json, NCU_NOTICE } from "@/lib/server/http";
import { exportVersion, seriesBase, seriesDetail } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";
import { seriesBaseQuerySchema } from "@/lib/schemas";

/** Saved Phase 5 base-scenario results for one curated series (also the planner's degraded-mode fallback). */
export async function GET(request: Request) {
  return handle(request, async (id) => {
    const q = await readRequest(request, seriesBaseQuerySchema);
    if (!(await seriesDetail(q.series))) throw new HttpError(404, "not_found", "Unknown series");
    return json({ meta: { exportVersion: await exportVersion(), evidence: "validation", scenario: "base",
                          ncuNotice: NCU_NOTICE },
                  rows: await seriesBase(q.series, q.origin) }, { id, cache: "immutable" });
  });
}
