import { handle, json } from "@/lib/server/http";
import { exportVersion, seriesList } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";
import { seriesListSchema } from "@/lib/schemas";

export async function GET(request: Request) {
  return handle(request, async (id) => {
    const q = await readRequest(request, seriesListSchema);
    const page = await seriesList(q.dataset, q.pattern, q.q, q.limit, q.cursor);
    return json({ meta: { exportVersion: await exportVersion(), evidence: "validation", scope: "curated demo series" },
                  ...page }, { id, cache: "immutable" });
  });
}
