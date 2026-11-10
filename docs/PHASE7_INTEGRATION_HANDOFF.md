# Phase 7 integration handoff: web application

Phase 7 has not started. This note explains how a web application can reuse the verified outputs
without depending on Power BI visuals and without re-implementing scientific calculations.

## Consume the reporting layer, not the dashboard

The reporting CSVs in `artifacts/powerbi/data/` are the integration contract. Their grains, keys, row
counts and SHA-256 hashes are in `reports/powerbi/data_manifest.json`; columns and lineage are in
[PHASE6_DATA_DICTIONARY.md](PHASE6_DATA_DICTIONARY.md). Regenerate them with
`python -m intelligent_demand.bi.export`, which reads only saved, hash-checked evidence.

Recommended use:

- Load the dimension and fact CSVs into the application's own store (for example DuckDB or SQLite) and
  verify each file hash against the manifest before serving it.
- Compute KPIs exactly as specified in [the dashboard KPI table](PHASE6_POWERBI_DASHBOARD.md#2-kpi-specifications)
  and the [DAX measure catalogue](PHASE6_DAX_MEASURE_CATALOGUE.md): pooled ratios from additive numerators
  and denominators, macro MASE/RMSSE per origin then averaged, and blank results instead of mixing datasets,
  model roles, scenarios or policies.
- Reconcile the application against the same references the dashboard uses. `python -m intelligent_demand.bi.qa A,B`
  runs the data-layer rules without Power BI; port the Layer D reference values (registry metrics, Phase 4
  leaderboard, Phase 5 audit summary, post-audit reconciliation) as API-level tests.

## Rules that must carry over

- Show only validation-origin evidence as analysis. Saved final-holdout results are reported values from
  `FactFinalHoldoutReported`; never recompute or re-evaluate them.
- Label inventory values as hypothetical NCU and never as savings; keep the eight `DimLimitation` statements
  visible wherever results appear.
- Always present selected ML with MA28 and Seasonal Naive, per validation origin, and state that the 17
  scenarios reuse the same four origins.
- Do not train, tune or regenerate forecasts or simulations from the application.

## Practical notes

- The CSVs are git-ignored; a deployment needs either the local evidence or a regenerated export.
- Series-level daily detail covers all Store Item series and only the six predeclared M5 representatives;
  full M5 daily detail would need a new, separately validated export at that grain.
- The off-device evidence backup is still outstanding (audit finding F-02).
