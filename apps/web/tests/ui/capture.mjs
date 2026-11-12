// Captures real responses from the locally running Phase 7B API (next dev on 127.0.0.1:3000 with the local
// Postgres and engine) into tests/ui/fixtures. Run: node tests/ui/capture.mjs [baseUrl]
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const base = process.argv[2] ?? "http://127.0.0.1:3000/api/v1";
const out = join(dirname(fileURLToPath(import.meta.url)), "fixtures");
mkdirSync(out, { recursive: true });

const reads = {
  health: "/health",
  datasets: "/datasets",
  research: "/research",
  aggregate_store_item: "/metrics/aggregate?dataset=store_item",
  aggregate_m5: "/metrics/aggregate?dataset=m5",
  aggregate_store_item_smooth: "/metrics/aggregate?dataset=store_item&pattern=smooth",
  study_store_item: "/inventory/study?dataset=store_item",
  study_m5: "/inventory/study?dataset=m5",
  series_store_item: "/series?dataset=store_item&limit=25",
  series_m5: "/series?dataset=m5&limit=25",
  forecasts_store_item: "/forecasts?origin=store_item%7C4&series=store_item%7C1%3A11",
  series_base_store_item: "/inventory/series-base?series=store_item%7C1%3A11",
};

for (const [name, path] of Object.entries(reads)) {
  const response = await fetch(base + path);
  if (!response.ok) throw new Error(`${path} -> ${response.status}`);
  writeFileSync(join(out, `${name}.json`), JSON.stringify(await response.json(), null, 1));
}

const simulate = await fetch(`${base}/planner/simulate`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ seriesKey: "store_item|1:11", originKey: "store_item|4" }),
});
if (!simulate.ok) throw new Error(`simulate -> ${simulate.status}`);
writeFileSync(join(out, "simulate_store_item.json"), JSON.stringify(await simulate.json(), null, 1));
console.log(`captured ${Object.keys(reads).length + 1} fixtures into ${out}`);
