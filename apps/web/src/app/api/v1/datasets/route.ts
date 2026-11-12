import { z } from "zod";
import { handle, json } from "@/lib/server/http";
import { datasets, exportVersion } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";

export async function GET(request: Request) {
  return handle(request, async (id) => {
    await readRequest(request, z.strictObject({}));
    const rows = await datasets();
    return json({
      meta: { exportVersion: await exportVersion(), evidence: "validation" },
      datasets: rows.map((d) => ({
        ...d,
        coverageNote: d.curatedSeries === d.seriesCount
          ? `All ${d.seriesCount} research series are available in the demo.`
          : `${d.curatedSeries} curated demo series of ${d.seriesCount} in the research population; population statistics use all ${d.seriesCount}.`,
      })),
    }, { id, cache: "immutable" });
  });
}
