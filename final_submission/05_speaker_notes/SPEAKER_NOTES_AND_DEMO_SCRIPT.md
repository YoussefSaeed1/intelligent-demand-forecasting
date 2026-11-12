# Speaker notes and live demonstration script

Generated from the speaker notes embedded in `04_presentation/IDF_Viva_Presentation.pptx` (24 slides: 23 for the talk, about 20 minutes plus questions, and one appendix slide of production screenshots as the demo fallback). Every number is traceable to `02_traceability/EVIDENCE_TO_CLAIM_TRACEABILITY.md`.

Timing guide: slides 1-3 (3 min), 4-6 data (3 min), 7-10 method (4 min), 11-13 results (3 min), 14-17 inventory and limits (4 min), 18-20 application and demo (5 min including the live demo), 21-23 close (2 min). Slide 24 is a backup slide.

## Slide 1: 

Good morning. My project asks a simple business question with a careful scientific answer: does machine-learning forecasting beat simple rules for daily retail demand, and what would that mean for inventory? I tested this on two public retail datasets under one governed protocol, evaluated the final models exactly once on a sealed holdout, simulated four replenishment policies, and deployed the evidence as a public research application. I will spend about twenty minutes and then take questions.

## Slide 2: 

Retailers reorder thousands of store-item combinations every day. Too little stock loses sales; too much ties up capital. Both mistakes start with the demand forecast. Machine learning is often promoted as the fix, but claims are hard to compare because studies use different data, horizons and error measures. My two datasets have opposite characters: Store Item is regular and seasonal; M5 from Walmart is mostly intermittent, with almost seven in ten days showing zero sales. That contrast is what makes the comparison informative. One caveat from the start: the data record sales, not demand, and contain no stock or cost data, so the inventory part is a hypothetical simulation.

## Slide 3: 

These four questions come directly from the project proposal. RQ1 is the core benchmark. RQ2 asks which data and feature choices matter, for example whether prices can be used safely. RQ3 asks whether a ranking found on one dataset holds on a very different second dataset. RQ4 moves from accuracy to decisions: how do simulated cost and service respond to the forecast and to the assumed operating parameters? Out of scope were causal business claims, reconstructing real stock and any claim of real savings.

## Slide 4: 

Store Item from Kaggle has 500 series over five years with complete coverage and only a single zero. M5 is Walmart data: 30,490 series, 59 million daily rows, and highly concentrated volume, where the top ten percent of products carry over half the units. M5 has weekly prices, but a fifth are missing, almost always before a product's first sale. Both datasets were converted into one canonical schema with unique keys, and all source hashes were re-verified in the final audit. I never merged the two sources or treated them as one population.

## Slide 5: 

Exploratory analysis used only the training prefix, so nothing about the validation or final windows could leak into design choices. Using the Syntetos-Boylan-Croston ADI and CV-squared scheme, all 500 Store Item series are smooth, while three quarters of M5 series are intermittent and a fifth lumpy, with a few all-zero histories. This single chart explains most of the later results: methods that exploit regular seasonality do well on Store Item, while on M5 a simple average is already hard to beat.

## Slide 6: 

Store Item shows a very stable weekly and annual calendar, with tight bootstrap intervals. For M5, a key finding was about prices: every missing price in the training prefix coincides with zero sales, mostly before a product's first sale. More importantly, I could not verify when prices were published relative to the forecast origin, so using them could leak future information. All final models are therefore price-free. That is my answer to RQ2: the decisive choices were excluding features whose availability is uncertain, keeping zeros and missing values rather than imputing, and evaluating full populations.

## Slide 7: 

Every method forecasts the next 28 days from an origin, without seeing any actual sales in that window. The machine-learning models are global: one model per dataset trained across all series, as a one-step regressor applied recursively, so from day two onwards it uses its own predictions as lags. Features use only data strictly before each target date, and tests deliberately poison future values to prove that the forecasts cannot depend on them. Forecasts are never rounded, are clipped at zero, and every series must receive a forecast.

## Slide 8: 

The evaluation is purely chronological. Training expands: each origin uses everything up to that date, and the next 28 days are the target. There are four validation windows and then the final holdout, which was evaluated only once, after the model choice was frozen. Two caveats I state openly: the four origins are adjacent, so they show variability over a limited season rather than four independent replications, and repeated tuning on the same windows makes validation scores optimistic, which is why the sealed holdout matters.

## Slide 9: 

This is the part of the project I am proudest of. After validation, the selection was frozen in a manifest whose SHA-256 fingerprint covers the chosen models, features, comparators and 89 source files. All final forecasts were sealed before the first holdout read, and each dataset's holdout was read exactly once, recorded in a hash-chained ledger of twelve events. In the final audit I re-verified the fingerprint, the ledger chain and all nine data file hashes. One honest limitation: the ledger timestamps are self-recorded, so this proves order only if the recorder is trusted.

## Slide 10: 

I compared thirteen methods in Phase 3 on the full populations. The baselines matter because they set the bar: naive, seasonal naive and moving averages. Statistical comparators include exponential smoothing, Holt-Winters and the intermittent-demand family: Croston, its bias-corrected SBA variant, and TSB, which updates the demand probability every period. ARIMA and SARIMA were run only on small stratified subsets, so I make no population claims about them. In Phase 4 a seeded random search evaluated 23 tuning trials plus four unchanged references, 108 fold runs in total.

## Slide 11: 

These are the frozen candidates at the four validation origins. On Store Item, LightGBM is lowest at every origin, around 6.3 units per day, against 9.2 for seasonal naive. Interestingly, tuning did not improve LightGBM: its initial configuration stayed best. On M5 the lines almost touch: the random forest is about 1.3% better than MA28 on average and lower at all four origins, yet MA28 still wins the majority of individual series at every origin. So on M5 the mean advantage is real but small.

## Slide 12: 

This is the single final assessment on the sealed window. On Store Item the selected LightGBM achieved a mean absolute error of 5.43 units per day against 12.81 for seasonal naive: a 57.6 percent reduction. On M5 the selected random forest achieved 1.047 against 1.066 for MA28: only 1.7 percent. The selections were not changed after seeing these results, and on both datasets the frozen choice also happened to have the lowest final MAE among the predeclared candidates. That answers RQ1 and RQ3: machine learning ranked first on both, but the size of the gain did not transfer.

## Slide 13: 

Here every bar is the percentage difference from MA28 on the final holdout, so below zero is better. The random forest wins on MAE, RMSE, WAPE and RMSSE, but it loses on macro MASE, where both MA28 and TSB are better. Scaled metrics change how much each series counts. I kept the predeclared primary metric and did not switch metrics after seeing results; instead I report all of them. On the saved per-series errors the forest wins 51.3 percent of series, a different pattern from validation, which again warns against strong claims on M5.

## Slide 14: 

To answer RQ4 I built a deterministic, periodic-review, lost-sales simulator and ran it on the saved validation sales with the saved fixed-origin forecasts, never the final holdout. Three forecast-driven policies share an order-up-to rule; a fourth is a fixed reorder-point comparator. Every assumption was frozen before any result. Costs are in normalised cost units, NCU, not currency, and I never call differences savings. The simulation covered 544 cases on the full populations, 8.4 million series-episodes, and its arithmetic was independently replayed; in the final audit I re-aggregated every base result from the raw outputs with zero discrepancy.

## Slide 15: 

Each bar is Selected ML minus a baseline at one origin, so below zero means ML was cheaper. On Store Item, ML is cheaper than MA28 at the first three origins but costlier at origin 4, even though it is more accurate there; 473 of 500 series cost more. Against the stronger seasonal-naive baseline the pooled advantage is only 1.1 percent and it reverses at origin 3. On M5 the more accurate random forest is costlier than MA28 at all four origins, though cheaper than seasonal naive. The reason is that an order-up-to policy reacts to the forecast level, not just its error.

## Slide 16: 

The fixed reorder point has the lowest cost on both datasets, and it would be easy to call it the winner. The audit showed why that is wrong: on Store Item it orders at essentially every review because its inventory position never reaches the trigger, so it behaves like replenishing one day of demand per day. It holds about half the stock and has lower fill. On M5 its fill rate is about four points lower. I therefore report it as a low-stock, lower-service comparator, not as a better policy. A properly tuned (s, S) policy is listed as future work.

## Slide 17: 

I want to be explicit about what this evidence cannot support. Sales are censored: a zero may be a stock-out rather than no demand. The inventory study reuses the validation windows that selected the ML models, which biases it in favour of ML; I cannot quantify that bias because the holdout is spent, which is why the M5 result, where ML still was not cheaper, is the more informative one. Four adjacent origins and correlated series do not support significance tests. Costs are hypothetical. And the results come from two public histories, so I make no claim of a universal ranking.

## Slide 18: 

The research is delivered as a public application. The browser talks only to the Next.js web app on Vercel. The web app reads evidence from Supabase PostgreSQL through a read-only role and calls a separate FastAPI service that wraps the byte-identical frozen Phase 5 engine. That engine is protected: it accepts requests only with a shared key and Vercel's protection bypass, and anonymous requests get 401. Crucially, the user can never send demand data: the engine loads saved sales and forecasts itself, so the app can only run the verified simulator on approved inputs.

## Slide 19: 

DEMO SCRIPT (about four minutes). One: open idf-web.vercel.app on the Executive Overview and point out the three evidence labels: validated, reported and hypothetical. Two: open the Forecast Explorer, choose a Store Item series and origin, and show the 28-day forecasts of the three models against actual sales. Three: click through to the Inventory Planner with that series, run the base scenario and show that the four totals equal the saved Phase 5 values in the comparison column. Four: change the lead time to 3 and the unmet-demand penalty to 25, run again, and note that the page labels it a custom hypothetical scenario. Five: open Scenario Comparison to show the origin-4 reversal. Six: end on the Research page, which lists limitations and the sealed holdout. Fallback if the network fails: use the screenshots on appendix slide 24 or the Power BI report.

## Slide 20: 

Before calling the deployment done I verified it against the local reference. All 21 API responses I compared, including three simulations and the CSV export, were byte-identical. Getting there required fixing two real defects. First, Supabase rounds floating-point text to 15 digits, which silently changed integer inventory results for 182 of 3,200 series-origin pairs; requiring exact parity is what exposed it, and it was fixed in both the engine and the web API. Second, a TLS option in the database connection string was being forwarded to the server and rejected; it is now applied on the client. Three things were not tested in production, and I do not claim them: a real engine outage, a real database outage and protection of a built preview deployment.

## Slide 21: 

To summarise the contributions. First, a governed benchmark: a frozen, fingerprinted selection evaluated once on a sealed holdout. Second, full-population evaluation on all 30,490 M5 series, rather than a convenient subset. Third, an honest decision analysis that shows where machine learning does not help, under explicit assumptions. Fourth, reproducibility: hashes, manifests, independent recomputation, and an audit trail. And fifth, a deployed application that serves exactly the recorded evidence.

## Slide 22: 

In conclusion: machine learning gave a large forecasting gain on regular retail demand and only a marginal, metric-dependent gain on intermittent demand, and better accuracy did not reliably lower simulated inventory cost. For future work, the most valuable step is a fresh, untouched evaluation window, which would remove the selection optimism of the inventory study. After that: a tuned (s, S) policy with service targets, explicit censored-demand modelling, verified price and event features, probabilistic forecasts for safety stock, and a clean-machine reproduction.

## Slide 23: 

Thank you. I am happy to take questions. Likely questions and short answers: Why price-free? Publication latency of prices was unverified, so using them risked leakage. Why is Fixed ROP cheapest? It holds less stock and serves less; it is a degenerate comparator. Is the 57.6% significant? I make no significance claim: it is one window, but the direction was consistent across all four validation origins. Why not tune more? The holdout is spent; any new model could only be compared on reused windows.

## Slide 24: 

Backup slide for the live demonstration. If the network or the Supabase project is unavailable, walk through these production screenshots in the same order as the demo script: Executive Overview, Forecast Explorer, Inventory Planner, Scenario Comparison.

## Live demonstration script (detailed)

Preparation (10 minutes before): open https://idf-web.vercel.app once so the Supabase Free project is awake; confirm `/api/v1/health` shows `status ok` and `engine.reachable true`; keep the Power BI report and appendix slide 24 ready as fallbacks.

1. **Executive Overview** (30 s). Point to the three evidence labels: *Validated* (validation origins), *Reported* (sealed final holdout, never recomputed) and *Hypothetical* (inventory costs in NCU). Read the two headline cards: Store Item LightGBM validation MAE 6.308; M5 random forest 1.0201.
2. **Forecast Explorer** (60 s). Store Item, series `store_item|1:11`, origin 1. Show the 84-day history, the 28 actual days and the three model forecasts; note the per-series MAE for each model and that the window ends before the final holdout.
3. **Inventory Planner** (60 s). Click through with the same series and origin. Run the base scenario. Show the four totals and the *Saved Phase 5* column: they are equal (2,555 / 2,772 / 2,900 / 1,309 NCU for Selected ML, MA28, seasonal naive and fixed ROP). The live result comes from the protected engine, which loads the saved sales itself.
4. **Custom scenario** (45 s). Set lead time 3 days and unmet-demand penalty 25 NCU; run. The page labels it a custom hypothetical scenario with no published reference. Export the CSV to show the NCU caveat line.
5. **Scenario Comparison** (30 s). Store Item, origin filter 4: show that Selected ML is costlier than MA28 at origin 4 although it is more accurate.
6. **Research and Methodology** (15 s). Show the protocol, the audit findings and the limitations list; the final holdout is presented as reported values only.

Scope to state if asked: the application exposes curated series only (all 500 Store Item and 300 of 30,490 M5 series). Fallbacks: if the engine is unavailable the planner shows a labelled fallback to the saved Phase 5 results (designed behaviour). If the network fails, use appendix slide 24 and the Power BI report.

## Anticipated examiner questions

| Question | Short answer | Evidence |
|---|---|---|
| Why are the M5 models price-free? | Price publication latency relative to the forecast origin could not be verified, so using prices risked leakage. Phase 3 price-enabled runs are conditional references only. | PHASE4_FEATURE_AVAILABILITY.md |
| Is the 57.6% Store Item improvement significant? | No significance claim; one final window. The direction was the same at all four validation origins. | Paper Tables 6 and 8 |
| Why is fixed ROP the cheapest? | It holds about half the stock and serves less; on Store Item it degenerates into daily one-day replenishment. | Audit F-03; paper Table 11 |
| Why does a more accurate forecast cost more? | Order-up-to policies react to the forecast level; a higher-level but more accurate forecast builds more stock. | Paper Section 9.2 |
| Could the holdout have influenced selection? | The selection was fingerprinted before the read, forecasts were sealed, and each holdout was read once (12-event ledger). Limitation: timestamps are self-recorded. | Audit F-08 |
| Who audited the work? | An AI-assisted review in a separate context (2026-11-10) and a Phase 8 second-pass review; neither is an external human examination. | 01_audits/ |
| Why not add a better model now? | The holdout is consumed; any new model could only be compared on reused validation windows. | Audit section 9 |
| What does NCU mean? | Normalised hypothetical cost units from frozen assumptions; not currency and never savings. | PHASE5_ASSUMPTIONS.md |
| May the app display Kaggle sales? | Raw files are not redistributed; the demonstrator shows curated daily sales. The owner's review of the competitions' data-use terms is pending (open checklist item). | DATASETS.md; checklist |
