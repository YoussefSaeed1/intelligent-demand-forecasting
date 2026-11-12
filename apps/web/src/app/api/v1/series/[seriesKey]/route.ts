import { z } from "zod";
import { handle, HttpError, json } from "@/lib/server/http";
import { exportVersion, originsFor, seriesDetail } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";
import { seriesKeySchema } from "@/lib/schemas";

export async function GET(request: Request, ctx: { params: Promise<{ seriesKey: string }> }) {
  return handle(request, async (id) => {
    await readRequest(request, z.strictObject({}));
    const key = seriesKeySchema.safeParse(decodeURIComponent((await ctx.params).seriesKey));
    if (!key.success) throw new HttpError(400, "invalid_request", "Invalid series key");
    const series = await seriesDetail(key.data);
    if (!series) throw new HttpError(404, "not_found", "Unknown series");
    return json({ meta: { exportVersion: await exportVersion(), evidence: "validation" },
                  series, origins: await originsFor(series.datasetKey) }, { id, cache: "immutable" });
  });
}
