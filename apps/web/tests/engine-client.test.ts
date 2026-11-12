/**
 * Phase 7D-3A engine connection security. A real local HTTP server stands in for the protected engine so the
 * headers are observed exactly as they arrive over the wire; a second server on another origin proves that a
 * Vercel-style login redirect never receives the secrets. Responses and server logs are scanned for secret values.
 */
import { createServer, type IncomingHttpHeaders, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { closeDb } from "@/lib/server/db";
import { ConfigurationError, serverEnv } from "@/lib/server/env";
import { LOCAL_SECRETS } from "./setup";
import * as health from "@/app/api/v1/health/route";
import * as simulate from "@/app/api/v1/planner/simulate/route";

const BYPASS = "test-vercel-bypass-secret-0123456789abcdef";
const KEY = LOCAL_SECRETS.ENGINE_SHARED_KEY;
const BASE = { seriesKey: "store_item|1:11", originKey: "store_item|1" };
const ENGINE_RESULT = {
  engineVersion: "cedc5a31533772fc", seriesKey: BASE.seriesKey, originKey: BASE.originKey, historicalMean56: 27.928571428571427,
  demand: [26], dates: ["2017-08-14"],
  policies: [{ policy: "moving_average_28", summary: { total_cost: 1, fill_rate: 1 }, daily: [{ date: "2017-08-14", demand: 26 }] }],
};

type Mode = "ok" | 401 | 403 | 503 | "redirect" | "health";
let mode: Mode = "ok";
const received: { path: string; method: string; headers: IncomingHttpHeaders }[] = [];
const elsewhere: IncomingHttpHeaders[] = [];
let engine: Server, other: Server, enginePort = 0, otherPort = 0;
let ipCounter = 0;
const logs: string[] = [];

function listen(server: Server, host: string): Promise<number> {
  return new Promise((resolve) => server.listen(0, host, () => resolve((server.address() as AddressInfo).port)));
}

beforeAll(async () => {
  engine = createServer((req, res) => {
    received.push({ path: req.url ?? "", method: req.method ?? "", headers: req.headers });
    req.resume();
    if (req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      return res.end(JSON.stringify({ status: "ok", engineVersion: "cedc5a31533772fc", keyConfigured: true }));
    }
    if (mode === "redirect") {
      res.writeHead(302, { location: `http://localhost:${otherPort}/sso-api?url=engine` });
      return res.end();
    }
    if (typeof mode === "number") {
      // Engine/Vercel error bodies must never be echoed: include marker text the test looks for.
      res.writeHead(mode, { "content-type": "text/html" });
      return res.end(`<html>ENGINE-INTERNAL-DETAIL ${mode}</html>`);
    }
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(ENGINE_RESULT));
  });
  other = createServer((req, res) => {
    elsewhere.push(req.headers);
    res.writeHead(200, { "content-type": "application/json" });
    res.end("{}");
  });
  enginePort = await listen(engine, "127.0.0.1");
  otherPort = await listen(other, "127.0.0.1");
  process.env.ENGINE_URL = `http://127.0.0.1:${enginePort}`;
  process.env.VERCEL_PROTECTION_BYPASS_SECRET = BYPASS;
  for (const level of ["log", "info", "warn", "error"] as const) {
    vi.spyOn(console, level).mockImplementation((...args: unknown[]) => { logs.push(args.map(String).join(" ")); });
  }
});

afterEach(() => {
  mode = "ok";
  received.length = 0;
  elsewhere.length = 0;
  process.env.ENGINE_URL = `http://127.0.0.1:${enginePort}`;
  process.env.VERCEL_PROTECTION_BYPASS_SECRET = BYPASS;
});

afterAll(async () => {
  // No secret value or secret-bearing header ever reached a log line.
  const all = logs.join("\n");
  for (const secret of [KEY, BYPASS, "local-webapp-only"]) expect(all.includes(secret)).toBe(false);
  expect(all).not.toMatch(/x-engine-key|x-vercel-protection-bypass|ENGINE-INTERNAL-DETAIL/i);
  vi.restoreAllMocks();
  process.env.ENGINE_URL = LOCAL_SECRETS.ENGINE_URL;
  delete process.env.VERCEL_PROTECTION_BYPASS_SECRET;
  await new Promise((r) => engine.close(r));
  await new Promise((r) => other.close(r));
  await closeDb();
});

async function post(body: unknown = BASE) {
  const response = await simulate.POST(new Request("http://localhost/api/v1/planner/simulate", {
    method: "POST", headers: { "content-type": "application/json", "x-forwarded-for": `10.88.0.${++ipCounter}` },
    body: JSON.stringify(body),
  }));
  const text = await response.text();
  return { status: response.status, headers: response.headers, text, body: JSON.parse(text) };
}

/** A client response never carries a secret, a secret header name, or the engine's own error body. */
function expectNoLeak(r: { headers: Headers; text: string }) {
  const headerDump = [...r.headers.entries()].map(([k, v]) => `${k}: ${v}`).join("\n");
  for (const secret of [KEY, BYPASS]) {
    expect(r.text.includes(secret)).toBe(false);
    expect(headerDump.includes(secret)).toBe(false);
  }
  expect(`${r.text}\n${headerDump}`).not.toMatch(/x-engine-key|x-vercel-protection-bypass|ENGINE-INTERNAL-DETAIL|127\.0\.0\.1/i);
}

describe("server-side engine headers", () => {
  it("sends x-engine-key and x-vercel-protection-bypass on /simulate, server-to-server only", async () => {
    const r = await post();
    expect(r.status).toBe(200);
    expect(received).toHaveLength(1);
    const { headers, method, path } = received[0];
    expect([method, path]).toEqual(["POST", "/simulate"]);
    expect(headers["x-engine-key"]).toBe(KEY);
    expect(headers["x-vercel-protection-bypass"]).toBe(BYPASS);
    expect(headers["x-request-id"]).toMatch(/^[A-Za-z0-9-]{8,64}$/);
    expectNoLeak(r);
  });

  it("sends only the bypass (never the engine key) on /health and never returns either", async () => {
    const response = await health.GET(new Request("http://localhost/api/v1/health", { headers: { "x-forwarded-for": "10.88.1.1" } }));
    const text = await response.text();
    expect(response.status).toBe(200);
    expect(JSON.parse(text).engine).toEqual({ reachable: true, engineVersion: "cedc5a31533772fc" });
    const call = received.find((x) => x.path === "/health")!;
    expect(call.headers["x-vercel-protection-bypass"]).toBe(BYPASS);
    expect(call.headers["x-engine-key"]).toBeUndefined();
    expectNoLeak({ headers: response.headers, text });
  });

  it("omits the bypass header when no bypass is configured for a loopback engine", async () => {
    delete process.env.VERCEL_PROTECTION_BYPASS_SECRET;
    expect((await post()).status).toBe(200);
    expect(received[0].headers["x-vercel-protection-bypass"]).toBeUndefined();
    expect(received[0].headers["x-engine-key"]).toBe(KEY);
  });
});

describe("engine failures are handled safely", () => {
  it.each([
    [401, 502, "engine_auth_rejected"],
    [403, 502, "engine_auth_rejected"],
    [503, 503, "engine_temporarily_unavailable"],
  ] as const)("engine %i -> client %i with the generic fallback message", async (engineStatus, clientStatus, reason) => {
    mode = engineStatus;
    logs.length = 0;
    const r = await post();
    expect(r.status).toBe(clientStatus);
    expect(r.body.error).toBe("engine_unavailable"); // the planner UI keys its precomputed-results fallback on this
    expect(r.body.message).toContain("precomputed Phase 5 results");
    expect(r.headers.get("cache-control")).toBe("no-store");
    expectNoLeak(r);
    expect(logs.some((l) => l.includes(reason) && l.includes(`"engineStatus":${engineStatus}`))).toBe(true);
  });

  it("refuses a login redirect: the other origin receives nothing and the client gets 502", async () => {
    mode = "redirect";
    const r = await post();
    expect(r.status).toBe(502);
    expect(r.body.error).toBe("engine_unavailable");
    expect(elsewhere).toHaveLength(0);
    expectNoLeak(r);
  });

  it("maps an engine timeout to 504 engine_unavailable", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new DOMException("The operation was aborted due to timeout", "TimeoutError"));
    try {
      const r = await post();
      expect(r.status).toBe(504);
      expect(r.body.error).toBe("engine_unavailable");
      expect(r.body.message).toContain("timed out");
      expectNoLeak(r);
      const init = fetchSpy.mock.calls[0][1] as RequestInit;
      expect(init.redirect).toBe("manual");
      expect(init.signal).toBeInstanceOf(AbortSignal);
    } finally {
      fetchSpy.mockRestore();
    }
  });

  it("maps an unreachable engine to 502 without echoing the address", async () => {
    process.env.ENGINE_URL = "http://127.0.0.1:9";
    const r = await post();
    expect(r.status).toBe(502);
    expectNoLeak(r);
  });
});

describe("engine configuration", () => {
  it("requires HTTPS and the bypass secret for a remote engine; never names a value", async () => {
    process.env.ENGINE_URL = "https://idf-engine.example.test";
    delete process.env.VERCEL_PROTECTION_BYPASS_SECRET;
    expect(() => serverEnv()).toThrow(ConfigurationError);
    expect(() => serverEnv()).toThrow(/VERCEL_PROTECTION_BYPASS_SECRET/);
    const r = await post();
    expect(r.status).toBe(503);
    expect(r.body.error).toBe("not_configured");
    expectNoLeak(r);
    expect(received).toHaveLength(0);

    process.env.VERCEL_PROTECTION_BYPASS_SECRET = BYPASS;
    expect(serverEnv().engineBypassSecret).toBe(BYPASS);
    for (const url of ["http://idf-engine.example.test", "https://user:pw@idf-engine.example.test",
                       "https://idf-engine.example.test/?x=1", "ftp://idf-engine.example.test", "not a url"]) {
      process.env.ENGINE_URL = url;
      expect(() => serverEnv(), url).toThrow(/ENGINE_URL/);
    }
  });

  it("no secret is exposed under a NEXT_PUBLIC_ name", () => {
    expect(Object.keys(process.env).filter((k) => k.startsWith("NEXT_PUBLIC_"))).toEqual([]);
  });
});
