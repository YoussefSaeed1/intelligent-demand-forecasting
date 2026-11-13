// Builds the Phase 8 research paper (.docx). Every project number is taken from verified evidence
// (see final_submission/02_traceability/EVIDENCE_TO_CLAIM_TRACEABILITY.md). Run with the docx package available:
//   node final_submission/_tools/build_paper.js <docx-module-dir>
const path = require("path");
const fs = require("fs");
const modDir = process.argv[2];
const D = require(path.join(modDir, "docx"));
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
  ShadingType, BorderStyle, ImageRun, PageBreak, TableOfContents, Footer, Header, PageNumber, LevelFormat,
  TabStopType,
} = D;

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = (p) => path.join(ROOT, p);
const OUT = path.join(ROOT, "final_submission", "03_paper", "IDF_Research_Paper.docx");
fs.mkdirSync(path.dirname(OUT), { recursive: true });

const FONT = "Times New Roman";
const PAGE_W = 11906, MARGIN = 1304; // A4, 23 mm margins
const TEXT_W = PAGE_W - 2 * MARGIN;   // 9298 DXA

// ---------------------------------------------------------------- numbering registry for cross-references
const reg = { fig: [], tab: [] };
const FIGS = ["classes", "calendar", "price", "design", "validation", "final", "metric", "costfill", "inventory", "arch", "app"];
const TABS = ["data", "classes", "features", "folds", "phase3", "phase4", "config", "final", "inv_pool", "inv_origin", "rop", "sens", "qa", "threats", "metrics", "audit"];
FIGS.forEach((k) => reg.fig.push(k));
TABS.forEach((k) => reg.tab.push(k));
const F = (k) => { const i = reg.fig.indexOf(k); if (i < 0) throw new Error("fig " + k); return `Figure ${i + 1}`; };
const T = (k) => { const i = reg.tab.indexOf(k); if (i < 0) throw new Error("tab " + k); return `Table ${i + 1}`; };

// ---------------------------------------------------------------- inline markup: **bold**, *italic*
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const s = m[0];
    if (s.startsWith("**")) out.push(new TextRun({ text: s.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: s.slice(1, -1), italics: true, ...base }));
    last = m.index + s.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (text, opts = {}) => new Paragraph({ children: runs(text), alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 300 }, ...opts });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: false });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (text) => new Paragraph({ children: runs(text), numbering: { reference: "bullets", level: 0 }, spacing: { after: 60, line: 288 }, alignment: AlignmentType.LEFT });
const N = (text) => new Paragraph({ children: runs(text), numbering: { reference: "numbers", level: 0 }, spacing: { after: 60, line: 288 } });
const EQ = (text) => new Paragraph({ children: [new TextRun({ text, font: "Cambria Math", size: 22 })], alignment: AlignmentType.CENTER, spacing: { before: 60, after: 120 } });
const BR = () => new Paragraph({ children: [new PageBreak()] });

const emitted = { fig: [], tab: [] };
function caption(kind, key, text) {
  emitted[kind].push(key);
  const label = kind === "fig" ? F(key) : T(key);
  return new Paragraph({
    children: [new TextRun({ text: label + ". ", bold: true, size: 20 }), ...runs(text, { size: 20 })],
    alignment: AlignmentType.LEFT, spacing: { before: kind === "fig" ? 60 : 200, after: kind === "fig" ? 240 : 80 },
    keepNext: kind === "tab",
  });
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function figure(key, file, text, widthIn = 6.4) {
  const full = FIG(file);
  const { w, h } = pngSize(full);
  const px = widthIn * 96;
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 0 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(full), transformation: { width: px, height: Math.round(px * h / w) },
        altText: { title: F(key), description: text.replace(/\*/g, ""), name: key } })],
    }),
    caption("fig", key, text),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "9A9893" };
function table(key, title, headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = TEXT_W / total;
  const w = widths.map((x) => Math.floor(x * scale));
  w[w.length - 1] += TEXT_W - w.reduce((a, b) => a + b, 0);
  const cell = (text, i, head) => new TableCell({
    width: { size: w[i], type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: "E4ECF7" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    borders: { top: border, bottom: border, left: border, right: border },
    children: [new Paragraph({
      children: runs(String(text), { size: opts.size || 18, bold: head || undefined }),
      alignment: i > 0 && (opts.right || []).includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      keepNext: rows.length <= 12,
    })],
  });
  return [
    caption("tab", key, title),
    new Table({
      width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: w,
      rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
        ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))],
    }),
    new Paragraph({ children: [], spacing: { after: 120 } }),
  ];
}

// ---------------------------------------------------------------- content
const body = [];
const add = (...xs) => xs.flat().forEach((x) => body.push(x));

// Title page
add(
  new Paragraph({ children: [], spacing: { before: 1800 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "Research Paper", size: 28, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 1000 }, children: [new TextRun({ text: "Research Project", size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [new TextRun({ text: "Intelligent Demand Forecasting and Inventory Optimisation", size: 44, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 1200 }, children: [new TextRun({ text: "A governed comparison of statistical and machine-learning forecasts on two retail datasets, with a hypothetical inventory simulation and a deployed research application", size: 26, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Youssef Saeed", size: 26, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Supervisor: ______________________", size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "November 2026", size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1400 }, children: [new TextRun({ text: "Live research application: https://idf-web.vercel.app", size: 20 })] }),
  BR(),
);

// Abstract
add(
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "Abstract", bold: true, size: 28 })] }),
  P("Retail replenishment depends on forecasts of daily demand that is noisy, seasonal and, for many products, intermittent. This project compares naive, statistical, intermittent-demand and global machine-learning forecasters on two public retail datasets under a single governed protocol, and then examines what the forecast differences would imply for inventory under explicitly assumed conditions. The Kaggle Store Item Demand dataset (500 store-item series, 913,000 daily observations, 2013 to 2017) is regular and strongly weekly-seasonal; the M5 Walmart dataset (30,490 series, 59,181,090 daily observations, 2011 to 2016) is dominated by intermittent and lumpy demand, with 68.8% zero observations in the training prefix. All full-population methods forecast 28 days ahead from four expanding validation origins (ARIMA and SARIMA only on stratified subsets), with a final 28-day holdout that was sealed, fingerprinted and evaluated exactly once after model selection was frozen."),
  P("On the final holdout the selected Store Item LightGBM model achieved a macro mean absolute error (MAE) of 5.434 units per day, 57.59% lower than seasonal naive (12.815). The selected price-free M5 random forest achieved 1.0472 against 1.0657 for a 28-day moving average (MA28), a reduction of only 1.74%, and it was worse than MA28 and the Teunter-Syntetos-Babai method on macro mean absolute scaled error: the M5 ranking depends on the metric. A deterministic lost-sales simulation of four replenishment policies over 544 cases and 8,429,280 series-episodes shows that forecast accuracy does not translate directly into lower cost. In hypothetical normalised cost units (NCU), selected-ML ordering was 376.14 NCU cheaper per series-episode than MA28 on Store Item, but the sign reversed at the last validation origin and the advantage over seasonal naive was 1.10%; on M5 it was costlier than MA28 at all four origins. These are simulated, validation-reused results, not realised savings."),
  P("The research evidence is delivered through a public Next.js application backed by a protected FastAPI simulation engine and a Supabase PostgreSQL database, whose 21 audited API responses are byte-identical to the local reference. The main contribution is methodological: a reproducible, leakage-controlled and honestly reported comparison in which the limits of the evidence are part of the result."),
  P("**Keywords:** demand forecasting; intermittent demand; LightGBM; random forest; rolling-origin evaluation; inventory simulation; reproducibility."),
  BR(),
  new Paragraph({ children: [new TextRun({ text: "Contents", bold: true, size: 28 })], spacing: { after: 160 } }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  BR(),
);

// 1 Introduction
add(
  H1("1. Introduction and problem statement"),
  P("Retailers decide every day how much stock to order for thousands of store-product combinations. Ordering too little loses sales and goodwill; ordering too much ties up capital and shelf space. Both errors originate partly in the forecast of future demand. Machine-learning forecasters are widely promoted as an improvement over simple rules, but published comparisons often differ in their data, horizon, evaluation windows and error measures, which makes claims of improvement hard to interpret (Tashman, 2000; Petropoulos et al., 2022)."),
  P("This project asks a narrower, testable question: under one fixed, leakage-controlled protocol, do machine-learning forecasters outperform naive and statistical baselines for 28-day daily retail forecasting, does the answer hold on a second, very different dataset, and what would the differences mean for replenishment under transparent assumptions? The datasets record **sales**, not demand, and contain no stock, order, lead-time or cost information. The inventory part is therefore a hypothetical simulation and is reported in normalised cost units (NCU) rather than currency."),
  P("The work was organised in governed phases: data acquisition and validation (Phase 1), training-prefix exploratory analysis and a frozen protocol (Phase 2), forecasting implementation (Phase 3), optimisation and a one-time final evaluation (Phase 4), an inventory simulation (Phase 5), a Power BI report (Phase 6) and a deployed research application (Phase 7). An independent technical audit of Phases 0 to 5 (a separate AI-assisted review, not an external human examination) returned a CONDITIONAL verdict with no critical or high findings; its reporting conditions govern how results are presented here (Section 12)."),
);

// 2 Objectives
add(
  H1("2. Research objectives and questions"),
  P("The project proposal defined four research questions:"),
  N("**RQ1.** How do naive, statistical and machine-learning approaches compare on the same daily horizons and evaluation windows?"),
  N("**RQ2.** Which data-quality and feature choices affect forecast reliability across series?"),
  N("**RQ3.** Does the relative ranking of methods hold on a second, independently sourced dataset?"),
  N("**RQ4.** How sensitive are simulated service and inventory-cost trade-offs to the forecast policy, lead time and assumed operating parameters?"),
  P("The corresponding objectives were to build documented ingestion, profiling and validation; to establish baselines; to perform systematic chronological tuning; to compare and interpret models; to retain reproducible evidence; and to investigate inventory implications without claiming observed savings. Causal business claims, reconstruction of actual stock and a live operational system were explicitly out of scope; the deployed application presents frozen research evidence and runs the frozen simulator on saved inputs."),
);

// 3 Related work
add(
  H1("3. Related work"),
  H2("3.1 Retail and large-scale forecasting"),
  P("Fildes, Ma and Kolassa (2022) review retail forecasting research and practice, emphasising the importance of hierarchy, promotions, intermittency and the gap between accuracy and decision value. The M5 competition, built on Walmart unit sales, provides the second dataset used here; Makridakis, Spiliotis and Assimakopoulos (2022a) describe its design and data, and the results paper (2022b) reports that machine-learning methods, notably LightGBM-based approaches, were prominent among the most accurate submissions. The present study does not reproduce the competition: it uses a common 28-day leaf-level task, its own windows and no official weighted scaled error."),
  H2("3.2 Statistical and intermittent-demand methods"),
  P("Exponential smoothing with trend and seasonality originates in the work of Holt (2004, reprinting a 1957 memorandum) and Winters (1960); Hyndman et al. (2002) placed these methods in a state-space framework. For intermittent demand, Croston (1972) proposed separate smoothing of demand sizes and inter-demand intervals; Syntetos and Boylan (2001) showed Croston's estimator to be biased, and Syntetos and Boylan (2005) proposed and evaluated a bias-corrected approximation (SBA); Teunter, Syntetos and Babai (2011) proposed updating the demand probability every period (TSB), which also handles obsolescence. Syntetos, Boylan and Croston (2005) introduced the average inter-demand interval (ADI) and squared coefficient of variation (CV²) categorisation with cut-offs of 1.32 and 0.49, used here descriptively."),
  H2("3.3 Machine learning and global models"),
  P("Random forests (Breiman, 2001) and gradient-boosted trees such as LightGBM (Ke et al., 2017) can learn non-linear relationships between lagged sales, calendar features and identifiers. Januschowski et al. (2020) distinguish local models, fitted per series, from global models fitted across series; Montero-Manso and Hyndman (2021) analyse why global models can perform well on groups of series. This project fits one global model per dataset and forecasts recursively, which exposes the model to its own errors over the 28-day horizon."),
  H2("3.4 Evaluation methodology"),
  P("Tashman (2000) reviews out-of-sample and rolling-origin evaluation; Bergmeir and Benítez (2012) examine cross-validation for time-series predictors; Hyndman and Athanasopoulos (2021) describe chronological cross-validation and simple benchmarks. Hyndman and Koehler (2006) proposed the mean absolute scaled error (MASE), which divides errors by an in-sample naive error and is defined across series with different scales. Scale-dependent and scaled measures can rank methods differently, a result observed on M5 in this project."),
  H2("3.5 Censored demand"),
  P("Sales data understate demand when stock-outs occur, because unmet demand is not recorded (Conrad, 1976). Because neither dataset records stock, this project cannot separate low demand from unavailability; it treats sales as a demand proxy and states this as a threat to validity."),
);

// 4 Data
add(
  H1("4. Datasets and data preparation"),
  P(`Both datasets were acquired through the official Kaggle client and converted to one canonical daily schema (dataset, date, store, item, sales) with unique business keys enforced on write. Raw CSV and canonical Parquet hashes are recorded; all nine files were re-hashed during the final audit and are unchanged. ${T("data")} summarises the two sources over the exploratory training prefix.`),
  ...table("data", "Dataset characteristics (exploratory training prefix unless stated). Source: docs/EDA_FINDINGS.md.",
    ["Characteristic", "Store Item", "M5"],
    [["Full verified history", "2013-01-01 to 2017-12-31", "2011-01-29 to 2016-05-22"],
      ["Full daily observations", "913,000", "59,181,090"],
      ["Stores / products / series", "10 / 50 / 500", "10 / 3,049 / 30,490"],
      ["Exploratory prefix (dates)", "2013-01-01 to 2017-08-13", "2011-01-29 to 2016-01-03"],
      ["Zero observations in prefix", "1 (0.0001%)", "37,800,354 (68.84%)"],
      ["Median / 99th percentile / maximum daily units", "46 / 134 / 231", "0 / 15 / 763"],
      ["Median per-series coefficient of variation", "0.288", "2.080"],
      ["Share of units from top 10% of products", "16.28%", "51.68%"],
      ["Price field", "None", "Weekly prices; 12,299,413 missing over the full history (20.78%)"]],
    [3.2, 2.6, 3.0]),
  P("Data quality checks found no missing dates, duplicate keys or missing targets. The single Store Item zero (store 6, item 4, 2014-01-15) and all extreme values were preserved after confirmation against the source files. M5 missing prices were left missing: every missing price in the exploratory prefix coincides with zero recorded sales, almost all before a product's first positive sale, which is consistent with late product introduction. Store Item's competition test file has no labels and was never used as a target source; M5's validation and evaluation sales files overlap and were treated as one history."),
);

// 5 EDA
add(
  H1("5. Exploratory data analysis"),
  P(`Exploratory analysis used only the training prefix, so that validation and final-test behaviour could not influence design choices. ${T("classes")} and ${F("classes")} show that the two datasets differ fundamentally in demand pattern under the ADI/CV² scheme of Syntetos, Boylan and Croston (2005).`),
  ...table("classes", "Demand-pattern classes over the exploratory prefix (ADI cut-off 1.32, CV² cut-off 0.49).",
    ["Class", "Store Item series", "M5 series", "M5 share"],
    [["Smooth", "500", "983", "3.22%"], ["Erratic", "0", "489", "1.60%"], ["Intermittent", "0", "23,044", "75.58%"],
      ["Lumpy", "0", "5,953", "19.52%"], ["All zero", "0", "16", "0.05%"], ["Insufficient positive history", "0", "5", "0.02%"]],
    [3.2, 2, 2, 2], { right: [1, 2, 3] }),
  ...figure("classes", "reports/figures/phase2/m5_classification.png", "M5 demand classes on a logarithmic scale, with exact counts and shares (Phase 2 figure)."),
  P(`Store Item has strong and stable calendar structure (${F("calendar")}). Relative to each week's mean, Sunday sales are 1.192 (pointwise block-bootstrap 95% interval 1.187 to 1.196) and Monday sales 0.791 (0.788 to 0.795); the weekly robust STL strength on log aggregate sales is 0.976. M5 has a weaker aggregate weekly strength (0.109) because large calendar effects, for example near-zero sales on Christmas, dominate the residual, although weekday contrasts are stable (Saturday 1.210, Wednesday 0.875). Median per-series lag-7 autocorrelations are 0.728 for Store Item and 0.175 for M5.`),
  ...figure("calendar", "reports/figures/phase2/store_item_calendar_patterns.png", "Store Item weekly and annual calendar structure over the exploratory prefix (Phase 2 figure)."),
  P(`M5 price coverage improves over time (${F("price")}): missing prices fall from 5,167,100 in partial 2011 to 513 in partial 2016. Because the publication latency of prices could not be verified, every model in the final comparison is price-free. These observations motivated the candidate families: seasonal and smoothing baselines and global ML for regular Store Item demand; intermittent-demand methods and global ML for M5, with all scores reported by training-period demand class.`),
  ...figure("price", "reports/figures/phase2/m5_price_missingness.png", "M5 historical price coverage by year and activity (Phase 2 figure)."),
);

// 6 Methodology
add(
  H1("6. Forecasting methodology"),
  H2("6.1 Task and horizon"),
  P("For every series, each method predicts expected daily unit sales for the next 28 calendar days from a forecast origin, without using any actual sales inside the forecast window. Four complete weeks give each weekday equal exposure. Forecasts are not rounded, are clipped below at zero, and every model must deliver a forecast for every series; a predeclared seasonal-naive fallback (zero for an all-zero history) covers fitting failures and is counted. No fallback was needed in the final assessment."),
  H2("6.2 Models"),
  P("Baselines were the zero forecast, naive (last value), weekly seasonal naive, 28-day moving average (MA28) and a seasonal moving average. Statistical comparators were simple exponential smoothing, Holt, additive Holt-Winters, ARIMA(1,0,0) and SARIMA(1,0,0)(1,0,0)7 on a reproducible stratified subset only, and the intermittent methods Croston, SBA and TSB. Machine-learning comparators were a global random forest (scikit-learn; Pedregosa et al., 2011) and a global LightGBM regressor (Ke et al., 2017), each fitted separately per dataset as a one-step model and applied recursively for 28 steps."),
  H2("6.3 Features and information availability"),
  P(`${T("features")} lists the feature contract of the final models. Every feature for a label at date t uses only observations strictly before t; during recursion, lag and rolling features are recomputed from the model's own clipped predictions, while occurrence statistics are frozen at the origin so that predictions are never treated as observed sales. Tests poison future targets and all prices to prove that the final price-free forecasts cannot depend on them.`),
  ...table("features", "Feature groups of the Phase 4 global ML models (27 Store Item and 30 M5 encoded columns). Source: docs/PHASE4_FEATURE_AVAILABILITY.md.",
    ["Feature group", "Information used", "During the 28-step recursion"],
    [["Sales lags 1, 7, 14, 28, 56", "Observed sales strictly before the label date", "Observed through the origin, then own clipped predictions"],
      ["Rolling means (7, 28, 56) and standard deviations (7, 28)", "Shifted historical sales", "Recomputed from the evolving recursive state"],
      ["Zero fractions, positive count, ADI, positive CV², age of last positive sale", "Observed sales strictly before the label date", "Frozen at the origin"],
      ["Calendar: weekday, day, month, weekend, weekly and annual sine/cosine, elapsed days", "Deterministic target date", "Known in advance"],
      ["Store and item codes; M5 category, department and state codes", "Fixed benchmark identifiers", "Unchanged frozen encoder"],
      ["Prices, events, SNAP", "Publication latency unverified", "Excluded"]],
    [3.2, 3, 3.2]),
);

// 7 Protocol
add(
  H1("7. Experimental protocol"),
  P(`The evaluation design is chronological and date-only (${T("folds")}, ${F("design")}). Training starts at the first labelled date and expands: each origin uses all observations up to and including the origin date, and the 28 target days begin the next day. Validation windows do not overlap, and every compared method is scored on identical series and dates. The four origins are adjacent, so they describe variability over a limited seasonal range rather than four independent replications.`),
  ...table("folds", "Forecast origins and target windows. Source: reports/eda/proposed_splits.json.",
    ["Window", "Store Item origin", "Store Item targets", "M5 origin", "M5 targets"],
    [["Validation 1", "2017-08-13", "2017-08-14 to 2017-09-10", "2016-01-03", "2016-01-04 to 2016-01-31"],
      ["Validation 2", "2017-09-10", "2017-09-11 to 2017-10-08", "2016-01-31", "2016-02-01 to 2016-02-28"],
      ["Validation 3", "2017-10-08", "2017-10-09 to 2017-11-05", "2016-02-28", "2016-02-29 to 2016-03-27"],
      ["Validation 4", "2017-11-05", "2017-11-06 to 2017-12-03", "2016-03-27", "2016-03-28 to 2016-04-24"],
      ["Final holdout", "2017-12-03", "2017-12-04 to 2017-12-31", "2016-04-24", "2016-04-25 to 2016-05-22"]],
    [1.6, 1.6, 2.4, 1.6, 2.4]),
  ...figure("design", "final_submission/figures/fig_rolling_origin.png", "Expanding-origin design: training history (light), validation windows (blue) and the final holdout (red), evaluated once."),
  H2("7.1 Metrics and aggregation"),
  P(`With error e = forecast minus actual, the project reports MAE, RMSE, WAPE, signed bias, MASE and RMSSE (definitions in Appendix A, ${T("metrics")}). Macro measures average per-series values, giving each series equal weight; pooled measures aggregate all errors first. MASE and RMSSE are scaled by the in-sample weekly seasonal-naive error of each series (Hyndman and Koehler, 2006). Undefined values, such as WAPE for a series with no sales in the window or a scaled error with a zero scale, are kept undefined and counted, never replaced by zero or an epsilon. The leaf-level weekly RMSSE is not the official hierarchical M5 WRMSSE.`),
  H2("7.2 Selection and the sealed final holdout"),
  P("The primary selection objective, declared before scoring, was the mean over the four validation origins of macro MAE, separately per dataset. Phase 4 evaluated 27 configurations, of which 23 were seed-42 random-search tuning trials (12 Store Item: six LightGBM, three random forest and three Holt-Winters; 11 M5: four random forest, three LightGBM and four TSB) and four were unchanged references, giving 108 fold runs and 45,177,440 validation forecasts, all independently reconciled. ML training used outcome-independent stratified samples of 300 labels per Store Item series and six per M5 series per origin."),
  P("The selection was then frozen in a manifest whose SHA-256 fingerprint (a71ab187…) covers the chosen models, features, comparators and 89 source and configuration files. All eight final forecast bundles (3,470,880 forecasts) were sealed before the first holdout read, and each dataset's holdout was read once, as recorded in a 12-event hash-chained access ledger. The final result was not used to change any selection."),
);

// 8 Results
add(
  H1("8. Results and model comparison"),
  H2("8.1 Validation with fixed initial configurations (Phase 3)"),
  P(`${T("phase3")} shows the full-population validation results of the initial, untuned configurations. On Store Item both global ML models clearly beat every statistical method; Holt-Winters and the seasonal moving average were the strongest classical comparators. On M5 differences were small: the random forest led narrowly, MA28 was second and TSB third, while LightGBM was worse than MA28. The Phase 3 M5 machine-learning runs used historical prices and are conditional references only; the price-free versions used in Phase 4 (random forest 1.0267, LightGBM 1.0731) give the same ranking against MA28. ARIMA and SARIMA were evaluated only on stratified stratified subsets of 53 Store Item and 51 M5 series and are therefore excluded from population claims.`),
  ...table("phase3", "Phase 3 validation, full populations, mean over four origins (selected rows). Source: docs/PHASE3_MODEL_COMPARISON.md.",
    ["Dataset", "Method", "Macro MAE", "Pooled RMSE", "WAPE %", "Macro MASE"],
    [["Store Item", "LightGBM", "6.308", "8.179", "10.34", "0.769"], ["Store Item", "Random forest", "6.885", "8.991", "11.28", "0.837"],
      ["Store Item", "Holt-Winters additive", "7.702", "10.242", "12.62", "0.935"], ["Store Item", "Seasonal moving average", "8.087", "10.600", "13.25", "0.973"],
      ["Store Item", "Seasonal naive", "9.155", "12.024", "15.00", "1.112"], ["Store Item", "MA28", "9.538", "12.549", "15.63", "1.127"],
      ["M5", "Random forest (price-enabled, conditional)", "1.0276", "2.309", "75.81", "1.754"], ["M5", "MA28", "1.0338", "2.343", "76.26", "1.665"],
      ["M5", "TSB", "1.0425", "2.366", "76.90", "1.672"], ["M5", "LightGBM (price-enabled, conditional)", "1.0708", "2.451", "78.99", "1.795"],
      ["M5", "Croston", "1.1224", "2.411", "82.80", "1.799"], ["M5", "Seasonal naive", "1.2120", "2.860", "89.41", "1.877"]],
    [1.4, 2.6, 1.3, 1.4, 1.1, 1.3], { right: [2, 3, 4, 5] }),
  H2("8.2 Optimisation (Phase 4)"),
  P(`Systematic search did not improve the Store Item LightGBM: its initial configuration remained best (validation MAE 6.308), so the final Store Item model reflects no additional tuning gain. On M5, random-forest trial 02 achieved 1.0201 against 1.0338 for MA28, a 1.33% reduction; it had the lower mean error at all four origins, yet MA28 had the lower error for a majority of individual series at every origin (50.15% to 53.20%). ${T("phase4")} and ${F("validation")} show the frozen candidates by origin.`),
  ...table("phase4", "Phase 4 validation macro MAE of the frozen selections and comparators by origin. Source: frozen_selection.json.",
    ["Dataset", "Candidate", "Origin 1", "Origin 2", "Origin 3", "Origin 4", "Mean"],
    [["Store Item", "LightGBM 00 (selected)", "6.492", "6.260", "6.158", "6.322", "6.308"], ["Store Item", "Holt-Winters 01", "6.872", "6.610", "6.770", "7.921", "7.043"],
      ["Store Item", "Seasonal moving average", "9.132", "7.774", "7.100", "8.341", "8.087"], ["Store Item", "Seasonal naive", "9.153", "8.784", "8.577", "10.105", "9.155"],
      ["M5", "Random forest 02 (selected)", "0.9987", "1.0195", "1.0346", "1.0275", "1.0201"], ["M5", "MA28", "1.0150", "1.0333", "1.0458", "1.0411", "1.0338"],
      ["M5", "TSB 01", "1.0102", "1.0369", "1.0431", "1.0463", "1.0341"], ["M5", "Seasonal naive", "1.2056", "1.1994", "1.2106", "1.2324", "1.2120"]],
    [1.3, 2.6, 1, 1, 1, 1, 1], { right: [2, 3, 4, 5, 6] }),
  P(`${T("config")} records the exact frozen configurations. The machine-learning models are deliberately compact: depth-limited trees, a fixed number of boosting rounds without early stopping, and a 56-day feature history, which keeps training on the full M5 population within a laptop budget and avoids any feedback from validation into stopping rules.`),
  ...table("config", "Frozen configurations of the selected models and the tuned statistical comparators. Source: frozen_selection.json.",
    ["Trial", "Model", "Key hyperparameters (all others at library defaults)"],
    [["store_item_lightgbm_00", "LightGBM regressor, recursive 28 steps", "200 boosting rounds, learning rate 0.05, 31 leaves, min 50 samples per leaf, max_bin 63, no bagging or regularisation, deterministic CPU"],
      ["m5_random_forest_02", "Random forest regressor, recursive 28 steps, price-free", "160 trees, max depth 16, max 512 leaves, min 20 samples per leaf and split, 80% features and 70% samples per tree"],
      ["store_item_holt_winters_additive_01", "Additive Holt-Winters, weekly season", "alpha 0.1, trend beta 0.05, seasonal gamma 0.02, damping 0.98"],
      ["m5_tsb_01", "Teunter-Syntetos-Babai", "demand-size alpha 0.1, occurrence beta 0.2"]],
    [2.6, 2.6, 4.2]),
  ...figure("validation", "final_submission/figures/fig_validation_by_origin.png", "Validation macro MAE of the frozen candidates at the four origins."),
  H2("8.3 Final holdout (evaluated once)"),
  P(`${T("final")} and ${F("final")} report the single final assessment. The selected Store Item LightGBM reduced macro MAE by 57.59% relative to seasonal naive, and the selected M5 random forest by 1.74% relative to MA28. On M5 the ordering depends on the metric (${F("metric")}): the random forest is best on MAE, pooled RMSE, WAPE and macro RMSSE, but MA28 (1.6106) and TSB (1.6247) have a lower macro MASE than the random forest (1.6370). On the saved per-series final MAEs the random forest wins 15,655 series and MA28 14,835 (random forest 51.34%), a different pattern from validation, where MA28 won the majority of series. 812 M5 series had no sales in the final window; their WAPE is undefined but they remain in MAE and RMSE.`),
  ...table("final", "Final-holdout results of the frozen selections and predeclared comparators. Source: artifacts/experiments/phase4/final_metrics.",
    ["Dataset", "Method", "Macro MAE", "Pooled RMSE", "Pooled WAPE %", "Macro MASE", "Macro RMSSE"],
    [["Store Item", "LightGBM (selected)", "5.434", "7.067", "12.26", "0.657", "0.645"], ["Store Item", "Holt-Winters additive", "10.651", "13.299", "24.03", "1.243", "1.127"],
      ["Store Item", "Seasonal naive", "12.815", "16.702", "28.91", "1.505", "1.433"], ["Store Item", "Seasonal moving average", "15.807", "18.892", "35.66", "1.820", "1.585"],
      ["M5", "Random forest (selected)", "1.0472", "2.2011", "72.58", "1.6370", "0.8976"], ["M5", "TSB", "1.0632", "2.2083", "73.69", "1.6247", "0.9160"],
      ["M5", "MA28", "1.0657", "2.2430", "73.86", "1.6106", "0.9049"], ["M5", "Seasonal naive", "1.2440", "2.6769", "86.22", "1.8101", "1.1783"]],
    [1.3, 2.5, 1.1, 1.2, 1.3, 1.1, 1.2], { right: [2, 3, 4, 5, 6] }),
  ...figure("final", "final_submission/figures/fig_final_holdout.png", "Final-holdout macro MAE, frozen selections and predeclared comparators."),
  ...figure("metric", "final_submission/figures/fig_m5_metric_dependence.png", "M5 final holdout: percentage difference from MA28 on five metrics; the ranking changes on macro MASE."),
  P("Answering RQ1 and RQ3: on regular, strongly seasonal Store Item demand a global gradient-boosting model gave a large and consistent improvement over every baseline. On intermittent M5 demand the best model improved on a 28-day moving average only marginally, and not on every metric. The method ranking therefore did not transfer between the datasets in magnitude, although machine learning ranked first on the primary metric in both."),
);

// 9 Inventory
add(
  H1("9. Inventory simulation"),
  H2("9.1 Design and assumptions"),
  P("The simulator is a discrete, periodic-review, lost-sales model run on the saved validation sales of each series and origin, using the fixed-origin validation forecasts (never refreshed during an episode and never using final-holdout demand). Forecast policies share an order-up-to rule: at each review the order is the positive part of the forecast over the lead time plus review period, plus a buffer, minus the inventory position, rounded up to whole units. A fixed reorder-point comparator orders a fixed quantity when the inventory position falls to a threshold. Base assumptions were frozen before any result: lead time 7 days, review every day, buffer 3 days of the trailing 56-day mean, initial stock 7 days of that mean, holding 1 NCU per unit per day, unmet demand 10 NCU per unit and 1 NCU per order. The formulae are in Appendix B."),
  P("Every one of the 544 cases (two datasets, four origins, four policies, 17 scenarios) completed on the full populations, giving 8,429,280 series-episodes; the project's own scalar replay of 3,264 episodes confirmed the arithmetic, the independent audit's exact-integer re-simulation of the three deterministic policies found only negligible ceiling-boundary differences, and the final audit re-aggregated all base results from the raw per-series outputs with zero discrepancy."),
  H2("9.2 Results"),
  P(`${T("inv_pool")} and ${F("costfill")} give the base results pooled over the four origins, and ${T("inv_origin")} and ${F("inventory")} the per-origin differences that the independent audit required to be shown together.`),
  ...table("inv_pool", "Base scenario, pooled over four origins (NCU per series per 28-day episode). Source: post_audit_reconciliation.json.",
    ["Dataset", "Policy", "Mean cost", "Cost per demanded unit", "Pooled fill %", "Average on-hand", "Stock-out days per episode"],
    [["Store Item", "Selected ML", "6,038.44", "3.534", "98.38", "205.08", "0.972"], ["Store Item", "MA28", "6,414.59", "3.755", "98.38", "218.52", "0.971"],
      ["Store Item", "Seasonal naive", "6,105.72", "3.574", "98.38", "207.48", "0.972"], ["Store Item", "Fixed ROP (comparator)", "3,276.44", "1.918", "97.68", "102.12", "2.266"],
      ["M5", "Selected ML", "223.82", "5.897", "83.92", "5.54", "2.149"], ["M5", "MA28", "221.92", "5.847", "83.40", "5.40", "2.205"],
      ["M5", "Seasonal naive", "234.83", "6.187", "82.75", "5.81", "2.318"], ["M5", "Fixed ROP (comparator)", "205.14", "5.405", "79.56", "4.20", "2.639"]],
    [1.2, 2.2, 1.2, 1.4, 1.1, 1.2, 1.4], { right: [2, 3, 4, 5, 6] }),
  ...figure("costfill", "final_submission/figures/fig_cost_fill_tradeoff.png", "Base scenario cost, fill rate and average stock by policy."),
  ...table("inv_origin", "Selected ML minus baseline, mean cost by validation origin (NCU; negative means ML cheaper).",
    ["Dataset", "Comparison", "Origin 1", "Origin 2", "Origin 3", "Origin 4", "Pooled"],
    [["Store Item", "ML minus MA28", "−915.78", "−598.09", "−375.92", "+385.21", "−376.14 (−5.86%)"],
      ["Store Item", "ML minus seasonal naive", "−200.30", "−158.19", "+112.83", "−23.43", "−67.27 (−1.10%)"],
      ["M5", "ML minus MA28", "+0.40", "+2.35", "+1.66", "+3.18", "+1.90 (+0.85%)"],
      ["M5", "ML minus seasonal naive", "−16.76", "−9.47", "−5.87", "−11.95", "−11.01 (−4.69%)"]],
    [1.2, 2.2, 1, 1, 1, 1, 1.9], { right: [2, 3, 4, 5, 6] }),
  ...figure("inventory", "final_submission/figures/fig_inventory_by_origin.png", "Simulated cost difference of selected-ML ordering against MA28 and seasonal naive, by origin."),
  P("Three findings follow. First, accuracy and cost diverge: on Store Item the ML forecast is more accurate than MA28 at every origin, yet costlier at origin 4, where 473 of 500 series cost more; cost depends on the forecast level relative to the order-up-to target, not on error magnitude alone. Second, against the stronger seasonal-naive baseline the Store Item advantage is small (−1.10%) and reverses at origin 3. Third, on M5 the more accurate random forest is costlier than MA28 at all four origins while giving a slightly higher pooled fill rate (+0.52 points). The M5 mean cost is driven by a minority of series: the median paired difference is zero at every origin, with 7,454 to 7,650 exactly tied series."),
  P("Why can a more accurate forecast cost more? Under an order-up-to policy the order quantity is driven by the level of the summed forecast over the protection interval (eight days in the base case), and holding cost accrues on every unit of excess stock, whereas a shortage is incurred only when stock runs out. A forecast whose absolute error is smaller but whose level is biased upwards in a particular window therefore builds more stock than a lower, less accurate forecast. The asymmetric cost ratio (10 NCU per unmet unit against 1 NCU per unit-day held) and the identical days-of-cover buffer for all policies mean that small level differences multiply into cost differences that need not follow the ranking by MAE."),
  H2("9.3 The fixed reorder-point comparator"),
  P(`The fixed reorder-point rule has the lowest cost in both datasets, but this reflects lower stock, not better management (${T("rop")}). On Store Item it orders at essentially every review because its inventory position (7.33 mean days of demand) never rises above the 11-day reorder point, so it behaves as a daily one-day replenishment; on M5 it acts as a threshold rule. Its fill rate is lower than the ML policy in 15 of 17 Store Item scenarios and all 17 M5 scenarios. It is therefore reported as a low-stock, lower-service comparator.`),
  ...table("rop", "Fixed reorder-point behaviour in the base scenario (series with positive history mean).",
    ["Dataset", "Series-episodes ordering at every review", "Mean orders (of 20)", "Mean inventory position (days)", "Scenarios cheapest (of 17)", "Scenarios with fill below ML (of 17)"],
    [["Store Item", "99.9%", "20.00", "7.33", "14", "15"], ["M5", "11.0%", "10.49", "11.34", "14", "17"]],
    [1.2, 2, 1.3, 1.6, 1.4, 1.6], { right: [1, 2, 3, 4, 5] }),
  H2("9.4 Sensitivity"),
  P(`Seventeen scenarios varied lead time, buffer, initial stock, cost rates, review interval and a demand-variability stress (${T("sens")}). They reuse the same four origins, forecasts and populations, so they are parameter sensitivity checks, not independent confirmations: on Store Item the ML policy is cheaper than MA28 in all 17 pooled scenarios yet in only 52 of 68 scenario-origin cells, because origin 4 reverses almost every scenario. Finite-episode effects matter: with a long lead time the empty initial pipeline produces early stock-outs that dominate cost. This answers RQ4: the cost ranking is sensitive both to the forecast policy and to the window, and on Store Item more sensitive to the validation origin than to the scenario parameters, while on M5 the sign against MA28 also depends on the scenario (ML cheaper in 3 of 17).`),
  ...table("sens", "Sensitivity summary over 17 scenarios. Source: docs/PHASE5_INVENTORY_RESULTS.md.",
    ["Dataset", "Reference", "Origins ML cheaper (base)", "Scenarios ML cheaper, pooled", "Scenario-origin cells ML cheaper"],
    [["Store Item", "MA28", "3 of 4", "17 of 17", "52 of 68"], ["Store Item", "Seasonal naive", "3 of 4", "16 of 17", "49 of 68"],
      ["M5", "MA28", "0 of 4", "3 of 17", "13 of 68"], ["M5", "Seasonal naive", "4 of 4", "17 of 17", "65 of 68"]],
    [1.3, 1.7, 1.8, 2, 2.2], { right: [2, 3, 4] }),
);

// 10 System
add(
  H1("10. System architecture and implementation"),
  P(`The research pipeline is a Python package (data adapters, exploratory analysis, forecasting, evaluation, inventory, preservation and reporting) with a command-line interface, configuration files and 352 automated tests at the Phase 4 checkpoint. Phase 6 delivered a five-page Power BI report (86 visuals, 69 DAX measures) whose 43-rule quality check (42 pass, 1 cosmetic warning) reconciles the report's measures with the saved evidence. Phase 7 delivered the public research application (${F("arch")}).`),
  ...figure("arch", "final_submission/figures/fig_architecture.png", "Deployed architecture. The browser holds no credentials; demand and forecasts for simulations are loaded server-side."),
  P("The Next.js application serves five pages (Executive Overview, Forecast Explorer, Inventory Planner, Scenario Comparison, Research and Methodology) from eleven versioned API routes. A FastAPI service wraps the byte-identical frozen Phase 5 engine and is reachable only with a shared key and Vercel's protection bypass. Supabase PostgreSQL holds 655,711 exported evidence rows behind two read-only roles. Validation, rate limiting, generic errors and security headers protect the public interface. Two defects found during deployment are instructive. First, Supabase rounds text-transferred double-precision values to 15 significant digits, which changed integer inventory results for 182 of 3,200 series-origin pairs; the engine now reads binary floats and the web API reads inside transactions that request exact output. Second, a TLS option in the database connection string was forwarded to the server as a startup parameter and rejected; it is now applied on the client. Both were found only because exact parity with the local reference was required."),
  ...figure("app", "final_submission/screenshots/planner_totals.png", "Inventory Planner in production: live engine totals (second column) for a curated series and origin equal the saved Phase 5 totals (third column).", 6.2),
  ...table("qa", "Production verification of the deployed application (2026-11-12). Source: reports/webapp/phase7d/live_web_checks.json, live_engine_checks.json.",
    ["Check", "Result"],
    [["API parity with the local reference", "21 of 21 responses byte-identical (reads, three simulations, CSV export)"],
      ["Phase 5 base totals through the full stack", "2,555 / 2,772 / 2,900 / 1,309 NCU for the four policies on the reference case"],
      ["Engine scientific parity", "Five series-origin pairs bit-exact against the local engine"],
      ["Validation, methods and data scope", "All invalid inputs rejected (400/404/405/413); only curated series exposed; final-holdout targets never served"],
      ["Security", "No secrets in 107 responses or 9 client assets; protected engine (401 anonymously); security headers including HSTS"],
      ["Browser", "Five pages at three widths: no overflow, no serious accessibility violation, no console errors"],
      ["Not tested in production", "Real engine or database outage; protection of a built preview deployment"]],
    [3, 6.4]),
);

// 11 Discussion
add(
  H1("11. Discussion"),
  P("The contrast between the datasets is the central result. Store Item series are regular, so lags and calendar effects carry real signal and a global gradient-boosting model can exploit them; the 57.59% final improvement over seasonal naive is large and consistent across origins. M5 leaf series are mostly intermittent: two thirds of the sampled training labels are zero, and a 28-day mean is already close to the best attainable point forecast for many series. In that regime the random forest's advantage is small, concentrated outside the sparsest series, and not robust to the choice of scaled metric. This is consistent with the literature's view that the value of complex models depends on the data (Petropoulos et al., 2022)."),
  P("The inventory study shows why accuracy alone is an incomplete criterion. An order-up-to policy is sensitive to the forecast level: a forecast with lower absolute error but a systematically higher level raises stock and holding cost. Better forecasts did not reliably lower simulated cost, and the cheapest policy was the one that held the least stock and served the fewest units. Any operational recommendation would require service targets, real costs and a fresh evaluation window, none of which these datasets provide."),
  P("For practice, the results suggest a pragmatic sequence: for regular, high-volume items a global gradient-boosting model was clearly more accurate on the one regular dataset studied, although its cost advantage was not robust; for intermittent items a well-chosen simple method such as a 28-day mean or TSB remains a strong default, and model choice should be validated on the decision metric (cost and service) rather than on accuracy alone. They also show the value of reporting results per evaluation window: a single pooled figure would have hidden the Store Item reversal at origin 4."),
  P("The governance design is a contribution in its own right. The selection fingerprint, sealed forecast bundles and once-only holdout ledger make it possible to demonstrate, rather than assert, that the final result did not influence model choice. The same discipline carried into deployment: the public application serves byte-identical evidence and runs the byte-identical frozen engine, and the two defects found in production, one of them a silent loss of floating-point precision, were detected only because exact, not approximate, parity was required."),
  P("Regarding RQ2, the decisive data choices were the exclusion of prices and events whose availability at the forecast origin could not be verified, the retention of zeros and missing values instead of imputation, and full-population evaluation. Price-enabled Phase 3 experiments are kept only as conditional references, because using prices that might not have been published by the origin would risk leakage."),
);

// 12 Limitations
add(
  H1("12. Limitations and threats to validity"),
  ...table("threats", "Threats to validity and how they were handled.",
    ["Threat", "Effect", "Handling"],
    [["Sales are censored demand", "Low sales may reflect stock-outs or assortment", "Treated as a demand proxy; lost sales are assumed in simulation"],
      ["Limited seasonal coverage", "Four adjacent origins and one final window", "Origin spread reported as variability, not confidence intervals"],
      ["Selection optimism", "Phase 5 reuses the windows that selected ML; bias favours ML and is unquantifiable", "Stated explicitly; the M5 result (ML not cheaper) is the more informative"],
      ["No significance testing", "Correlated series and four origins", "No significance claims are made"],
      ["Metric dependence", "M5 ranking changes on MASE", "All metrics reported; primary metric unchanged"],
      ["Bounded ML training sample", "Six labels per M5 series per origin", "Disclosed; full histories not used for training"],
      ["Hypothetical costs and assumptions", "NCU are not prices", "No savings claim; 17 sensitivity scenarios"],
      ["Self-recorded chronology", "Ledger order relies on the recorder's clock", "Mitigated by code hashes and once-only reads"],
      ["Environment portability", "Clean-machine retraining untested (Python 3.14 on Windows)", "Reproduction is of saved artefacts"],
      ["External validity", "Two public histories", "No claim of universal ranking or direct transfer"]],
    [2.4, 3.3, 3.7]),
  P(`The independent technical audit of Phases 0 to 5, an AI-assisted review in a separate context (${T("audit")}, Appendix E) found no critical or high issue and set reporting rules that this paper follows: show selected ML, MA28 and seasonal naive by origin together; never present the scenario count as robustness; describe the fixed reorder point as a low-stock comparator; and never describe simulated cost differences as savings.`),
);

// 13 Conclusions
add(
  H1("13. Conclusions and future work"),
  P("Under one governed protocol, global machine learning gave a large forecasting improvement on regular retail demand and only a marginal, metric-dependent improvement on intermittent demand. Forecast accuracy did not translate reliably into lower simulated inventory cost. The project's contribution is a reproducible, leakage-controlled and transparently reported comparison, with a sealed final evaluation, full-population results on 30,490 M5 series, an audited simulation and a deployed application that serves exactly the recorded evidence for its curated series (all 500 Store Item and 300 of 30,490 M5 series)."),
  P("Future work should (i) evaluate on a fresh, untouched window to remove the selection optimism of the inventory study; (ii) add a properly tuned (s, S) comparator and service-level targets; (iii) model censored demand explicitly; (iv) test price and event features under verified publication-availability assumptions; (v) report distributional forecasts for safety-stock decisions; and (vi) repeat the analysis on a clean machine to confirm reproduction from source."),
);

// References
const refs = [
  "Bergmeir, C. and Benítez, J.M. (2012) 'On the use of cross-validation for time series predictor evaluation', Information Sciences, 191, pp. 192–213. doi:10.1016/j.ins.2011.12.028.",
  "Breiman, L. (2001) 'Random forests', Machine Learning, 45(1), pp. 5–32. doi:10.1023/A:1010933404324.",
  "Conrad, S.A. (1976) 'Sales data and the estimation of demand', Operational Research Quarterly, 27(1), pp. 123–127. doi:10.1057/jors.1976.13.",
  "Croston, J.D. (1972) 'Forecasting and stock control for intermittent demands', Operational Research Quarterly, 23(3), pp. 289–303. doi:10.2307/3007885.",
  "Fildes, R., Ma, S. and Kolassa, S. (2022) 'Retail forecasting: Research and practice', International Journal of Forecasting, 38(4), pp. 1283–1318. doi:10.1016/j.ijforecast.2019.06.004.",
  "Holt, C.C. (2004) 'Forecasting seasonals and trends by exponentially weighted moving averages', International Journal of Forecasting, 20(1), pp. 5–10. doi:10.1016/j.ijforecast.2003.09.015.",
  "Hyndman, R.J. and Athanasopoulos, G. (2021) Forecasting: Principles and Practice. 3rd edn. Melbourne: OTexts. Available at: https://otexts.com/fpp3/.",
  "Hyndman, R.J. and Koehler, A.B. (2006) 'Another look at measures of forecast accuracy', International Journal of Forecasting, 22(4), pp. 679–688. doi:10.1016/j.ijforecast.2006.03.001.",
  "Hyndman, R.J., Koehler, A.B., Snyder, R.D. and Grose, S. (2002) 'A state space framework for automatic forecasting using exponential smoothing methods', International Journal of Forecasting, 18(3), pp. 439–454. doi:10.1016/S0169-2070(01)00110-8.",
  "Januschowski, T., Gasthaus, J., Wang, Y., Salinas, D., Flunkert, V., Bohlke-Schneider, M. and Callot, L. (2020) 'Criteria for classifying forecasting methods', International Journal of Forecasting, 36(1), pp. 167–177. doi:10.1016/j.ijforecast.2019.05.008.",
  "Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q. and Liu, T.-Y. (2017) 'LightGBM: A highly efficient gradient boosting decision tree', Advances in Neural Information Processing Systems, 30.",
  "Makridakis, S., Spiliotis, E. and Assimakopoulos, V. (2022a) 'The M5 competition: Background, organization, and implementation', International Journal of Forecasting, 38(4), pp. 1325–1336. doi:10.1016/j.ijforecast.2021.07.007.",
  "Makridakis, S., Spiliotis, E. and Assimakopoulos, V. (2022b) 'M5 accuracy competition: Results, findings, and conclusions', International Journal of Forecasting, 38(4), pp. 1346–1364. doi:10.1016/j.ijforecast.2021.11.013.",
  "Montero-Manso, P. and Hyndman, R.J. (2021) 'Principles and algorithms for forecasting groups of time series: Locality and globality', International Journal of Forecasting, 37(4), pp. 1632–1653. doi:10.1016/j.ijforecast.2021.03.004.",
  "Pedregosa, F. et al. (2011) 'Scikit-learn: Machine learning in Python', Journal of Machine Learning Research, 12, pp. 2825–2830.",
  "Petropoulos, F. et al. (2022) 'Forecasting: theory and practice', International Journal of Forecasting, 38(3), pp. 705–871. doi:10.1016/j.ijforecast.2021.11.001.",
  "Syntetos, A.A. and Boylan, J.E. (2001) 'On the bias of intermittent demand estimates', International Journal of Production Economics, 71(1–3), pp. 457–466. doi:10.1016/S0925-5273(00)00143-2.",
  "Syntetos, A.A. and Boylan, J.E. (2005) 'The accuracy of intermittent demand estimates', International Journal of Forecasting, 21(2), pp. 303–314. doi:10.1016/j.ijforecast.2004.10.001.",
  "Syntetos, A.A., Boylan, J.E. and Croston, J.D. (2005) 'On the categorization of demand patterns', Journal of the Operational Research Society, 56(5), pp. 495–503. doi:10.1057/palgrave.jors.2601841.",
  "Tashman, L.J. (2000) 'Out-of-sample tests of forecasting accuracy: an analysis and review', International Journal of Forecasting, 16(4), pp. 437–450. doi:10.1016/S0169-2070(00)00065-0.",
  "Teunter, R.H., Syntetos, A.A. and Babai, M.Z. (2011) 'Intermittent demand: Linking forecasting to inventory obsolescence', European Journal of Operational Research, 214(3), pp. 606–615. doi:10.1016/j.ejor.2011.05.018.",
  "Winters, P.R. (1960) 'Forecasting sales by exponentially weighted moving averages', Management Science, 6(3), pp. 324–342. doi:10.1287/mnsc.6.3.324.",
];
add(H1("References"), ...refs.map((r) => new Paragraph({ children: runs(r, { size: 21 }), indent: { left: 567, hanging: 567 }, spacing: { after: 100 } })));
add(new Paragraph({ indent: { left: 567, hanging: 567 }, spacing: { after: 100 }, children: runs("Datasets: Kaggle, *Store Item Demand Forecasting Challenge* (demand-forecasting-kernels-only) and *M5 Forecasting – Accuracy* (m5-forecasting-accuracy), obtained through the official Kaggle client. The raw files are not redistributed with this work; the public demonstrator displays derived results and daily sales for curated series. The owner's recorded review of both competitions' data-use terms is pending.", { size: 21 }) }));

// Appendices
add(
  BR(),
  H1("Appendix A. Metric definitions"),
  ...table("metrics", "Error measures (e = forecast − actual; positive bias = over-forecasting).",
    ["Measure", "Definition", "Notes"],
    [["MAE", "mean(|e|)", "Units per day; primary selection metric (macro)"], ["RMSE", "sqrt(mean(e²))", "Emphasises large errors"],
      ["WAPE", "100 × Σ|e| / Σ|y|", "Undefined when Σ|y| = 0"], ["Bias", "mean(e) and 100 × Σe / Σ|y|", "Opposing errors cancel"],
      ["MASE", "MAE / q_abs, q_abs = mean |y_t − y_(t−7)| over the training period", "Undefined if q_abs = 0"],
      ["RMSSE", "sqrt(mean(e²) / q_sq), q_sq = mean (y_t − y_(t−7))²", "Leaf-level; not official M5 WRMSSE"]],
    [1.3, 4.6, 3.5]),
  H1("Appendix B. Inventory policy mathematics"),
  P("Let μ be the trailing 56-day training mean, L the lead time, R the review interval, P = L + R, B = b·μ the buffer and IP = closing stock + pipeline. Orders placed at the end of day t arrive at the start of day t + L + 1; unmet demand is lost."),
  EQ("Forecast policies:  S = (f(t+1) + f(t+2) + … + f(t+P)) + B,   order = ⌈ max(0, S − IP) ⌉"),
  EQ("Fixed reorder point:  s = μ·P + B,   Q = ⌈ μ·R ⌉,   order Q if IP ≤ s"),
  EQ("Daily cost = h·closing + p·unmet + k·1[order > 0] + v·ordered;  terminal e·(closing + pipeline)"),
  P("Base parameters: L = 7, R = 1, b = 3, initial stock 7·μ, h = 1, p = 10, k = 1, v = 0, e = 0 NCU. Pooled fill rate = Σ fulfilled / Σ demand. Average on-hand is the mean daily closing stock.", { spacing: { before: 200, after: 120, line: 300 } }),
  H1("Appendix C. Reproducibility and evidence"),
  B("Raw and canonical data hashes, the frozen selection fingerprint (a71ab187…), the 12-event holdout ledger (fa2af529…), the Phase 5 plan (63efc59e…) and execution (b55ba4a0…) freezes were all re-verified in the final audit."),
  B("Saved-artefact reproduction is exact: validation MAE of the selected and baseline models was recomputed from saved forecasts with zero difference, and all Phase 5 base results were re-aggregated from raw outputs with zero difference."),
  B("Source code is in a private Git repository; a verified Git bundle, SHA-256 manifest and evidence copy are part of the submission backup. Kaggle data are not redistributed."),
  B("Reproduction scripts and commands: final_submission/_verification and the phase reproducibility documents (PHASE4_REPRODUCIBILITY.md, PHASE5_INVENTORY_RESULTS.md)."),
  H1("Appendix D. Evidence traceability"),
  P("Every project-specific number in this paper is mapped to its source file in final_submission/02_traceability/EVIDENCE_TO_CLAIM_TRACEABILITY.md, which also lists the statements the evidence does not support."),
  H1("Appendix E. Independent audit findings"),
  ...table("audit", "Findings of the independent audit of Phases 0 to 5 (2026-11-10) and their disposition. Source: docs/PHASE5_AUDIT_RESPONSE.md.",
    ["ID", "Severity", "Finding", "Disposition"],
    [["F-01", "Medium", "Phase 5 checkpoint not committed", "Resolved (committed)"], ["F-02", "Medium", "No off-device evidence copy", "Open: off-device copy pending owner action (see backup report)"],
      ["F-03", "Medium", "Fixed reorder point is degenerate", "Reported as a low-stock comparator"], ["F-04", "Medium", "Headline ML cost result less robust than presented", "Per-origin and seasonal-naive comparisons always shown"],
      ["F-05", "Medium", "Selection optimism from reused validation", "Documented limitation"], ["F-06", "Medium", "M5 sparse-demand weakness", "Documented limitation"],
      ["F-07", "Low", "Volume-weighted mean cost, many ties", "Median, ties and cost per unit reported"], ["F-08", "Low", "Self-recorded chronology", "Accepted limitation"],
      ["F-09", "Low", "Finite-episode artefacts", "Caveats attached to scenarios"], ["F-10", "Low", "Clean-room reproduction untested", "Open, optional"],
      ["F-11", "Info", "Scalar reference shared and amended", "Closed"], ["F-12", "Info", "Variability stress changes mean and zeros", "Closed"]],
    [0.9, 1.1, 3.9, 3.5]),
);

// ---------------------------------------------------------------- document
const doc = new Document({
  creator: "Youssef Saeed", title: "Intelligent Demand Forecasting and Inventory Optimisation", description: "Research paper",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 23 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: "1F3A5F" }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 25, bold: true, color: "1F3A5F" }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 23, bold: true, italics: true }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 283 } } } }] },
    { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 340 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 1304, bottom: 1304, left: MARGIN, right: MARGIN } }, titlePage: true },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Intelligent Demand Forecasting and Inventory Optimisation", size: 17, color: "6B6A66" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] }) },
    children: body,
  }],
});

for (const k of ["fig", "tab"]) {
  if (JSON.stringify(emitted[k]) !== JSON.stringify(reg[k])) throw new Error(`${k} order mismatch: ${emitted[k]} vs ${reg[k]}`);
}
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length, "bytes; figures", reg.fig.length, "tables", reg.tab.length); });
