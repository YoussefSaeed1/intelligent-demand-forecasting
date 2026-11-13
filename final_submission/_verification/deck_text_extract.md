<!-- Slide number: 1 -->
Intelligent Demand Forecasting and Inventory Optimisation
A governed comparison of statistical and machine-learning forecasts, a hypothetical inventory simulation and a deployed research application
Youssef Saeed  ·  November 2026

### Notes:
Good morning. My project asks a simple business question with a careful scientific answer: does machine-learning forecasting beat simple rules for daily retail demand, and what would that mean for inventory? I tested this on two public retail datasets under one governed protocol, evaluated the final models exactly once on a sealed holdout, simulated four replenishment policies, and deployed the evidence as a public research application. I will spend about twenty minutes and then take questions.

<!-- Slide number: 2 -->
Every order is a bet on tomorrow's demand
30,990
60.1 M
68.8%
daily store-item series analysed (500 Store Item + 30,490 M5)
daily sales observations across both histories (913,000 + 59,181,090)
of M5 training-period series-day observations have zero sales: intermittent demand
Why it matters
What makes it hard
Under-forecasting loses sales and goodwill; over-forecasting raises holding cost and waste. Forecast quality is only valuable through the decisions it drives.
Comparisons of ML and simple rules differ in data, horizon, windows and metrics. Sales are censored by stock-outs, so observed sales understate true demand.
2

### Notes:
Retailers reorder thousands of store-item combinations every day. Too little stock loses sales; too much ties up capital. Both mistakes start with the demand forecast. Machine learning is often promoted as the fix, but claims are hard to compare because studies use different data, horizons and error measures. My two datasets have opposite characters: Store Item is regular and seasonal; M5 from Walmart is mostly intermittent, with almost seven in ten days showing zero sales. That contrast is what makes the comparison informative. One caveat from the start: the data record sales, not demand, and contain no stock or cost data, so the inventory part is a hypothetical simulation.

<!-- Slide number: 3 -->
Four research questions
RQ1  Methods
RQ2  Data and features
How do naive, statistical and machine-learning approaches compare on the same 28-day daily horizon and windows?
Which data-quality and feature choices affect forecast reliability across series?
RQ3  Replication
RQ4  Decisions
Does the relative ranking of methods hold on a second, independently sourced dataset?
How sensitive are simulated cost and service trade-offs to the forecast policy and assumed parameters?
3

### Notes:
These four questions come directly from the project proposal. RQ1 is the core benchmark. RQ2 asks which data and feature choices matter, for example whether prices can be used safely. RQ3 asks whether a ranking found on one dataset holds on a very different second dataset. RQ4 moves from accuracy to decisions: how do simulated cost and service respond to the forecast and to the assumed operating parameters? Out of scope were causal business claims, reconstructing real stock and any claim of real savings.

<!-- Slide number: 4 -->
Two public datasets with opposite demand character

|  | Store Item | M5 (Walmart) |
| --- | --- | --- |
| History | 2013-01-01 to 2017-12-31 | 2011-01-29 to 2016-05-22 |
| Stores / products / series | 10 / 50 / 500 | 10 / 3,049 / 30,490 |
| Daily observations | 913,000 | 59,181,090 |
| Zero days (training prefix) | 1 (0.0001%) | 68.84% |
| Median daily units | 46 | 0 |
| Top-10% products' share of units | 16.3% | 51.7% |
| Prices | none | weekly; 20.8% missing |

Source: docs/EDA_FINDINGS.md, docs/DATASETS.md. Raw Kaggle files are not redistributed; data-use terms review by the owner is pending.
4

### Notes:
Store Item from Kaggle has 500 series over five years with complete coverage and only a single zero. M5 is Walmart data: 30,490 series, 59 million daily rows, and highly concentrated volume, where the top ten percent of products carry over half the units. M5 has weekly prices, but a fifth are missing, almost always before a product's first sale. Both datasets were converted into one canonical schema with unique keys, and all source hashes were re-verified in the final audit. I never merged the two sources or treated them as one population.

<!-- Slide number: 5 -->
EDA: M5 is mostly intermittent; Store Item is smooth
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\reports\figures\phase2\m5_classification.png](Image 0)
Store Item
All 500 series smooth. Strong weekly cycle: Sunday 1.19 and Monday 0.79 of the week's mean; weekly STL strength 0.976.
Implication for design
Seasonal and smoothing baselines plus global ML for Store Item; intermittent-demand methods (Croston, SBA, TSB) plus global ML for M5, scored by demand class.
ADI cut-off 1.32, CV² cut-off 0.49 (Syntetos, Boylan and Croston, 2005). Figure: reports/figures/phase2/m5_classification.png. Full references: research paper.
5

### Notes:
Exploratory analysis used only the training prefix, so nothing about the validation or final windows could leak into design choices. Using the Syntetos-Boylan-Croston ADI and CV-squared scheme, all 500 Store Item series are smooth, while three quarters of M5 series are intermittent and a fifth lumpy, with a few all-zero histories. This single chart explains most of the later results: methods that exploit regular seasonality do well on Store Item, while on M5 a simple average is already hard to beat.

<!-- Slide number: 6 -->
EDA: stable calendars; prices unusable at the origin
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\reports\figures\phase2\store_item_calendar_patterns.png](Image 0)
M5 prices
12.3 million missing prices (20.8%, full history); all 12,298,948 in the training prefix coincide with zero sales. Publication latency unverified, so prices, events and SNAP are excluded from every final model.
Data quality decisions (RQ2)
No imputation of sales or prices; zeros and extreme values preserved after checks against source files; no deletion of difficult series; competition test rows without labels never used as targets.
Figure: reports/figures/phase2/store_item_calendar_patterns.png (training prefix 2013-01-01 to 2017-08-13).
6

### Notes:
Store Item shows a very stable weekly and annual calendar, with tight bootstrap intervals. For M5, a key finding was about prices: every missing price in the training prefix coincides with zero sales, mostly before a product's first sale. More importantly, I could not verify when prices were published relative to the forecast origin, so using them could leak future information. All final models are therefore price-free. That is my answer to RQ2: the decisive choices were excluding features whose availability is uncertain, keeping zeros and missing values rather than imputing, and evaluating full populations.

<!-- Slide number: 7 -->
Forecasting architecture: 28 days, recursive, leakage-controlled
1  Origin
2  Features
3  One-step model
4  Recurse 28 days
All data up to and including the origin date
Lags 1, 7, 14, 28, 56; rolling means; zero fractions; ADI/CV²; calendar; IDs
Global LightGBM or random forest per dataset
Own clipped predictions feed later lags
Information contract
Delivery rules
Every feature for target date t uses observations strictly before t. Prices, events and SNAP excluded. Occurrence statistics frozen at the origin so predictions are never treated as observed sales.
No rounding; clip at zero; predeclared seasonal-naive fallback counted if a fit fails (none needed in the final assessment); full populations: 500 and 30,490 series.
Source: docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md, docs/PHASE4_FEATURE_AVAILABILITY.md.
7

### Notes:
Every method forecasts the next 28 days from an origin, without seeing any actual sales in that window. The machine-learning models are global: one model per dataset trained across all series, as a one-step regressor applied recursively, so from day two onwards it uses its own predictions as lags. Features use only data strictly before each target date, and tests deliberately poison future values to prove that the forecasts cannot depend on them. Forecasts are never rounded, are clipped at zero, and every series must receive a forecast.

<!-- Slide number: 8 -->
Validation: four expanding origins and one sealed final window
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\figures\fig_rolling_origin.png](Image 0)
Primary objective
Mean over the four origins of macro MAE (each series weighted equally), declared before any scoring.
Secondary metrics
Not claimed
Pooled RMSE and WAPE, bias, and scaled MASE and RMSSE. Undefined values stay undefined, never zero.
No significance tests (four correlated origins); not the official M5 WRMSSE; no direct cross-dataset transfer.
8

### Notes:
The evaluation is purely chronological. Training expands: each origin uses everything up to that date, and the next 28 days are the target. There are four validation windows and then the final holdout, which was evaluated only once, after the model choice was frozen. Two caveats I state openly: the four origins are adjacent, so they show variability over a limited season rather than four independent replications, and repeated tuning on the same windows makes validation scores optimistic, which is why the sealed holdout matters.

<!-- Slide number: 9 -->
Governance: the final holdout could not influence model choice
1
2
3
4
Freeze
Seal
Read once
Re-verify
Manifest a71ab187… fixes models, features, comparators and 89 source files
3,470,880 final forecasts sealed before any target read
Each holdout read once; 12‑event hash‑chained ledger fa2af529…
Phase 8 audit: fingerprint, ledger chain and 9 data hashes all match
Independent technical audit (2026-11-10)
AI-assisted review of Phases 0 to 5 in a separate context: verdict CONDITIONAL with 0 critical, 0 high, 6 medium and 4 low findings. Its reporting rules govern every result shown today.
9

### Notes:
This is the part of the project I am proudest of. After validation, the selection was frozen in a manifest whose SHA-256 fingerprint covers the chosen models, features, comparators and 89 source files. All final forecasts were sealed before the first holdout read, and each dataset's holdout was read exactly once, recorded in a hash-chained ledger of twelve events. In the final audit I re-verified the fingerprint, the ledger chain and all nine data file hashes. One honest limitation: the ledger timestamps are self-recorded, so this proves order only if the recorder is trusted.

<!-- Slide number: 10 -->
Models and baselines
Baselines
Exponential smoothing
Zero · Naive · Seasonal naive · MA28 · Seasonal moving average
SES · Holt · Additive Holt-Winters (weekly)
Intermittent demand
Global machine learning
Croston (1972) · SBA (Syntetos and Boylan, 2005) · TSB (Teunter et al., 2011)
Random forest · LightGBM: one model per dataset, recursive
27
108
45.2 M
Phase 4 configurations (23 tuned + 4 references)
fold runs, all independently reconciled
validation forecasts checked (45,177,440)
ARIMA and SARIMA ran on stratified subsets only (53 Store Item, 51 M5 series). Full references: research paper.
10

### Notes:
I compared thirteen methods in Phase 3 on the full populations. The baselines matter because they set the bar: naive, seasonal naive and moving averages. Statistical comparators include exponential smoothing, Holt-Winters and the intermittent-demand family: Croston, its bias-corrected SBA variant, and TSB, which updates the demand probability every period. ARIMA and SARIMA were run only on small stratified subsets, so I make no population claims about them. In Phase 4 a seeded random search evaluated 23 tuning trials plus four unchanged references, 108 fold runs in total.

<!-- Slide number: 11 -->
Validation: clear lead on Store Item, narrow lead on M5

### Chart: Store Item: macro MAE

| Category | LightGBM (selected) | Holt-Winters | Seasonal naive |
| --- | --- | --- | --- |
| Origin 1 | 6.492088088665719 | 6.872005886334718 | 9.153214285714286 |
| Origin 2 | 6.260136069670047 | 6.609829902192527 | 8.783928571428573 |
| Origin 3 | 6.157554588806195 | 6.770359515583637 | 8.577285714285713 |
| Origin 4 | 6.322380540737706 | 7.921101746417289 | 10.105428571428572 |

### Chart: M5: macro MAE

| Category | Random forest (selected) | MA28 | TSB |
| --- | --- | --- | --- |
| Origin 1 | 0.9986903229382016 | 1.014950033801648 | 1.0101687994289086 |
| Origin 2 | 1.0195172344666987 | 1.0332807343993682 | 1.0368755531147937 |
| Origin 3 | 1.0345736584988314 | 1.0457541281517526 | 1.0431494049193253 |
| Origin 4 | 1.0274867244328751 | 1.0411320038018488 | 1.0463306519699302 |

Source: frozen_selection.json fold MAE. M5 seasonal naive (about 1.21) omitted for scale. Origins are adjacent, not independent replications.
11

### Notes:
These are the frozen candidates at the four validation origins. On Store Item, LightGBM is lowest at every origin, around 6.3 units per day, against 9.2 for seasonal naive. Interestingly, tuning did not improve LightGBM: its initial configuration stayed best. On M5 the lines almost touch: the random forest is about 1.3% better than MA28 on average and lower at all four origins, yet MA28 still wins the majority of individual series at every origin. So on M5 the mean advantage is real but small.

<!-- Slide number: 12 -->
Final holdout: large gain on Store Item, marginal on M5

### Chart: Store Item: final macro MAE

| Category | Final macro MAE |
| --- | --- |
| LightGBM (selected) | 5.434342530628236 |
| Holt-Winters | 10.651093200657884 |
| Seasonal naive | 12.814642857142857 |
| Seasonal MA | 15.807285714285713 |

### Chart: M5: final macro MAE

| Category | Final macro MAE |
| --- | --- |
| Random forest (selected) | 1.0472313706239513 |
| TSB | 1.063192966557648 |
| MA28 | 1.0657293123874672 |
| Seasonal naive | 1.2439722625685237 |

−57.6%
Store Item MAE vs seasonal naive
−1.7%
M5 MAE vs MA28
Read with care
One 28-day window per dataset; no significance claim; selections frozen before the read and never revised. 812 M5 series had zero sales in the window (WAPE undefined, kept in MAE).
Source: artifacts/experiments/phase4/final_metrics/*.json (SHA-256 verified). Store Item 2017-12-04 to 2017-12-31; M5 2016-04-25 to 2016-05-22.
12

### Notes:
This is the single final assessment on the sealed window. On Store Item the selected LightGBM achieved a mean absolute error of 5.43 units per day against 12.81 for seasonal naive: a 57.6 percent reduction. On M5 the selected random forest achieved 1.047 against 1.066 for MA28: only 1.7 percent. The selections were not changed after seeing these results, and on both datasets the frozen choice also happened to have the lowest final MAE among the predeclared candidates. That answers RQ1 and RQ3: machine learning ranked first on both, but the size of the gain did not transfer.

<!-- Slide number: 13 -->
On M5 the ranking depends on the metric

### Chart: % difference vs MA28 (negative = better)

| Category | Random forest (selected) | TSB |
| --- | --- | --- |
| MAE (primary) | -1.74 | -0.24 |
| Pooled RMSE | -1.87 | -1.55 |
| Pooled WAPE | -1.74 | -0.24 |
| Macro MASE | 1.64 | 0.88 |
| Macro RMSSE | -0.8 | 1.22 |

What it means
RF is better on four of five metrics but worse than MA28 and TSB on macro MASE (1.637 vs 1.611 and 1.625). On intermittent demand a 28-day mean is already near the best point forecast for many series.
Source: final_metrics/*.json. Seasonal naive (12% to 30% worse than MA28 on every metric) omitted for scale.
13

### Notes:
Here every bar is the percentage difference from MA28 on the final holdout, so below zero is better. The random forest wins on MAE, RMSE, WAPE and RMSSE, but it loses on macro MASE, where both MA28 and TSB are better. Scaled metrics change how much each series counts. I kept the predeclared primary metric and did not switch metrics after seeing results; instead I report all of them. On the saved per-series errors the forest wins 51.3 percent of series, a different pattern from validation, which again warns against strong claims on M5.

<!-- Slide number: 14 -->
Inventory simulation: a hypothetical, audited what-if
544
8.43 M
0.0
cases: 2 datasets × 4 origins × 4 policies × 17 scenarios
series-episodes simulated (8,429,280), full populations
discrepancy when re-aggregated from raw outputs in the final audit
Policies
Base assumptions
Costs (NCU)
Order-up-to with Selected ML, MA28 or seasonal-naive forecasts; fixed reorder-point comparator.
Lead 7 days, review daily, buffer 3 mean-days, initial cover 7 days; lost sales; unlimited supply.
Holding 1 per unit-day, unmet 10 per unit, 1 per order. Hypothetical units, not prices or savings.
14

### Notes:
To answer RQ4 I built a deterministic, periodic-review, lost-sales simulator and ran it on the saved validation sales with the saved fixed-origin forecasts, never the final holdout. Three forecast-driven policies share an order-up-to rule; a fourth is a fixed reorder-point comparator. Every assumption was frozen before any result. Costs are in normalised cost units, NCU, not currency, and I never call differences savings. The simulation covered 544 cases on the full populations, 8.4 million series-episodes, and its arithmetic was independently replayed; in the final audit I re-aggregated every base result from the raw outputs with zero discrepancy.

<!-- Slide number: 15 -->
Better forecasts did not reliably lower simulated cost

### Chart: Store Item: NCU per series-episode

| Category | ML minus MA28 | ML minus seasonal naive |
| --- | --- | --- |
| Origin 1 | -915.78 | -200.3 |
| Origin 2 | -598.09 | -158.19 |
| Origin 3 | -375.92 | 112.83 |
| Origin 4 | 385.21 | -23.43 |

### Chart: M5: NCU per series-episode

| Category | ML minus MA28 | ML minus seasonal naive |
| --- | --- | --- |
| Origin 1 | 0.4 | -16.76 |
| Origin 2 | 2.35 | -9.47 |
| Origin 3 | 1.66 | -5.87 |
| Origin 4 | 3.18 | -11.95 |

Pooled: Store Item ML−MA28 −376.14 (−5.86%), ML − seasonal naive −67.27 (−1.10%); M5 ML−MA28 +1.90 (+0.85%), ML − seasonal naive −11.01 (−4.69%). Hypothetical NCU, not savings.
15

### Notes:
Each bar is Selected ML minus a baseline at one origin, so below zero means ML was cheaper. On Store Item, ML is cheaper than MA28 at the first three origins but costlier at origin 4, even though it is more accurate there; 473 of 500 series cost more. Against the stronger seasonal-naive baseline the pooled advantage is only 1.1 percent and it reverses at origin 3. On M5 the more accurate random forest is costlier than MA28 at all four origins, though cheaper than seasonal naive. The reason is that an order-up-to policy reacts to the forecast level, not just its error.

<!-- Slide number: 16 -->
The cheapest rule simply holds less stock and serves less

| Policy | Store Item cost (NCU) | Store Item fill | M5 cost (NCU) | M5 fill |
| --- | --- | --- | --- | --- |
| Selected ML | 6,038.44 | 98.38% | 223.82 | 83.92% |
| MA28 | 6,414.59 | 98.38% | 221.92 | 83.40% |
| Seasonal naive | 6,105.72 | 98.38% | 234.83 | 82.75% |
| Fixed ROP | 3,276.44 | 97.68% | 205.14 | 79.56% |

Fixed ROP behaviour
Store Item: orders at 99.9% of reviews; its inventory position (7.3 mean-days) never rises above the 11-day reorder point. Fill below ML in 15 of 17 Store Item and 17 of 17 M5 scenarios.
Sensitivity (17 scenarios)
They reuse the same four origins and forecasts, so they are not independent confirmations: Store Item ML beats MA28 in 17 of 17 pooled scenarios but only 52 of 68 scenario-origin cells. On M5, ML beats MA28 in only 3 of 17.
Source: reports/inventory/post_audit_reconciliation.json (base, pooled over four origins).
16

### Notes:
The fixed reorder point has the lowest cost on both datasets, and it would be easy to call it the winner. The audit showed why that is wrong: on Store Item it orders at essentially every review because its inventory position never reaches the trigger, so it behaves like replenishing one day of demand per day. It holds about half the stock and has lower fill. On M5 its fill rate is about four points lower. I therefore report it as a low-stock, lower-service comparator, not as a better policy. A properly tuned (s, S) policy is listed as future work.

<!-- Slide number: 17 -->
Scientific limitations
Censored demand
Selection optimism
Limited seasons
Sales understate demand when stock runs out; lost sales are assumed, not observed.
Inventory reuses the windows that selected ML; the bias favours ML and is unquantifiable.
Four adjacent origins plus one final window; no significance testing.
Hypothetical costs
Small ML samples
External validity
NCU and frozen assumptions; no realised savings or prices.
Six training labels per M5 series per origin; bounded compute.
Two public datasets; no claim of universal ranking or transfer.
17

### Notes:
I want to be explicit about what this evidence cannot support. Sales are censored: a zero may be a stock-out rather than no demand. The inventory study reuses the validation windows that selected the ML models, which biases it in favour of ML; I cannot quantify that bias because the holdout is spent, which is why the M5 result, where ML still was not cheaper, is the more informative one. Four adjacent origins and correlated series do not support significance tests. Costs are hypothetical. And the results come from two public histories, so I make no claim of a universal ranking.

<!-- Slide number: 18 -->
Application architecture
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\figures\fig_architecture.png](Image 0)
Security by design
No credentials in the browser; read-only database roles; protected engine; validation and rate limiting; generic errors; security headers and HSTS.
Stack
Next.js 16 · FastAPI (Python 3.14) · Supabase PostgreSQL 17 · Vercel (Frankfurt) · Power BI report from the same evidence.
18

### Notes:
The research is delivered as a public application. The browser talks only to the Next.js web app on Vercel. The web app reads evidence from Supabase PostgreSQL through a read-only role and calls a separate FastAPI service that wraps the byte-identical frozen Phase 5 engine. That engine is protected: it accepts requests only with a shared key and Vercel's protection bypass, and anonymous requests get 401. Crucially, the user can never send demand data: the engine loads saved sales and forecasts itself, so the app can only run the verified simulator on approved inputs.

<!-- Slide number: 19 -->
Live demonstration: idf-web.vercel.app
Executive Overview: evidence labels and headline results
Forecast Explorer: one series, three models vs actuals
Inventory Planner: base run equals saved Phase 5 totals
Custom scenario: lead 3 days, penalty 25 NCU
Scenario Comparison: Store Item origin-4 reversal
Research: protocol, audit and limitations
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\screenshots\planner_totals.png](Image 0)
Live engine totals (left) equal the saved Phase 5 totals (right) for this series and origin.
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\screenshots\overview_top.png](Image 1)
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\screenshots\forecasts_top.png](Image 2)
Fallback if the network fails: Appendix slide 24 and the Power BI report.
19

### Notes:
DEMO SCRIPT (about four minutes). One: open idf-web.vercel.app on the Executive Overview and point out the three evidence labels: validated, reported and hypothetical. Two: open the Forecast Explorer, choose a Store Item series and origin, and show the 28-day forecasts of the three models against actual sales. Three: click through to the Inventory Planner with that series, run the base scenario and show that the four totals equal the saved Phase 5 values in the comparison column. Four: change the lead time to 3 and the unmet-demand penalty to 25, run again, and note that the page labels it a custom hypothetical scenario. Five: open Scenario Comparison to show the origin-4 reversal. Six: end on the Research page, which lists limitations and the sealed holdout. Fallback if the network fails: use the screenshots on appendix slide 24 or the Power BI report.

<!-- Slide number: 20 -->
Production verification
21 / 21
2,555
15 / 15
API responses byte-identical to the local reference
NCU: Selected ML total for the reference series through the production stack (MA28 2,772; seasonal naive 2,900; fixed ROP 1,309), equal to Phase 5
page × width browser checks: no overflow, no serious accessibility issue
Defects found and fixed
Not tested in production
Float rounding: Supabase's extra_float_digits = 0 changed results for 182 of 3,200 pairs (fixed with binary floats and exact-output transactions). TLS: a connection option rejected by the server, now applied client-side.
Real engine outage; real database outage or pause; protection of a built preview deployment. Covered by local tests only.
20

### Notes:
Before calling the deployment done I verified it against the local reference. All 21 API responses I compared, including three simulations and the CSV export, were byte-identical. Getting there required fixing two real defects. First, Supabase rounds floating-point text to 15 digits, which silently changed integer inventory results for 182 of 3,200 series-origin pairs; requiring exact parity is what exposed it, and it was fixed in both the engine and the web API. Second, a TLS option in the database connection string was being forwarded to the server and rejected; it is now applied on the client. Three things were not tested in production, and I do not claim them: a real engine outage, a real database outage and protection of a built preview deployment.

<!-- Slide number: 21 -->
Research contributions
Governed benchmark
Full populations
Decision-aware analysis
Frozen, fingerprinted selection; sealed holdout read once.
All 500 and 30,490 series; no convenient subsets for claims.
Accuracy versus cost and service, reported where ML does not help.
Reproducibility
Deployed evidence
Limits are part of the result
Hashes, manifests, exact recomputation, independent audit.
Public app serving byte-identical evidence (curated series) and the frozen engine.
21

### Notes:
To summarise the contributions. First, a governed benchmark: a frozen, fingerprinted selection evaluated once on a sealed holdout. Second, full-population evaluation on all 30,490 M5 series, rather than a convenient subset. Third, an honest decision analysis that shows where machine learning does not help, under explicit assumptions. Fourth, reproducibility: hashes, manifests, independent recomputation, and an audit trail. And fifth, a deployed application that serves exactly the recorded evidence.

<!-- Slide number: 22 -->
Conclusions and future work
ML: −57.6% MAE on regular Store Item demand; −1.7% on intermittent M5, and worse on MASE. Accuracy did not reliably lower simulated cost.
Next: a fresh evaluation window · tuned (s, S) policy with service targets · censored-demand models · verified price and event features · probabilistic forecasts · clean-machine reproduction

### Notes:
In conclusion: machine learning gave a large forecasting gain on regular retail demand and only a marginal, metric-dependent gain on intermittent demand, and better accuracy did not reliably lower simulated inventory cost. For future work, the most valuable step is a fresh, untouched evaluation window, which would remove the selection optimism of the inventory study. After that: a tuned (s, S) policy with service targets, explicit censored-demand modelling, verified price and event features, probabilistic forecasts for safety stock, and a clean-machine reproduction.

<!-- Slide number: 23 -->
Thank you. Questions?
Live application: https://idf-web.vercel.app  ·  Evidence, code and audit trail available to examiners on request

### Notes:
Thank you. I am happy to take questions. Likely questions and short answers: Why price-free? Publication latency of prices was unverified, so using them risked leakage. Why is Fixed ROP cheapest? It holds less stock and serves less; it is a degenerate comparator. Is the 57.6% significant? I make no significance claim: it is one window, but the direction was consistent across all four validation origins. Why not tune more? The holdout is spent; any new model could only be compared on reused windows.

<!-- Slide number: 24 -->
Appendix: the deployed application (production, 2026-11-12)
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\screenshots\overview_top.png](Image 0)
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\screenshots\forecasts_top.png](Image 1)
Executive Overview
Forecast Explorer
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\screenshots\planner_top.png](Image 2)
![C:\Users\RTX\Desktop\Intelligent Demand Forecasting & Inventory Optimisation\final_submission\screenshots\scenarios_top.png](Image 3)
Inventory Planner
Scenario Comparison
Screenshots from https://idf-web.vercel.app at 1280 px width, captured during production QA (reports/webapp/phase7d/browser_prod).
24

### Notes:
Backup slide for the live demonstration. If the network or the Supabase project is unavailable, walk through these production screenshots in the same order as the demo script: Executive Overview, Forecast Explorer, Inventory Planner, Scenario Comparison.
