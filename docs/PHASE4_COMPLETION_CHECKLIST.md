# Phase 4 completion checklist

4A, 4B, pre-holdout freeze, 4C and 4D: **COMPLETE**, within the declared research scope. The mandatory independent Claude audit is not performed and Phase 5 is not started.

| Check | Actual result |
|---|---|
| optimisation contract | PASS |
| complete comparable trials | PASS |
| validation prediction reconciliation | PASS |
| training labels features and strata | PASS |
| pre holdout freeze and unchanged scientific snapshot | PASS |
| complete final prediction keys dates | PASS |
| one canonical assessment per dataset | PASS |
| independent final metric reconciliation | PASS |
| source hashes and original protocol | PASS |
| ruff | PASS |
| pytest | PASS |
| pip check | PASS |
| PNG SVG decoding and links | PASS |
| figure visual inspection | PASS |
| browser rendering | NOT RUN |
| scientific generalisability | WARNING |
| independent Claude audit | NOT RUN |
| phase5 | NOT STARTED |
| final Git checkpoint | NOT RUN |

All 27 cases, 108 fold runs, 45,177,440 validation forecasts, eight final evaluations and 3,470,880 final forecasts reconciled. No failed/incomplete experiment entered selection. All final methods delivered complete populations without fallback.

The complete suite passed **352 tests in 44.92 seconds** after the one-time assessment. The 4D gate reused that passing run because all 89 frozen scientific source/configuration/test/protocol files remain byte-identical; Ruff, pip, source/protocol and report checks were separately executed for 4D.

Frozen selection: `a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`. Bundle: `a06bcb32586c359d701b622fd5e2f9090d6ff988e51e98c700a859574abf20f5`. Each dataset has one canonical target-read reservation and one completed assessment; later snapshot reads are separately logged. All nine source hashes remain unchanged.

The offline report contains 11 figures in PNG/SVG pairs: all 22 files and 31 relative links passed. All figures were reviewed in a contact sheet; complex examples and demand-pattern plots were inspected individually. Crowded M5 tick labels were repaired and rechecked using a separately recorded presentation helper. Browser rendering is NOT RUN because file URL navigation was restricted; no browser-access workaround was attempted.

Internal checks found no remaining critical/high scientific defect. Preserve all limitations and metric trade-offs in [PHASE4_SCIENTIFIC_REVIEW.md](PHASE4_SCIENTIFIC_REVIEW.md) and [PHASE4_LIMITATIONS.md](PHASE4_LIMITATIONS.md).

[Offline report](../reports/forecasting/PHASE4_FORECASTING_REPORT.html) ? [Reproducibility](PHASE4_REPRODUCIBILITY.md) ? [Audit package guide](PHASE4_AUDIT_PACKAGE.md).

Git remains on `main` at `6e1a407de0b676e858ffec43bab1fae8d51dae1d`. Phase 4 is intentionally uncommitted. No push, upload, source-data deletion or final Git checkpoint occurred.
