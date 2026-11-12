// Viva presentation (.pptx). Numbers come from the verified evidence (see 02_traceability). Run with NODE_PATH set to a
// folder containing pptxgenjs, and pass the pptx skill's scripts directory for apply_theme.js:
//   NODE_PATH=<node_modules> node final_submission/_tools/build_deck.js <pptx-skill-scripts-dir>
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(path.join(process.argv[2], "apply_theme.js"));

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "final_submission", "04_presentation", "IDF_Viva_Presentation.pptx");
fs.mkdirSync(path.dirname(OUT), { recursive: true });
const img = (p) => path.join(ROOT, p);
const ev = JSON.parse(fs.readFileSync(path.join(ROOT, "final_submission/figures/figure_data.json"), "utf8"));

const THEME = {
  name: "IDF Research", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "0B0B0B", lt1: "FFFFFF", dk2: "14253D", lt2: "EEF2F7", accent1: "2A78D6", accent2: "EB6834",
    accent3: "1BAF7A", accent4: "EDA100", accent5: "6250D6", accent6: "D03B3B", hlink: "2A78D6", folHlink: "6250D6" },
};
const HEX = { navy: "14253D", blue: "2A78D6", orange: "EB6834", aqua: "1BAF7A", yellow: "EDA100", violet: "6250D6",
  red: "D03B3B", ink2: "52514E", muted: "898781", grid: "E6E5E0", tint: "EEF2F7", white: "FFFFFF" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.title = "Intelligent Demand Forecasting and Inventory Optimisation";
pres.author = "Youssef Saeed";
pres.company = "Cairo University";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

const FOOT = "Cairo University · Postgraduate Data Science · Intelligent Demand Forecasting and Inventory Optimisation";
pres.defineSlideMaster({
  title: "DARK", background: { color: HEX.navy },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.7, h: 1.6, fontSize: 40, bold: true,
    color: C.background1, fontFace: "Cambria", valign: "bottom" }, text: "" } },
  { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.05, w: 11.7, h: 1.6, fontSize: 18, color: "CADCFC",
    valign: "top" }, text: "" } }],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: HEX.white },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 30, bold: true,
      color: C.text2, fontFace: "Cambria", valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: FOOT, options: { x: 0.6, y: 7.05, w: 10.5, h: 0.3, fontSize: 10, color: "6B6A66", margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.5, h: 0.3, fontSize: 10, color: "6B6A66", align: "right" },
});

let n = 0;
function slide(master, section, title, notes) {
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  if (title) s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(notes);
  n += 1;
  return s;
}
const text = (s, t, o) => s.addText(t, { isTextBox: true, margin: 0, fontSize: 15, color: HEX.ink2, valign: "top", ...o });
function card(s, x, y, w, h, head, body, color, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: opts.fill || HEX.tint },
    line: { color: opts.fill || HEX.tint }, objectName: "card " + head });
  s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.27, w: 0.22, h: 0.22, fill: { color }, line: { color } });
  text(s, head, { x: x + 0.6, y: y + 0.18, w: w - 0.8, h: 0.42, fontSize: 17, bold: true, color: HEX.navy, valign: "middle" });
  text(s, body, { x: x + 0.25, y: y + 0.72, w: w - 0.5, h: h - 0.9, fontSize: opts.size || 14 });
}
function stat(s, x, y, w, value, label, color) {
  text(s, value, { x, y, w, h: 0.95, fontSize: 44, bold: true, color, fontFace: "Cambria", valign: "bottom" });
  text(s, label, { x, y: y + 1.0, w, h: 0.8, fontSize: 13, color: HEX.ink2 });
}
const source = (s, t) => text(s, t, { x: 0.6, y: 6.62, w: 12.1, h: 0.32, fontSize: 11, color: "6B6A66", italic: true });
const chartBase = { catAxisLabelColor: HEX.ink2, valAxisLabelColor: HEX.ink2, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" },
  dataLabelFontFace: "+mn-lt", dataLabelFontSize: 10, dataLabelColor: "0B0B0B", titleFontFace: "+mn-lt", titleColor: HEX.navy, titleFontSize: 14,
  legendFontFace: "+mn-lt", legendFontSize: 11, legendColor: HEX.ink2 };

// ------------------------------------------------------------------ 1 Title
pres.addSection({ title: "Introduction" });
let s = slide("DARK", "Introduction", "Intelligent Demand Forecasting and Inventory Optimisation",
  "Good morning. My project asks a simple business question with a careful scientific answer: does machine-learning forecasting beat simple rules for daily retail demand, and what would that mean for inventory? I tested this on two public retail datasets under one governed protocol, evaluated the final models exactly once on a sealed holdout, simulated four replenishment policies, and deployed the evidence as a public research application. I will spend about twenty minutes and then take questions.");
s.addText("A governed comparison of statistical and machine-learning forecasts, a hypothetical inventory simulation and a deployed research application", { placeholder: "body" });
text(s, "Youssef Saeed  ·  Postgraduate Diploma in Data Science, Cairo University  ·  November 2026", { x: 0.8, y: 6.3, w: 11.7, h: 0.4, fontSize: 14, color: "CADCFC" });

// ------------------------------------------------------------------ 2 Problem
s = slide("CONTENT", "Introduction", "Every order is a bet on tomorrow's demand",
  "Retailers reorder thousands of store-item combinations every day. Too little stock loses sales; too much ties up capital. Both mistakes start with the demand forecast. Machine learning is often promoted as the fix, but claims are hard to compare because studies use different data, horizons and error measures. My two datasets have opposite characters: Store Item is regular and seasonal; M5 from Walmart is mostly intermittent, with almost seven in ten days showing zero sales. That contrast is what makes the comparison informative. One caveat from the start: the data record sales, not demand, and contain no stock or cost data, so the inventory part is a hypothetical simulation.");
stat(s, 0.6, 1.55, 3.8, "30,990", "daily store-item series analysed (500 Store Item + 30,490 M5)", HEX.blue);
stat(s, 4.75, 1.55, 3.8, "60.1 M", "daily sales observations across both histories (913,000 + 59,181,090)", HEX.navy);
stat(s, 8.9, 1.55, 3.8, "68.8%", "of M5 training-period series-day observations have zero sales: intermittent demand", HEX.orange);
card(s, 0.6, 4.2, 5.9, 2.2, "Why it matters", "Under-forecasting loses sales and goodwill; over-forecasting raises holding cost and waste. Forecast quality is only valuable through the decisions it drives.", HEX.blue);
card(s, 6.8, 4.2, 5.9, 2.2, "What makes it hard", "Comparisons of ML and simple rules differ in data, horizon, windows and metrics. Sales are censored by stock-outs, so observed sales understate true demand.", HEX.orange);

// ------------------------------------------------------------------ 3 Objectives
s = slide("CONTENT", "Introduction", "Four research questions",
  "These four questions come directly from the project proposal. RQ1 is the core benchmark. RQ2 asks which data and feature choices matter, for example whether prices can be used safely. RQ3 asks whether a ranking found on one dataset holds on a very different second dataset. RQ4 moves from accuracy to decisions: how do simulated cost and service respond to the forecast and to the assumed operating parameters? Out of scope were causal business claims, reconstructing real stock and any claim of real savings.");
const rq = [["RQ1  Methods", "How do naive, statistical and machine-learning approaches compare on the same 28-day daily horizon and windows?", HEX.blue],
  ["RQ2  Data and features", "Which data-quality and feature choices affect forecast reliability across series?", HEX.aqua],
  ["RQ3  Replication", "Does the relative ranking of methods hold on a second, independently sourced dataset?", HEX.violet],
  ["RQ4  Decisions", "How sensitive are simulated cost and service trade-offs to the forecast policy and assumed parameters?", HEX.orange]];
rq.forEach(([h, b, c], i) => card(s, 0.6 + (i % 2) * 6.2, 1.45 + Math.floor(i / 2) * 2.55, 5.9, 2.3, h, b, c, { size: 15 }));

// ------------------------------------------------------------------ 4 Datasets
pres.addSection({ title: "Data" });
s = slide("CONTENT", "Data", "Two public datasets with opposite demand character",
  "Store Item from Kaggle has 500 series over five years with complete coverage and only a single zero. M5 is Walmart data: 30,490 series, 59 million daily rows, and highly concentrated volume, where the top ten percent of products carry over half the units. M5 has weekly prices, but a fifth are missing, almost always before a product's first sale. Both datasets were converted into one canonical schema with unique keys, and all source hashes were re-verified in the final audit. I never merged the two sources or treated them as one population.");
const rowsD = [["", "Store Item", "M5 (Walmart)"], ["History", "2013-01-01 to 2017-12-31", "2011-01-29 to 2016-05-22"], ["Stores / products / series", "10 / 50 / 500", "10 / 3,049 / 30,490"],
  ["Daily observations", "913,000", "59,181,090"], ["Zero days (training prefix)", "1 (0.0001%)", "68.84%"], ["Median daily units", "46", "0"],
  ["Top-10% products' share of units", "16.3%", "51.7%"], ["Prices", "none", "weekly; 20.8% missing"]];
s.addTable(rowsD.map((r, i) => r.map((c, j) => ({ text: c, options: { bold: i === 0 || j === 0, color: i === 0 ? HEX.white : "0B0B0B",
  fill: { color: i === 0 ? HEX.navy : (i % 2 ? HEX.white : HEX.tint) }, fontSize: 15 } }))),
  { x: 0.6, y: 1.5, w: 12.1, colW: [4.1, 4, 4], rowH: 0.52, border: { type: "solid", pt: 0.5, color: "D0D5DD" }, valign: "middle" });
source(s, "Source: docs/EDA_FINDINGS.md, docs/DATASETS.md. Raw Kaggle files are not redistributed; data-use terms review by the owner is pending.");

// ------------------------------------------------------------------ 5 EDA patterns
s = slide("CONTENT", "Data", "EDA: M5 is mostly intermittent; Store Item is smooth",
  "Exploratory analysis used only the training prefix, so nothing about the validation or final windows could leak into design choices. Using the Syntetos-Boylan-Croston ADI and CV-squared scheme, all 500 Store Item series are smooth, while three quarters of M5 series are intermittent and a fifth lumpy, with a few all-zero histories. This single chart explains most of the later results: methods that exploit regular seasonality do well on Store Item, while on M5 a simple average is already hard to beat.");
s.addImage({ path: img("reports/figures/phase2/m5_classification.png"), x: 0.6, y: 1.4, w: 8.2, h: 3.35 });
card(s, 9.1, 1.4, 3.6, 3.35, "Store Item", "All 500 series smooth. Strong weekly cycle: Sunday 1.19 and Monday 0.79 of the week's mean; weekly STL strength 0.976.", HEX.blue, { size: 14 });
card(s, 0.6, 4.95, 12.1, 1.5, "Implication for design", "Seasonal and smoothing baselines plus global ML for Store Item; intermittent-demand methods (Croston, SBA, TSB) plus global ML for M5, scored by demand class.", HEX.aqua, { size: 14 });
source(s, "ADI cut-off 1.32, CV² cut-off 0.49 (Syntetos, Boylan and Croston, 2005). Figure: reports/figures/phase2/m5_classification.png. Full references: research paper.");

// ------------------------------------------------------------------ 6 EDA calendar + prices
s = slide("CONTENT", "Data", "EDA: stable calendars; prices unusable at the origin",
  "Store Item shows a very stable weekly and annual calendar, with tight bootstrap intervals. For M5, a key finding was about prices: every missing price in the training prefix coincides with zero sales, mostly before a product's first sale. More importantly, I could not verify when prices were published relative to the forecast origin, so using them could leak future information. All final models are therefore price-free. That is my answer to RQ2: the decisive choices were excluding features whose availability is uncertain, keeping zeros and missing values rather than imputing, and evaluating full populations.");
s.addImage({ path: img("reports/figures/phase2/store_item_calendar_patterns.png"), x: 0.6, y: 1.4, w: 7.6, h: 2.76 });
card(s, 8.5, 1.4, 4.2, 2.76, "M5 prices", "12.3 million missing prices (20.8%, full history); all 12,298,948 in the training prefix coincide with zero sales. Publication latency unverified, so prices, events and SNAP are excluded from every final model.", HEX.orange, { size: 14 });
card(s, 0.6, 4.4, 12.1, 2.0, "Data quality decisions (RQ2)", "No imputation of sales or prices; zeros and extreme values preserved after checks against source files; no deletion of difficult series; competition test rows without labels never used as targets.", HEX.violet, { size: 14 });
source(s, "Figure: reports/figures/phase2/store_item_calendar_patterns.png (training prefix 2013-01-01 to 2017-08-13).");

// ------------------------------------------------------------------ 7 Forecasting architecture
pres.addSection({ title: "Method" });
s = slide("CONTENT", "Method", "Forecasting architecture: 28 days, recursive, leakage-controlled",
  "Every method forecasts the next 28 days from an origin, without seeing any actual sales in that window. The machine-learning models are global: one model per dataset trained across all series, as a one-step regressor applied recursively, so from day two onwards it uses its own predictions as lags. Features use only data strictly before each target date, and tests deliberately poison future values to prove that the forecasts cannot depend on them. Forecasts are never rounded, are clipped at zero, and every series must receive a forecast.");
const steps = [["1  Origin", "All data up to and including the origin date", HEX.navy], ["2  Features", "Lags 1, 7, 14, 28, 56; rolling means; zero fractions; ADI/CV²; calendar; IDs", HEX.blue],
  ["3  One-step model", "Global LightGBM or random forest per dataset", HEX.aqua], ["4  Recurse 28 days", "Own clipped predictions feed later lags", HEX.violet]];
steps.forEach(([h, b, c], i) => {
  const x = 0.6 + i * 3.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.55, w: 2.8, h: 2.1, rectRadius: 0.08, fill: { color: HEX.tint }, line: { color: HEX.tint } });
  text(s, h, { x: x + 0.2, y: 1.7, w: 2.4, h: 0.45, fontSize: 17, bold: true, color: c });
  text(s, b, { x: x + 0.2, y: 2.2, w: 2.4, h: 1.35, fontSize: 14 });
  if (i < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.83, y: 2.45, w: 0.24, h: 0.32, fill: { color: HEX.muted }, line: { color: HEX.muted } });
});
card(s, 0.6, 3.95, 5.9, 2.45, "Information contract", "Every feature for target date t uses observations strictly before t. Prices, events and SNAP excluded. Occurrence statistics frozen at the origin so predictions are never treated as observed sales.", HEX.red, { size: 14 });
card(s, 6.8, 3.95, 5.9, 2.45, "Delivery rules", "No rounding; clip at zero; predeclared seasonal-naive fallback counted if a fit fails (none needed in the final assessment); full populations: 500 and 30,490 series.", HEX.blue, { size: 14 });
source(s, "Source: docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md, docs/PHASE4_FEATURE_AVAILABILITY.md.");

// ------------------------------------------------------------------ 8 Validation methodology
s = slide("CONTENT", "Method", "Validation: four expanding origins and one sealed final window",
  "The evaluation is purely chronological. Training expands: each origin uses everything up to that date, and the next 28 days are the target. There are four validation windows and then the final holdout, which was evaluated only once, after the model choice was frozen. Two caveats I state openly: the four origins are adjacent, so they show variability over a limited season rather than four independent replications, and repeated tuning on the same windows makes validation scores optimistic, which is why the sealed holdout matters.");
s.addImage({ path: img("final_submission/figures/fig_rolling_origin.png"), x: 0.6, y: 1.35, w: 8.4, h: 2.9 });
card(s, 9.25, 1.35, 3.45, 2.9, "Primary objective", "Mean over the four origins of macro MAE (each series weighted equally), declared before any scoring.", HEX.blue, { size: 14 });
card(s, 0.6, 4.5, 5.9, 1.95, "Secondary metrics", "Pooled RMSE and WAPE, bias, and scaled MASE and RMSSE. Undefined values stay undefined, never zero.", HEX.aqua, { size: 14 });
card(s, 6.8, 4.5, 5.9, 1.95, "Not claimed", "No significance tests (four correlated origins); not the official M5 WRMSSE; no direct cross-dataset transfer.", HEX.orange, { size: 14 });

// ------------------------------------------------------------------ 9 Governance
s = slide("CONTENT", "Method", "Governance: the final holdout could not influence model choice",
  "This is the part of the project I am proudest of. After validation, the selection was frozen in a manifest whose SHA-256 fingerprint covers the chosen models, features, comparators and 89 source files. All final forecasts were sealed before the first holdout read, and each dataset's holdout was read exactly once, recorded in a hash-chained ledger of twelve events. In the final audit I re-verified the fingerprint, the ledger chain and all nine data file hashes. One honest limitation: the ledger timestamps are self-recorded, so this proves order only if the recorder is trusted.");
const gov = [["Freeze", "Manifest a71ab187… fixes models, features, comparators and 89 source files", HEX.navy], ["Seal", "3,470,880 final forecasts sealed before any target read", HEX.blue],
  ["Read once", "Each holdout read once; 12‑event hash‑chained ledger fa2af529…", HEX.violet], ["Re-verify", "Phase 8 audit: fingerprint, ledger chain and 9 data hashes all match", HEX.aqua]];
gov.forEach(([h, b, c], i) => {
  const x = 0.6 + i * 3.1;
  s.addShape(pres.shapes.OVAL, { x: x + 0.95, y: 1.6, w: 0.9, h: 0.9, fill: { color: c }, line: { color: c } });
  text(s, String(i + 1), { x: x + 0.95, y: 1.6, w: 0.9, h: 0.9, fontSize: 28, bold: true, color: HEX.white, align: "center", valign: "middle", fontFace: "Cambria" });
  text(s, h, { x, y: 2.65, w: 2.8, h: 0.45, fontSize: 18, bold: true, color: HEX.navy, align: "center" });
  text(s, b, { x: x + 0.1, y: 3.15, w: 2.6, h: 1.4, fontSize: 14, align: "center" });
});
card(s, 0.6, 4.85, 12.1, 1.55, "Independent technical audit (2026-11-10)", "AI-assisted review of Phases 0 to 5 in a separate context: verdict CONDITIONAL with 0 critical, 0 high, 6 medium and 4 low findings. Its reporting rules govern every result shown today.", HEX.orange, { size: 14 });

// ------------------------------------------------------------------ 10 Models
s = slide("CONTENT", "Method", "Models and baselines",
  "I compared thirteen methods in Phase 3 on the full populations. The baselines matter because they set the bar: naive, seasonal naive and moving averages. Statistical comparators include exponential smoothing, Holt-Winters and the intermittent-demand family: Croston, its bias-corrected SBA variant, and TSB, which updates the demand probability every period. ARIMA and SARIMA were run only on small stratified subsets, so I make no population claims about them. In Phase 4 a seeded random search evaluated 23 tuning trials plus four unchanged references, 108 fold runs in total.");
const fam = [["Baselines", "Zero · Naive · Seasonal naive · MA28 · Seasonal moving average", HEX.muted], ["Exponential smoothing", "SES · Holt · Additive Holt-Winters (weekly)", HEX.violet],
  ["Intermittent demand", "Croston (1972) · SBA (Syntetos and Boylan, 2005) · TSB (Teunter et al., 2011)", HEX.aqua], ["Global machine learning", "Random forest · LightGBM: one model per dataset, recursive", HEX.blue]];
fam.forEach(([h, b, c], i) => card(s, 0.6 + (i % 2) * 6.2, 1.45 + Math.floor(i / 2) * 1.95, 5.9, 1.75, h, b, c, { size: 15 }));
stat(s, 0.6, 5.3, 3.6, "27", "Phase 4 configurations (23 tuned + 4 references)", HEX.navy);
source(s, "ARIMA and SARIMA ran on stratified subsets only (53 Store Item, 51 M5 series). Full references: research paper.");
stat(s, 4.6, 5.3, 3.6, "108", "fold runs, all independently reconciled", HEX.blue);
stat(s, 8.6, 5.3, 4.0, "45.2 M", "validation forecasts checked (45,177,440)", HEX.aqua);

// ------------------------------------------------------------------ 11 Validation results (native line charts)
pres.addSection({ title: "Results" });
s = slide("CONTENT", "Results", "Validation: clear lead on Store Item, narrow lead on M5",
  "These are the frozen candidates at the four validation origins. On Store Item, LightGBM is lowest at every origin, around 6.3 units per day, against 9.2 for seasonal naive. Interestingly, tuning did not improve LightGBM: its initial configuration stayed best. On M5 the lines almost touch: the random forest is about 1.3% better than MA28 on average and lower at all four origins, yet MA28 still wins the majority of individual series at every origin. So on M5 the mean advantage is real but small.");
const vf = ev.validation_fold_mae;
const lineOpts = (title, min, max) => ({ ...chartBase, x: 0, y: 0, w: 0, h: 0, showTitle: true, title, showLegend: true, legendPos: "b",
  lineSize: 2, lineDataSymbolSize: 7, valAxisMinVal: min, valAxisMaxVal: max, valAxisLabelFormatCode: "0.00", catAxisTitle: "", showValue: false });
s.addChart(pres.charts.LINE, [
  { name: "LightGBM (selected)", labels: ["Origin 1", "Origin 2", "Origin 3", "Origin 4"], values: vf.store_item_lightgbm_00 },
  { name: "Holt-Winters", labels: ["Origin 1", "Origin 2", "Origin 3", "Origin 4"], values: vf.store_item_holt_winters_additive_01 },
  { name: "Seasonal naive", labels: ["Origin 1", "Origin 2", "Origin 3", "Origin 4"], values: vf.store_item_seasonal_naive_reference },
], { ...lineOpts("Store Item: macro MAE", 5.5, 10.5), x: 0.6, y: 1.4, w: 6.0, h: 4.9, chartColors: [HEX.blue, HEX.violet, HEX.aqua], valAxisLabelFormatCode: "0.0" });
s.addChart(pres.charts.LINE, [
  { name: "Random forest (selected)", labels: ["Origin 1", "Origin 2", "Origin 3", "Origin 4"], values: vf.m5_random_forest_02 },
  { name: "MA28", labels: ["Origin 1", "Origin 2", "Origin 3", "Origin 4"], values: vf.m5_moving_average_28_reference },
  { name: "TSB", labels: ["Origin 1", "Origin 2", "Origin 3", "Origin 4"], values: vf.m5_tsb_01 },
], { ...lineOpts("M5: macro MAE", 0.98, 1.06), x: 6.75, y: 1.4, w: 6.0, h: 4.9, chartColors: [HEX.blue, HEX.orange, HEX.violet], valAxisLabelFormatCode: "0.000" });
source(s, "Source: frozen_selection.json fold MAE. M5 seasonal naive (about 1.21) omitted for scale. Origins are adjacent, not independent replications.");

// ------------------------------------------------------------------ 12 Final holdout
s = slide("CONTENT", "Results", "Final holdout: large gain on Store Item, marginal on M5",
  "This is the single final assessment on the sealed window. On Store Item the selected LightGBM achieved a mean absolute error of 5.43 units per day against 12.81 for seasonal naive: a 57.6 percent reduction. On M5 the selected random forest achieved 1.047 against 1.066 for MA28: only 1.7 percent. The selections were not changed after seeing these results, and on both datasets the frozen choice also happened to have the lowest final MAE among the predeclared candidates. That answers RQ1 and RQ3: machine learning ranked first on both, but the size of the gain did not transfer.");
const fh = ev.final_holdout;
s.addChart(pres.charts.BAR, [{ name: "Final macro MAE", labels: ["LightGBM (selected)", "Holt-Winters", "Seasonal naive", "Seasonal MA"],
  values: ["store_item_lightgbm_00", "store_item_holt_winters_additive_01", "store_item_seasonal_naive_reference", "store_item_seasonal_moving_average_reference"].map((k) => fh.store_item[k].macro_mae) }],
{ ...chartBase, x: 0.6, y: 1.4, w: 4.6, h: 3.4, barDir: "bar", showTitle: true, title: "Store Item: final macro MAE", showLegend: false, showValue: true, dataLabelPosition: "outEnd", valAxisMinVal: 0,
  dataLabelFormatCode: "0.000", chartColors: [HEX.blue, HEX.violet, HEX.aqua, "E87BA4"], valAxisHidden: true, valGridLine: { style: "none" }, catAxisOrientation: "maxMin", barGapWidthPct: 60 });
s.addChart(pres.charts.BAR, [{ name: "Final macro MAE", labels: ["Random forest (selected)", "TSB", "MA28", "Seasonal naive"],
  values: ["m5_random_forest_02", "m5_tsb_01", "m5_moving_average_28_reference", "m5_seasonal_naive_reference"].map((k) => fh.m5[k].macro_mae) }],
{ ...chartBase, x: 5.4, y: 1.4, w: 4.6, h: 3.4, barDir: "bar", showTitle: true, title: "M5: final macro MAE", showLegend: false, showValue: true, dataLabelPosition: "outEnd", valAxisMinVal: 0,
  dataLabelFormatCode: "0.000", chartColors: [HEX.blue, HEX.violet, HEX.orange, HEX.aqua], valAxisHidden: true, valGridLine: { style: "none" }, catAxisOrientation: "maxMin", barGapWidthPct: 60 });
stat(s, 10.3, 1.45, 2.6, "−57.6%", "Store Item MAE vs seasonal naive", HEX.blue);
stat(s, 10.3, 3.25, 2.6, "−1.7%", "M5 MAE vs MA28", HEX.orange);
card(s, 0.6, 5.0, 12.1, 1.45, "Read with care", "One 28-day window per dataset; no significance claim; selections frozen before the read and never revised. 812 M5 series had zero sales in the window (WAPE undefined, kept in MAE).", HEX.red, { size: 14 });
source(s, "Source: artifacts/experiments/phase4/final_metrics/*.json (SHA-256 verified). Store Item 2017-12-04 to 2017-12-31; M5 2016-04-25 to 2016-05-22.");

// ------------------------------------------------------------------ 13 Metric dependence
s = slide("CONTENT", "Results", "On M5 the ranking depends on the metric",
  "Here every bar is the percentage difference from MA28 on the final holdout, so below zero is better. The random forest wins on MAE, RMSE, WAPE and RMSSE, but it loses on macro MASE, where both MA28 and TSB are better. Scaled metrics change how much each series counts. I kept the predeclared primary metric and did not switch metrics after seeing results; instead I report all of them. On the saved per-series errors the forest wins 51.3 percent of series, a different pattern from validation, which again warns against strong claims on M5.");
const rel = ev.m5_relative_to_ma28;
const mlabels = ["MAE (primary)", "Pooled RMSE", "Pooled WAPE", "Macro MASE", "Macro RMSSE"];
const relKeys = ["Macro MAE (primary)", "Pooled RMSE", "Pooled WAPE", "Macro MASE", "Macro RMSSE"];
s.addChart(pres.charts.BAR, [
  { name: "Random forest (selected)", labels: mlabels, values: relKeys.map((k) => +rel.m5_random_forest_02[k].toFixed(2)) },
  { name: "TSB", labels: mlabels, values: relKeys.map((k) => +rel.m5_tsb_01[k].toFixed(2)) },
], { ...chartBase, x: 0.6, y: 1.4, w: 8.3, h: 5.0, barDir: "col", barGrouping: "clustered", showTitle: true, title: "% difference vs MA28 (negative = better)",
  showLegend: true, legendPos: "b", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.00;-0.00", chartColors: [HEX.blue, HEX.violet],
  valAxisMinVal: -2.5, valAxisMaxVal: 2.5, valAxisLabelFormatCode: "0.0" });
card(s, 9.2, 1.4, 3.5, 5.0, "What it means", "RF is better on four of five metrics but worse than MA28 and TSB on macro MASE (1.637 vs 1.611 and 1.625). On intermittent demand a 28-day mean is already near the best point forecast for many series.", HEX.orange, { size: 14 });
source(s, "Source: final_metrics/*.json. Seasonal naive (12% to 30% worse than MA28 on every metric) omitted for scale.");

// ------------------------------------------------------------------ 14 Inventory design
pres.addSection({ title: "Inventory" });
s = slide("CONTENT", "Inventory", "Inventory simulation: a hypothetical, audited what-if",
  "To answer RQ4 I built a deterministic, periodic-review, lost-sales simulator and ran it on the saved validation sales with the saved fixed-origin forecasts, never the final holdout. Three forecast-driven policies share an order-up-to rule; a fourth is a fixed reorder-point comparator. Every assumption was frozen before any result. Costs are in normalised cost units, NCU, not currency, and I never call differences savings. The simulation covered 544 cases on the full populations, 8.4 million series-episodes, and its arithmetic was independently replayed; in the final audit I re-aggregated every base result from the raw outputs with zero discrepancy.");
stat(s, 0.6, 1.5, 3.8, "544", "cases: 2 datasets × 4 origins × 4 policies × 17 scenarios", HEX.navy);
stat(s, 4.75, 1.5, 3.8, "8.43 M", "series-episodes simulated (8,429,280), full populations", HEX.blue);
stat(s, 8.9, 1.5, 3.8, "0.0", "discrepancy when re-aggregated from raw outputs in the final audit", HEX.aqua);
card(s, 0.6, 3.9, 3.9, 2.5, "Policies", "Order-up-to with Selected ML, MA28 or seasonal-naive forecasts; fixed reorder-point comparator.", HEX.blue, { size: 14 });
card(s, 4.7, 3.9, 3.9, 2.5, "Base assumptions", "Lead 7 days, review daily, buffer 3 mean-days, initial cover 7 days; lost sales; unlimited supply.", HEX.violet, { size: 14 });
card(s, 8.8, 3.9, 3.9, 2.5, "Costs (NCU)", "Holding 1 per unit-day, unmet 10 per unit, 1 per order. Hypothetical units, not prices or savings.", HEX.orange, { size: 14 });

// ------------------------------------------------------------------ 15 Inventory by origin
s = slide("CONTENT", "Inventory", "Better forecasts did not reliably lower simulated cost",
  "Each bar is Selected ML minus a baseline at one origin, so below zero means ML was cheaper. On Store Item, ML is cheaper than MA28 at the first three origins but costlier at origin 4, even though it is more accurate there; 473 of 500 series cost more. Against the stronger seasonal-naive baseline the pooled advantage is only 1.1 percent and it reverses at origin 3. On M5 the more accurate random forest is costlier than MA28 at all four origins, though cheaper than seasonal naive. The reason is that an order-up-to policy reacts to the forecast level, not just its error.");
const inv = ev.inventory_ml_minus_reference_by_origin;
const oL = ["Origin 1", "Origin 2", "Origin 3", "Origin 4"];
const invChart = (ds, title, x, fmt, min, max, unit) => s.addChart(pres.charts.BAR, [
  { name: "ML minus MA28", labels: oL, values: inv[ds].moving_average_28.map((v) => +v.toFixed(2)) },
  { name: "ML minus seasonal naive", labels: oL, values: inv[ds].seasonal_naive.map((v) => +v.toFixed(2)) },
], { ...chartBase, x, y: 1.4, w: 6.0, h: 4.75, barDir: "col", barGrouping: "clustered", showTitle: true, title, showLegend: true, legendPos: "b",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: fmt, chartColors: [HEX.orange, HEX.aqua], valAxisMinVal: min, valAxisMaxVal: max, valAxisMajorUnit: unit });
invChart("store_item", "Store Item: NCU per series-episode", 0.6, "+0;-0", -1000, 500, 250);
invChart("m5", "M5: NCU per series-episode", 6.75, "+0.00;-0.00", -20, 5, 5);
source(s, "Pooled: Store Item ML−MA28 −376.14 (−5.86%), ML − seasonal naive −67.27 (−1.10%); M5 ML−MA28 +1.90 (+0.85%), ML − seasonal naive −11.01 (−4.69%). Hypothetical NCU, not savings.");

// ------------------------------------------------------------------ 16 Cost vs service
s = slide("CONTENT", "Inventory", "The cheapest rule simply holds less stock and serves less",
  "The fixed reorder point has the lowest cost on both datasets, and it would be easy to call it the winner. The audit showed why that is wrong: on Store Item it orders at essentially every review because its inventory position never reaches the trigger, so it behaves like replenishing one day of demand per day. It holds about half the stock and has lower fill. On M5 its fill rate is about four points lower. I therefore report it as a low-stock, lower-service comparator, not as a better policy. A properly tuned (s, S) policy is listed as future work.");
const pooled = ev.inventory_pooled;
const pols = ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"];
const polL = ["Selected ML", "MA28", "Seasonal naive", "Fixed ROP"];
const tbl = [["Policy", "Store Item cost (NCU)", "Store Item fill", "M5 cost (NCU)", "M5 fill"]].concat(pols.map((p, i) => [polL[i],
  pooled.store_item[p].mean_cost.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }), (100 * pooled.store_item[p].pooled_fill_rate).toFixed(2) + "%",
  pooled.m5[p].mean_cost.toFixed(2), (100 * pooled.m5[p].pooled_fill_rate).toFixed(2) + "%"]));
s.addTable(tbl.map((r, i) => r.map((c, j) => ({ text: c, options: { bold: i === 0 || j === 0, color: i === 0 ? HEX.white : "0B0B0B", align: j === 0 ? "left" : "right",
  fill: { color: i === 0 ? HEX.navy : (i === 4 ? "FDF3DC" : (i % 2 ? HEX.white : HEX.tint)) }, fontSize: 15 } }))),
  { x: 0.6, y: 1.5, w: 7.6, colW: [1.8, 1.6, 1.35, 1.5, 1.35], rowH: 0.55, border: { type: "solid", pt: 0.5, color: "D0D5DD" }, valign: "middle" });
card(s, 8.5, 1.5, 4.2, 2.8, "Fixed ROP behaviour", "Store Item: orders at 99.9% of reviews; its inventory position (7.3 mean-days) never rises above the 11-day reorder point. Fill below ML in 15 of 17 Store Item and 17 of 17 M5 scenarios.", HEX.yellow, { size: 14 });
card(s, 0.6, 4.65, 12.1, 1.75, "Sensitivity (17 scenarios)", "They reuse the same four origins and forecasts, so they are not independent confirmations: Store Item ML beats MA28 in 17 of 17 pooled scenarios but only 52 of 68 scenario-origin cells. On M5, ML beats MA28 in only 3 of 17.", HEX.violet, { size: 14 });
source(s, "Source: reports/inventory/post_audit_reconciliation.json (base, pooled over four origins).");

// ------------------------------------------------------------------ 17 Limitations
s = slide("CONTENT", "Inventory", "Scientific limitations",
  "I want to be explicit about what this evidence cannot support. Sales are censored: a zero may be a stock-out rather than no demand. The inventory study reuses the validation windows that selected the ML models, which biases it in favour of ML; I cannot quantify that bias because the holdout is spent, which is why the M5 result, where ML still was not cheaper, is the more informative one. Four adjacent origins and correlated series do not support significance tests. Costs are hypothetical. And the results come from two public histories, so I make no claim of a universal ranking.");
const lim = [["Censored demand", "Sales understate demand when stock runs out; lost sales are assumed, not observed.", HEX.red],
  ["Selection optimism", "Inventory reuses the windows that selected ML; the bias favours ML and is unquantifiable.", HEX.orange],
  ["Limited seasons", "Four adjacent origins plus one final window; no significance testing.", HEX.yellow],
  ["Hypothetical costs", "NCU and frozen assumptions; no realised savings or prices.", HEX.violet],
  ["Small ML samples", "Six training labels per M5 series per origin; bounded compute.", HEX.blue],
  ["External validity", "Two public datasets; no claim of universal ranking or transfer.", HEX.aqua]];
lim.forEach(([h, b, c], i) => card(s, 0.6 + (i % 3) * 4.1, 1.45 + Math.floor(i / 3) * 2.55, 3.85, 2.3, h, b, c, { size: 14 }));

// ------------------------------------------------------------------ 18 Application architecture
pres.addSection({ title: "Application" });
s = slide("CONTENT", "Application", "Application architecture",
  "The research is delivered as a public application. The browser talks only to the Next.js web app on Vercel. The web app reads evidence from Supabase PostgreSQL through a read-only role and calls a separate FastAPI service that wraps the byte-identical frozen Phase 5 engine. That engine is protected: it accepts requests only with a shared key and Vercel's protection bypass, and anonymous requests get 401. Crucially, the user can never send demand data: the engine loads saved sales and forecasts itself, so the app can only run the verified simulator on approved inputs.");
s.addImage({ path: img("final_submission/figures/fig_architecture.png"), x: 0.6, y: 1.35, w: 8.6, h: 4.07 });
card(s, 9.45, 1.35, 3.25, 4.07, "Security by design", "No credentials in the browser; read-only database roles; protected engine; validation and rate limiting; generic errors; security headers and HSTS.", HEX.blue, { size: 14 });
card(s, 0.6, 5.55, 12.1, 1.3, "Stack", "Next.js 16 · FastAPI (Python 3.14) · Supabase PostgreSQL 17 · Vercel (Frankfurt) · Power BI report from the same evidence.", HEX.aqua, { size: 13 });

// ------------------------------------------------------------------ 19 Live demo
s = slide("CONTENT", "Application", "Live demonstration: idf-web.vercel.app",
  "DEMO SCRIPT (about four minutes). One: open idf-web.vercel.app on the Executive Overview and point out the three evidence labels: validated, reported and hypothetical. Two: open the Forecast Explorer, choose a Store Item series and origin, and show the 28-day forecasts of the three models against actual sales. Three: click through to the Inventory Planner with that series, run the base scenario and show that the four totals equal the saved Phase 5 values in the comparison column. Four: change the lead time to 3 and the unmet-demand penalty to 25, run again, and note that the page labels it a custom hypothetical scenario. Five: open Scenario Comparison to show the origin-4 reversal. Six: end on the Research page, which lists limitations and the sealed holdout. Fallback if the network fails: use the screenshots on appendix slide 24 or the Power BI report.");
s.addImage({ path: img("final_submission/screenshots/planner_totals.png"), x: 0.6, y: 1.6, w: 6.5, h: 1.93 });
text(s, "Live engine totals (left) equal the saved Phase 5 totals (right) for this series and origin.", { x: 0.6, y: 3.65, w: 6.5, h: 0.5, fontSize: 13, color: HEX.ink2, italic: true });
s.addImage({ path: img("final_submission/screenshots/overview_top.png"), x: 0.6, y: 4.25, w: 3.2, h: 2.15 });
s.addImage({ path: img("final_submission/screenshots/forecasts_top.png"), x: 3.9, y: 4.25, w: 3.2, h: 2.15 });
const demo = ["Executive Overview: evidence labels and headline results", "Forecast Explorer: one series, three models vs actuals", "Inventory Planner: base run equals saved Phase 5 totals",
  "Custom scenario: lead 3 days, penalty 25 NCU", "Scenario Comparison: Store Item origin-4 reversal", "Research: protocol, audit and limitations"];
s.addText(demo.map((d, i) => ({ text: d, options: { bullet: { type: "number" }, breakLine: i < demo.length - 1 } })),
  { x: 7.3, y: 1.45, w: 5.4, h: 4.2, fontSize: 16, color: HEX.ink2, paraSpaceAfter: 10, valign: "top", isTextBox: true, margin: 0 });
text(s, "Fallback if the network fails: Appendix slide 24 and the Power BI report.", { x: 7.3, y: 5.8, w: 5.4, h: 0.6, fontSize: 13, italic: true, color: HEX.ink2 });

// ------------------------------------------------------------------ 20 Production verification
s = slide("CONTENT", "Application", "Production verification",
  "Before calling the deployment done I verified it against the local reference. All 21 API responses I compared, including three simulations and the CSV export, were byte-identical. Getting there required fixing two real defects. First, Supabase rounds floating-point text to 15 digits, which silently changed integer inventory results for 182 of 3,200 series-origin pairs; requiring exact parity is what exposed it, and it was fixed in both the engine and the web API. Second, a TLS option in the database connection string was being forwarded to the server and rejected; it is now applied on the client. Three things were not tested in production, and I do not claim them: a real engine outage, a real database outage and protection of a built preview deployment.");
stat(s, 0.6, 1.5, 3.8, "21 / 21", "API responses byte-identical to the local reference", HEX.blue);
stat(s, 4.75, 1.5, 3.8, "2,555", "NCU: Selected ML total for the reference series through the production stack (MA28 2,772; seasonal naive 2,900; fixed ROP 1,309), equal to Phase 5", HEX.navy);
stat(s, 8.9, 1.5, 3.8, "15 / 15", "page × width browser checks: no overflow, no serious accessibility issue", HEX.aqua);
card(s, 0.6, 3.95, 5.9, 2.45, "Defects found and fixed", "Float rounding: Supabase's extra_float_digits = 0 changed results for 182 of 3,200 pairs (fixed with binary floats and exact-output transactions). TLS: a connection option rejected by the server, now applied client-side.", HEX.orange, { size: 14 });
card(s, 6.8, 3.95, 5.9, 2.45, "Not tested in production", "Real engine outage; real database outage or pause; protection of a built preview deployment. Covered by local tests only.", HEX.red, { size: 14 });

// ------------------------------------------------------------------ 21 Contributions
pres.addSection({ title: "Conclusion" });
s = slide("CONTENT", "Conclusion", "Research contributions",
  "To summarise the contributions. First, a governed benchmark: a frozen, fingerprinted selection evaluated once on a sealed holdout. Second, full-population evaluation on all 30,490 M5 series, rather than a convenient subset. Third, an honest decision analysis that shows where machine learning does not help, under explicit assumptions. Fourth, reproducibility: hashes, manifests, independent recomputation, and an audit trail. And fifth, a deployed application that serves exactly the recorded evidence.");
const contrib = [["Governed benchmark", "Frozen, fingerprinted selection; sealed holdout read once.", HEX.navy], ["Full populations", "All 500 and 30,490 series; no convenient subsets for claims.", HEX.blue],
  ["Decision-aware analysis", "Accuracy versus cost and service, reported where ML does not help.", HEX.orange], ["Reproducibility", "Hashes, manifests, exact recomputation, independent audit.", HEX.aqua],
  ["Deployed evidence", "Public app serving byte-identical evidence (curated series) and the frozen engine.", HEX.violet]];
contrib.forEach(([h, b, c], i) => card(s, 0.6 + (i % 3) * 4.1, 1.45 + Math.floor(i / 3) * 2.55, 3.85, 2.3, h, b, c, { size: 14 }));
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.8, y: 4.0, w: 3.85, h: 2.3, rectRadius: 0.08, fill: { color: HEX.navy }, line: { color: HEX.navy } });
text(s, "Limits are part of the result", { x: 9.05, y: 4.25, w: 3.4, h: 1.8, fontSize: 20, bold: true, color: HEX.white, fontFace: "Cambria", valign: "middle" });

// ------------------------------------------------------------------ 22 Conclusions
s = slide("DARK", "Conclusion", "Conclusions and future work",
  "In conclusion: machine learning gave a large forecasting gain on regular retail demand and only a marginal, metric-dependent gain on intermittent demand, and better accuracy did not reliably lower simulated inventory cost. For future work, the most valuable step is a fresh, untouched evaluation window, which would remove the selection optimism of the inventory study. After that: a tuned (s, S) policy with service targets, explicit censored-demand modelling, verified price and event features, probabilistic forecasts for safety stock, and a clean-machine reproduction.");
s.addText("ML: −57.6% MAE on regular Store Item demand; −1.7% on intermittent M5, and worse on MASE. Accuracy did not reliably lower simulated cost.", { placeholder: "body" });
text(s, "Next: a fresh evaluation window · tuned (s, S) policy with service targets · censored-demand models · verified price and event features · probabilistic forecasts · clean-machine reproduction",
  { x: 0.8, y: 5.75, w: 11.7, h: 0.9, fontSize: 15, color: HEX.white });

// ------------------------------------------------------------------ 23 Thanks
s = slide("DARK", "Conclusion", "Thank you. Questions?",
  "Thank you. I am happy to take questions. Likely questions and short answers: Why price-free? Publication latency of prices was unverified, so using them risked leakage. Why is Fixed ROP cheapest? It holds less stock and serves less; it is a degenerate comparator. Is the 57.6% significant? I make no significance claim: it is one window, but the direction was consistent across all four validation origins. Why not tune more? The holdout is spent; any new model could only be compared on reused windows.");
s.addText("Live application: https://idf-web.vercel.app  ·  Evidence, code and audit trail available to examiners on request", { placeholder: "body" });

pres.addSection({ title: "Appendix" });
s = slide("CONTENT", "Appendix", "Appendix: the deployed application (production, 2026-11-12)",
  "Backup slide for the live demonstration. If the network or the Supabase project is unavailable, walk through these production screenshots in the same order as the demo script: Executive Overview, Forecast Explorer, Inventory Planner, Scenario Comparison.");
const shots = [["overview_top.png", "Executive Overview"], ["forecasts_top.png", "Forecast Explorer"], ["planner_top.png", "Inventory Planner"], ["scenarios_top.png", "Scenario Comparison"]];
shots.forEach(([f, label], i) => {
  const x = 0.6 + (i % 2) * 6.15, y = 1.35 + Math.floor(i / 2) * 2.75;
  s.addImage({ path: img("final_submission/screenshots/" + f), x, y, w: 3.45, h: 2.32 });
  text(s, label, { x: x + 3.6, y: y + 0.1, w: 2.3, h: 0.5, fontSize: 15, bold: true, color: HEX.navy });
});
source(s, "Screenshots from https://idf-web.vercel.app at 1280 px width, captured during production QA (reports/webapp/phase7d/browser_prod).");

pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, "slides", n);
});
