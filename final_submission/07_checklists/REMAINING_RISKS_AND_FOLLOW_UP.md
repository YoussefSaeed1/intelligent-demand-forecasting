# Remaining risks and recommended follow-up

| # | Risk | Severity | Owner action | Effort |
|---|---|---|---|---|
| 1 | **No complete off-device copy of the 6.5 GB frozen Phase 4/5 evidence** (models, predictions, simulation outputs). Only the laptop holds them. | High for submission | Copy `C:\Project_Backups\Demand_Forecasting_Phase4_Evidence_verified_20261108` and `..._Phase5_Evidence_verified_20261108` to an external drive. Then run `final_submission\_verification\verify_backups.py` against the copy (point the script's `B` folder at the drive). | 15 min |
| 2 | Off-device copy of the essential Phase 8 package | Medium | See `08_backup/BACKUP_REPORT.md`; OneDrive copy only with owner authorisation | 5 min |
| 3 | Supabase Free project pauses when idle; the demo would return 503 | Medium (viva) | Open the app 10 minutes before the viva; resume the project in the Supabase dashboard if paused | 2 min |
| 4 | Untested production outage behaviour (engine, database) and built-preview protection | Low | Optional: test in a planned window after submission; never during the viva | 30 min |
| 5 | Supervisor name and programme formatting rules not available in the repository | Medium | Fill in the title page; adjust length or format if the regulations differ | 15 min |
| 6 | Kaggle data-use terms review not recorded since Phase 1 | Low | Record that both competitions' rules permit academic use; never redistribute the data | 10 min |
| 7 | Dev-only vulnerable tooling (vitest, typescript-eslint) | Low | Upgrade in a separate change after submission | 30 min |
| 8 | Database TLS without certificate pinning | Low | Optionally move to `verify-full` with the Supabase CA after submission | 30 min |
| 9 | Paired secret rotation (engine key, bypass secret) | Low | Rotate both projects together; keep the runbook | n/a |
| 10 | Clean-machine retraining reproduction untested (F-10) | Low | Optional follow-up research task | hours |
| 11 | Stale status text in some historical documents (scientific audit section 4) | Low | Leave historical documents unchanged; point examiners to the Phase 8 audit | n/a |

## Scientific follow-up (future work, not required for submission)

1. A fresh, untouched evaluation window to remove the selection optimism of the inventory study.
2. A properly tuned (s, S) comparator with explicit service-level targets.
3. Censored-demand modelling (stock-out-aware estimation).
4. Price and event features under verified publication-availability assumptions.
5. Probabilistic forecasts for safety-stock decisions.
