/**
 * Test boundary doubles for isolated component tests: an in-memory URL for next/navigation and a fetch
 * double that serves fixtures captured from the real local Phase 7B API (tests/ui/fixtures, see capture.mjs).
 * These tests are NOT backend integration evidence; that lives in tests/api.test.ts and the browser QA run.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { useSyncExternalStore } from "react";
import { vi } from "vitest";

let url = new URL("http://localhost/");
const listeners = new Set<() => void>();
export const router = {
  replace: vi.fn((href: string) => setUrl(href)),
  push: vi.fn((href: string) => setUrl(href)),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
};

export function setUrl(href: string) {
  url = new URL(href, "http://localhost");
  listeners.forEach((l) => l());
}

export function currentUrl(): URL {
  return url;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function usePathnameDouble() {
  return useSyncExternalStore(subscribe, () => url.pathname);
}

export function useSearchParamsDouble() {
  const search = useSyncExternalStore(subscribe, () => url.search);
  return new URLSearchParams(search);
}

const FIXTURES = join(__dirname, "fixtures");
export function fixture<T = unknown>(name: string): T {
  return JSON.parse(readFileSync(join(FIXTURES, `${name}.json`), "utf8")) as T;
}

export type Route = (request: { url: URL; method: string; body: unknown }) =>
  { status?: number; body: unknown; delayMs?: number; headers?: Record<string, string> } | undefined;

/** Installs a fetch double; unmatched requests fail loudly so a test can never silently hit the network. */
export function mockFetch(routes: Route[]) {
  const calls: { url: URL; method: string; body: unknown }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const target = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url, "http://localhost");
    const method = (init?.method ?? "GET").toUpperCase();
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    const call = { url: target, method, body };
    calls.push(call);
    for (const route of routes) {
      const hit = route(call);
      if (!hit) continue;
      if (hit.delayMs) {
        await new Promise<void>((resolve, reject) => {
          const timer = setTimeout(resolve, hit.delayMs);
          init?.signal?.addEventListener("abort", () => {
            clearTimeout(timer);
            reject(init.signal?.reason ?? new DOMException("Aborted", "AbortError"));
          });
        });
      }
      const text = typeof hit.body === "string" ? hit.body : JSON.stringify(hit.body);
      return new Response(text, { status: hit.status ?? 200,
                                  headers: { "content-type": "application/json", ...hit.headers } });
    }
    throw new Error(`Unmocked request ${method} ${target.pathname}${target.search}`);
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}

/** Route helper: match by pathname (and optional query predicate). */
export function on(pathname: string, respond: (url: URL, body: unknown) => ReturnType<Route>,
                   method = "GET"): Route {
  return ({ url: u, method: m, body }) => (u.pathname === pathname && m === method ? respond(u, body) : undefined);
}

/** Standard read fixtures (captured from the local stack) for the read endpoints. */
export function readRoutes(): Route[] {
  return [
    on("/api/v1/health", () => ({ body: fixture("health") })),
    on("/api/v1/datasets", () => ({ body: fixture("datasets") })),
    on("/api/v1/research", () => ({ body: fixture("research") })),
    on("/api/v1/metrics/aggregate", (u) => ({ body: fixture(`aggregate_${u.searchParams.get("dataset")}${u.searchParams.get("pattern") ? `_${u.searchParams.get("pattern")}` : ""}`) })),
    on("/api/v1/inventory/study", (u) => ({ body: fixture(`study_${u.searchParams.get("dataset")}`) })),
    on("/api/v1/series", (u) => ({ body: fixture(`series_${u.searchParams.get("dataset")}`) })),
    on("/api/v1/forecasts", () => ({ body: fixture("forecasts_store_item") })),
    on("/api/v1/inventory/series-base", () => ({ body: fixture("series_base_store_item") })),
  ];
}

export function NoopLink({ href, children, ...rest }: { href: string | { pathname?: string }; children: React.ReactNode } & Record<string, unknown>) {
  const target = typeof href === "string" ? href : href.pathname ?? "/";
  return <a href={target} {...rest}>{children}</a>;
}
