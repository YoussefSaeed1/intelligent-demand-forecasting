import { handle, json } from "@/lib/server/http";
import { parseSimulateBody, simulate } from "@/lib/server/planner";
import { simulateLimits } from "@/lib/server/routes";

/** Bounded, server-mediated hypothetical simulation on saved validation demand (one series, one origin). */
export async function POST(request: Request) {
  return handle(request, async (id) => {
    await simulateLimits(request);
    const body = await parseSimulateBody(request);
    return json(await simulate(body, id), { id });
  });
}
