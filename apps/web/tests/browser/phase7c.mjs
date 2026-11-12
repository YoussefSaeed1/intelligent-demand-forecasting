// Real local stack browser QA, with explicitly labelled intercepted error-state checks at the end.
// Run from apps/web: node tests/browser/phase7c.mjs
import { chromium } from "playwright-core";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import assert from "node:assert/strict";
import { scanCopy } from "../copy-gate.mjs";

const out = resolve(process.env.QA_OUT ?? "../../reports/webapp/phase7c_final");
await mkdir(out, { recursive: true });
const base = process.env.APP_URL ?? "http://127.0.0.1:3000";
const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage();
page.setDefaultTimeout(15_000);
const report = { base, backend: "real local Postgres and Python engine", pages: [], interactions: [], interceptedStates: [], console: [] };
page.on("pageerror", (e) => report.console.push(e.message));
page.on("console", (m) => { if (m.type() === "error") report.console.push(m.text()); });
try {
  for (const width of [1280, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/", "/forecasts", "/planner", "/scenarios", "/research"]) {
      const response = await page.goto(base + path, { waitUntil: "networkidle" });
      assert.equal(response.status(), 200);
      await page.locator("main").waitFor();
      if (path === "/forecasts") await page.getByTestId("metrics-table").waitFor();
      if (path === "/scenarios") await page.getByTestId("scenario-pooled").waitFor();
      if (path === "/") await page.getByTestId("policy-table").waitFor();
      if (path === "/planner") {
        await page.getByRole("button", { name: "Run simulation" }).click();
        await page.getByTestId("planner-results").waitFor();
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
      await page.addScriptTag({ path: resolve("node_modules/axe-core/axe.min.js") });
      const violations = await page.evaluate(async () => (await window.axe.run(document.querySelector("main"))).violations
        .filter((v) => ["critical", "serious"].includes(v.impact)).map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.map((n) => n.target) })));
      const copy = await page.locator("main").innerText();
      const copyGate = scanCopy(copy);
      const screenshot = `${path === "/" ? "overview" : path.slice(1)}_${width}.png`;
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({ path: resolve(out, screenshot), fullPage: true });
      report.pages.push({ path, width, status: response.status(), overflow, violations, copyGate, screenshot });
      assert.equal(overflow, 0, `Horizontal overflow ${path} at ${width}`);
    }
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(base + "/forecasts?series=store_item%7C1%3A11&origin=store_item%7C1", { waitUntil: "networkidle" });
  await page.getByRole("link", { name: /Open in Inventory Planner/ }).click();
  await page.waitForURL(/\/planner\?/);
  assert.equal(new URL(page.url()).searchParams.get("origin"), "store_item|1");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.getByTestId("planner-results").waitFor();
  assert.equal(await page.getByTestId("planner-results").getByRole("row").count(), 5);
  // Real engine parity in the browser: each base-scenario run total equals the saved Phase 5 total shown beside it.
  const parity = await page.getByTestId("planner-results").locator("tbody tr").evaluateAll((rows) =>
    rows.map((r) => [...r.querySelectorAll("th,td")].map((c) => c.textContent.trim())));
  for (const row of parity) assert.equal(row[1], row[2], `run vs saved Phase 5 total for ${row[0]}`);
  report.interactions.push(`Real engine run equals saved Phase 5 base totals for ${parity.length} policies: ${parity.map((r) => `${r[0]} ${r[1]}`).join("; ")}`);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export planner CSV" }).click();
  const download = await downloadPromise;
  await download.saveAs(resolve(out, "planner_run.csv"));
  report.interactions.push("Explorer → Planner preserves series/origin; real four-policy run; server CSV downloaded");
  const pngPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /Export PNG: Daily closing/ }).click();
  const png = await pngPromise;
  await png.saveAs(resolve(out, "inventory_chart.png"));
  report.interactions.push("Displayed inventory SVG exported as PNG with scientific caption");
  await page.getByRole("spinbutton", { name: "Lead time (days)" }).fill("15");
  assert.equal(await page.getByRole("button", { name: "Run simulation" }).isDisabled(), true);
  await page.getByText("Enter a number from 0 to 14 (whole days).").waitFor();
  assert.equal(await page.getByTestId("planner-results").count(), 0);
  report.interactions.push("Invalid bounds block execution and clear stale results");
  await page.goto(base + "/scenarios?dataset=m5", { waitUntil: "networkidle" });
  const filtered = page.waitForResponse((r) => r.url().includes("/inventory/study") && r.url().includes("pattern=all_zero"));
  await page.locator("#study-pattern").selectOption("all_zero");
  assert.equal((await filtered).status(), 200);
  await page.getByTestId("scenario-pooled").getByRole("row").nth(4).waitFor();
  assert.equal(await page.getByTestId("scenario-pooled").getByRole("row").count(), 5);
  report.interactions.push("Real saved study filters by demand pattern");
  await page.goto(base + "/scenarios?dataset=store_item", { waitUntil: "networkidle" });
  await page.getByText(/Store Item final-origin cost reversal/).waitFor();
  await page.getByRole("radio", { name: "Origin 4" }).click();
  await page.waitForURL(/origin=store_item%7C4/);
  await page.getByTestId("origin-grid-table").waitFor();
  report.interactions.push("Scenario origin filter is URL state; Store Item final-origin reversal shown from real data");
  // Intercepted (mocked) engine outage: honest error plus clearly labelled precomputed Phase 5 fallback (real GET).
  {
    const context = await browser.newContext();
    const mockPage = await context.newPage();
    await mockPage.route("**/api/v1/planner/simulate", (route) => route.fulfill({ status: 502, contentType: "application/json",
      body: JSON.stringify({ error: "engine_unavailable", message: "The simulation engine is unavailable; precomputed Phase 5 results remain available" }) }));
    await mockPage.goto(base + "/planner", { waitUntil: "networkidle" });
    await mockPage.getByRole("button", { name: "Run simulation" }).click();
    await mockPage.getByText("Simulation unavailable").waitFor();
    await mockPage.getByTestId("fallback-table").waitFor();
    await mockPage.getByRole("note", { name: "Precomputed fallback" }).waitFor();
    report.interceptedStates.push("engine unavailable: error + labelled precomputed fallback PASS (simulate mocked; fallback GET real)");
    await context.close();
  }
  // Fresh contexts ensure no memoised GET can mask intercepted failures.
  for (const state of ["loading", "empty", "error"]) {
    const context = await browser.newContext();
    const mockPage = await context.newPage();
    mockPage.setDefaultTimeout(15_000);
    await mockPage.route("**/api/v1/inventory/study?*", async (route) => {
      if (state === "loading") await new Promise((resolve) => setTimeout(resolve, 1500));
      await route.fulfill({ status: state === "error" ? 503 : 200, contentType: "application/json",
        body: JSON.stringify(state === "error" ? { error: "not_configured", message: "Unavailable" } : { meta: {}, policies: [], pooled: [], perOrigin: [] }) });
    });
    await mockPage.goto(base + "/scenarios", { waitUntil: "domcontentloaded" });
    if (state === "loading") await mockPage.getByRole("status").filter({ hasText: "Loading saved Phase 5 scenarios" }).waitFor();
    else if (state === "empty") await mockPage.getByText("No saved study episodes").waitFor();
    else await mockPage.getByRole("alert").waitFor();
    report.interceptedStates.push(`${state}: PASS (mocked, not integration)`);
    await context.close();
  }
} finally {
  await writeFile(resolve(out, "browser-qa.json"), JSON.stringify(report, null, 2));
  await browser.close();
}
assert.equal(report.console.length, 0, "Browser console errors");
assert.equal(report.pages.flatMap((p) => p.violations).length, 0, "Serious/critical axe findings");
assert.equal(report.pages.filter((p) => !p.copyGate.pass).length, 0, "U-05 copy gate");
console.log(JSON.stringify(report, null, 2));
