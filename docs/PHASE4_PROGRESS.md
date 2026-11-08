# Phase 4 execution progress

Authorised sequence: 4A protocol → 4B tuning → frozen selection → 4C one-time final
assessment → 4D report/audit preparation. No routine approval between passed gates.

| Milestone | Actual current status |
|---|---|
| Preflight | COMPLETE: clean Phase 3 checkpoint 6e1a407; 320 existing tests passed; all 224 saved evaluations hash-verified; nine source hashes unchanged; installed dependencies and resources inspected |
| 4A protocol | COMPLETE: contract 2bbef5b2cc80b629f21fd520f10380206fcd91038b4f7fc97909b1b9ed8dfe7f; 339 tests, Ruff, pip, source/protocol/config gates passed |
| 4B search | COMPLETE: 27 cases, 108 fold runs and 45,177,440 forecasts independently reconciled; 352 tests, Ruff, pip and protocol/source gates passed |
| Selection freeze | COMPLETE: a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb at 2026-11-07T12:41:37.811576+00:00; 89 scientific code/config/test/protocol files snapshotted; selection event appended before target access |
| 4C final assessment | COMPLETE: eight frozen evaluations / 3,470,880 forecasts; canonical access once per dataset; independent final metrics and 352 tests passed |
| 4D reporting/audit package | COMPLETE: offline academic report; 11 PNG/SVG figure pairs; 22 images and 31 links verified; Ruff/pip/source/protocol gates passed; independent audit inventory prepared |

Initial observed resources: 15.68 GiB physical RAM, 2.66 GiB available, 220.12 GiB free
disk. Initial suite: 320 passed in 90.06 seconds. Installed LightGBM 4.6.0,
scikit-learn 1.9.1, statsmodels 0.15.0, NumPy 2.5.4, Pandas 3.1.1, Arrow 26.0.1.
These measurements describe preflight, not guarantees about later system load.

The 16 key Phase 3 anchor evaluations were freshly recomputed from persisted
predictions and canonical validation rows; they match the committed scientific review.
The frozen search manifest contains 23 tuning configurations and four references,
108 total full-population fold runs. Final targets were inaccessible throughout 4A/4B and were first read only in the authorised frozen 4C assessment.

Smoke worker times: Store Item HW 2.6 s, LightGBM 5.6 s, RF 14.7 s; M5
LightGBM 57.5 s, RF 49.1 s, TSB 21.8 s. Maximum recorded smoke working set/RSS
was 1,193.9 MiB. These include preparation, scoring and persistence, not isolated
estimator costs. Price-free M5 matrices contain 30 columns, with no price/event/SNAP
inputs. The pre-holdout selection is now authorised; the ledger preserves selection freezing, the single canonical assessment per dataset, and explicitly logged later snapshot audit/report reads.

Scientific contract: [PHASE4_OPTIMISATION_PROTOCOL.md](PHASE4_OPTIMISATION_PROTOCOL.md).
All Phase 4 ML is price-free. No raw/canonical file or verified Phase 3 output is
overwritten. Phase 4 development remains uncommitted; no push is authorised.

The first independent 4B audit stopped on a seed-key lookup in the new reporting/audit helper. Validation keeps the seed at the run-specification level; final configuration also carries it locally. The helper now uses the authoritative specification key, with a regression check for both layouts. No model, forecast, raw input or source transformation was changed or rerun. That helper correction was completed before freezing and before any final target access.

Completed search cost: 2,064.91 measured worker seconds; largest monitored RSS 1,239.71 MiB. Independent validation reconciliation took 81.13 seconds and peaked at 1,220.84 MiB OS working set. Store Item selected the unchanged initial LightGBM configuration (no additional search gain); M5 selected price-free RF trial 02, validation MAE 1.020066985. Exact comparators and configurations are frozen, not adjustable after target access.

Final 4C assessment: 26.61 seconds, 1,033.76 MiB OS peak working set. Store Item LightGBM MAE 5.434342531; M5 RF MAE 1.047231371 versus MA28 1.065729312. MA28 has better macro MASE; no objective or frozen choice changed. The 4D gate reuses the successful unchanged-code 4C full-suite run (352 passed in 44.92 seconds), and independently reruns Ruff/pip/source/protocol checks. One report-only long-label wrap was recorded with input and before/after image hashes. Browser rendering is NOT RUN under the file URL policy; file decoding, SVG structure, links and figure inspection passed. No critical/high scientific issue remains in the internally reviewed scope. The independent Claude audit and Phase 5 remain NOT STARTED. No final Git commit or push was created.
