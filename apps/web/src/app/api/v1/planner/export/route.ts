import { handle } from "@/lib/server/http";
import { parseSimulateBody, simulate, toCsv } from "@/lib/server/planner";
import { simulateLimits } from "@/lib/server/routes";

/** CSV of one bounded planner run (at most 4 policies x 28 days); nothing is stored server-side. */
export async function POST(request: Request) {
  return handle(request, async (id) => {
    await simulateLimits(request);
    const body = await parseSimulateBody(request);
    const csv = toCsv(await simulate(body, id));
    const name = `planner_${body.seriesKey}_${body.originKey}`.replace(/[^A-Za-z0-9_-]/g, "_");
    return new Response(csv, {
      headers: { "content-type": "text/csv; charset=utf-8", "content-disposition": `attachment; filename="${name}.csv"`,
                 "cache-control": "no-store", "x-request-id": id, "x-content-type-options": "nosniff" },
    });
  });
}
