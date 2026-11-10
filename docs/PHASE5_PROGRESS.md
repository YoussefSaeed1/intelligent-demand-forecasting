# Phase 5 progress

5A COMPLETE: immutable protocol, mathematics, assumptions and 17 scenarios; eight
full-population validation cohorts, four policies and 24 saved forecast sources.
Plan: artifacts/inventory/phase5/plan.json; original model selection unchanged.

5B COMPLETE: deterministic lost-sales engine; 26 original design/engine tests plus
15 subsequent adversarial input/publication/report tests. Hand reference examples:
H3, L0, demand=2, initial=0 => receipts [0,2,2], fulfilled=4, unmet=2, cost=22;
H5, L1, demand=1, initial=0 => receipts [0,0,2,0,1], cost=23. Synthetic correctness
is not empirical policy performance. The initial full-suite attempt had a Windows
access-denied disposable-fixture failure (423 passed/1 failed); a fresh retry passed
424. Original failed log/fixture retained; exact OS cause unconfirmed.

5C COMPLETE: smoke then 32 base cases; 495,840 series episodes and 13,883,520
full daily events. Base runtime 77.141 seconds, peak working set 958,377,984 bytes.
Independent base gate passed before sensitivity execution. No final holdout use.

5D sensitivity execution COMPLETE: 512 additional cases, 306.175 seconds,
peak working set 972,214,272 bytes. All 544 cases independently audited:
8,429,280 series episodes; 13,969,536 retained daily events; 3,264 scalar
reference episodes. Every series is evaluated in every scenario. Additional
persisted-only ratio/order/stockout/position checks passed. Ten PNG/SVG figure
pairs and an offline report were built; 35 local links and 136 aggregated scenario
rows validated. Images decoded and were visually inspected; browser rendering
was not performed. Final gate details are in PHASE5_COMPLETION_CHECKLIST.md.

Audit replay correction: fractional stress exposed a ceiling boundary when the
independent scalar reference reassociated S-IP as S-stock-pipeline. It now follows
the declared IP=stock+pipeline grouping. Production code/results and numerical
check tolerances were unchanged; all scalar episodes reconcile. Near-integer
fractional quantities retain the declared deterministic raw-ceiling convention.

No fit, tune, new forecast selection, final target scan, ledger append, commit,
push or Phase 6/7 work. The broader independent Claude audit has since been completed (CONDITIONAL); see
PHASE5_AUDIT_RESPONSE.md.
