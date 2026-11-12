# Phase 7A: UI and UX specification

Target audience: academic reviewers, hiring managers and analytics practitioners. The product reads like an
enterprise analytics application with explicit scientific guard-rails, and it adds something Power BI did not
offer: interactive scenario planning on the validated engine.

## 1. Minimum viable feature set (MVP)

| Area | In MVP | Deferred |
|---|---|---|
| Overview | Headline cards per dataset, origin-robustness chart, policy cost/service table, key caveats | Animated tour |
| Forecast Explorer | Dataset, series search, origin selector; history + actual + three forecasts chart; per-model metric table; pattern badge; origin tabs | Horizon-step error breakdown |
| Inventory Planner | Series + origin pick, forecast source(s), policy toggles, parameter sliders with Phase 5 defaults, run, trajectory chart, replenishment table, cost/service summary, "compare with the published study" when applicable | Saved scenarios (needs auth), run history |
| Scenario Comparison | 17-scenario matrix (full population), scenario x origin differences, cost-vs-fill scatter, policy descriptions | Custom multi-series batch runs |
| Research | Objectives, datasets, protocol, selection, assumptions, key results, audit findings, limitations, reproducibility, provenance, GitHub link placeholder | PDF export of the page |
| Export | PNG of any chart (client), CSV of a planner run | Shareable permalinks of runs |

## 2. Navigation and layout

Top navigation with five items: Overview, Forecast Explorer, Inventory Planner, Scenario Comparison, Research.
A persistent right-aligned evidence badge ("Validation origins only", "Hypothetical NCU") and a footer with
export version, engine version and the limitation link.

Layout grid: 12 columns, max width 1280 px, 24 px gutters; cards with 8 px radius and 1 px `#DCE3EA` border;
page background `#F4F6F8`, card background `#FFFFFF`.

Responsive breakpoints: ≥1280 desktop (3 or 4 cards per row, chart + side panel), 768 to 1279 tablet (2 per row,
panels stack under charts), <768 mobile (1 per row, sliders full width, tables become key-value lists with
horizontal scroll for matrices).

## 3. Design tokens (continuation of the Phase 6 theme)

| Token | Value | Use |
|---|---|---|
| `--ink` | `#14213D` | headings, body text |
| `--ink-muted` | `#3D4B5C` | secondary text |
| `--brand` | `#1F4E79` | primary actions, selected ML series |
| `--accent` | `#2A9D8F` | teal accents, MA28 series, positive emphasis |
| `--neutral` | `#8FA3B8` | Seasonal Naive series, borders of charts |
| `--amber` | `#E9A23B` | Fixed reorder point, caution |
| `--danger` | `#C0504D` | errors, "not savings" notices |
| `--bg` / `--surface` | `#F4F6F8` / `#FFFFFF` | page / cards |
| Typography | Inter (or system UI), 16 px base; headings 28/22/18 px semibold | WCAG AA contrast ≥ 4.5:1 on all text |
| Numbers | tabular figures; MAE 4 dp, WAPE and fill 2 dp %, NCU 2 dp with thousands separator, differences signed | Consistent with the dashboard |

Series colour mapping is fixed across every chart: Actual = ink, Selected ML = brand, MA28 = accent, Seasonal
Naive = neutral, Fixed ROP = amber. Legends always show the policy or model name, never a key.

## 4. Page specifications

### Overview
Hero statement (one sentence of what the project is), two dataset panels (series count, selected model,
validation MAE and change vs both baselines, simulated cost change vs both baselines in NCU %), origin
robustness bar chart (both datasets), policy cost and service table, three evidence cards (what is validated,
what is reported, what is hypothetical), link to Research.

### Forecast Explorer
Left panel: dataset toggle, series search (debounced, 50 results), pattern filter, origin tabs. Main: line
chart of 84 days history + 28-day validation window with actual and three forecasts; vertical origin marker;
shaded validation window labelled "fixed-origin forecasts, not daily refreshed". Below: metric table per model
(MAE, RMSE, WAPE, bias, MASE, RMSSE) with tooltips defining each; a panel comparing the series to its
pattern's population aggregate. Empty state when no series is selected; skeleton loaders; "M5: 300 curated of
30,490" notice.

### Inventory Planner
Three-step flow on one page: 1) pick series and origin (defaults to the Explorer selection), 2) choose
forecast sources and policies, adjust parameters with sliders and numeric inputs (Phase 5 base defaults,
reset button, "matches published scenario: base" indicator), 3) run. Results: trajectory chart (on-hand,
pipeline, demand, orders as markers) per policy with a policy switcher; replenishment table; summary cards
(total NCU, fill rate, stockout days, average on-hand, orders); comparison strip versus MA28; study reference
when the scenario is a frozen one. Fixed reorder point card carries the fixed label "low-stock comparator,
lower service". Loading state shows "running the Phase 5 engine"; errors show field messages or a generic
retry.

### Scenario Comparison
Scenario matrix (rows: scenario groups and scenarios; columns: policies; cells: mean NCU per episode) with
dataset toggle and origin filter; difference chart ML vs MA28 and vs Seasonal Naive by scenario; scenario x
origin heat table; cost-vs-fill scatter; a sticky note that the 17 scenarios reuse the same four origins and
are not independent replications.

### Research and Methodology
Long-form page with anchored sections: objectives, datasets, forecasting methodology, validation protocol,
model selection and baselines, inventory assumptions (timing diagram), key results (tables generated from
the same API as the Overview), independent audit summary (12 findings with status), limitations (8), audit
corrections (fixed ROP wording), reproducibility (commands, hashes, export version), GitHub link placeholder.

## 5. States and accessibility

Every data view defines loading (skeletons), empty (explanatory copy and a primary action), error (generic
message, retry, request id) and no-result (filters too narrow) states. Keyboard navigation for all controls,
visible focus rings, ARIA labels on charts with a data table alternative, reduced-motion respect, colour never
the only encoding (line styles and markers differ).

## 6. Copy rules (enforced by review and gate U-05)

Never "savings", "profit", "ROI" or "optimal" for simulated results. Always "hypothetical simulated cost
(NCU)", "validation origins", "saved forecasts", "reported final-holdout result". Fixed reorder point is
always "a low-stock comparator with lower fill rate".
