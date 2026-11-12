"use client";

import Link from "next/link";
import { apiPath } from "@/lib/api/client";
import type { HealthResponse } from "@/lib/api/types";
import { useApi } from "@/lib/api/useApi";

/** Export version and engine reachability (checked once per session), plus the standing limitation link. */
export function StatusFooter() {
  const { data, error } = useApi<HealthResponse>(apiPath("/health"));
  const engine = data ? (data.engine.reachable ? "reachable" : "unavailable (precomputed results only)") : error ? "unknown" : "checking…";
  return (
    <footer className="mt-10 border-t border-line px-4 py-4 text-xs text-muted sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-center gap-x-5 gap-y-1">
        <span>Export <code className="text-ink-2">{data?.exportVersion ?? "—"}</code></span>
        <span>Simulation engine: <span data-testid="engine-status" className="text-ink-2">{engine}</span>
          {data?.engine.engineVersion && <> · <code>{data.engine.engineVersion}</code></>}</span>
        <span>Build <code>{data?.build ?? "—"}</code></span>
        <Link href="/research#limitations" className="text-brand underline-offset-2 hover:underline">Known limitations</Link>
        <span className="basis-full sm:basis-auto">Academic project (Cairo University). Costs are hypothetical normalised cost units, not realised savings.</span>
      </div>
    </footer>
  );
}
