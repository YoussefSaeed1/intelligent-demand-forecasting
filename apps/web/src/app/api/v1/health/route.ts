import { engineHealth } from "@/lib/server/engine";
import { handle, json, rateLimit } from "@/lib/server/http";
import { exportVersion } from "@/lib/server/repository";
import { serverEnv } from "@/lib/server/env";

export async function GET(request: Request) {
  return handle(request, async (id) => {
    await rateLimit(request, "read", serverEnv().readPerMinute, 60);
    const [version, engine] = await Promise.all([exportVersion(), engineHealth()]);
    return json({
      status: engine.reachable ? "ok" : "degraded",
      exportVersion: version,
      engine,
      build: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 12) ?? "local",
    }, { id });
  });
}
