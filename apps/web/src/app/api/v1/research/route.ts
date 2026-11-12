import { z } from "zod";
import { handle, json, NCU_NOTICE } from "@/lib/server/http";
import { provenance, research } from "@/lib/server/repository";
import { readRequest } from "@/lib/server/routes";

export async function GET(request: Request) {
  return handle(request, async (id) => {
    await readRequest(request, z.strictObject({}));
    const [content, source] = await Promise.all([research(), provenance()]);
    return json({
      meta: { exportVersion: source.exportVersion, ncuNotice: NCU_NOTICE },
      provenance: source,
      limitations: content.limitations,
      auditFindings: content.findings,
      demandPatterns: content.patterns,
      modelSelectionTrials: { evidence: "validation", rows: content.trials },
      finalHoldout: { evidence: "reported_final_holdout",
                      note: "Saved Phase 4 one-time final assessment, reported as recorded; not a new evaluation.",
                      rows: content.finalHoldout },
    }, { id, cache: "immutable" });
  });
}
