// Developer helper: screenshots of pages from the running local app with the installed Microsoft Edge.
// Usage: node tests/browser/shot.mjs <outDir> <width> <path> [<path> ...]
import { chromium } from "playwright-core";

const [outDir, width, ...paths] = process.argv.slice(2);
const base = process.env.APP_URL ?? "http://127.0.0.1:3000";
const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({ viewport: { width: Number(width), height: 900 } });
const problems = [];
page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") problems.push(`${m.type()}: ${m.text()}`); });
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
for (const path of paths) {
  await page.goto(base + path, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const name = path.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") || "home";
  await page.screenshot({ path: `${outDir}/${name}_${width}.png`, fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  console.log(`${path} overflowX=${overflow}`);
}
console.log(problems.length ? problems.join("\n") : "no console errors");
await browser.close();
