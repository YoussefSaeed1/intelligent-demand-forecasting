# Phase 8 backup and integrity report

Date: 2026-11-13. Builder: `final_submission/_tools/make_final_backup.py`.

## Final backup (VERIFIED, same device)

| Item | Value |
|---|---|
| Location | `C:\Project_Backups\Demand_Forecasting_Phase8_Final_verified_20261113_0022` |
| Kind | **Local backup on the same laptop: NOT an off-device copy** |
| Repository state | Git bundle `repository_main_6c2aa24.bundle` (20.5 MB, all refs; `main` = `6c2aa24`, the Phase 8 deliverables commit). The one uncommitted change at build time was the builder's own byte-exact SHA256SUMS fix, which is included in `files/` and committed afterwards |
| Contents | 567 files plus the bundle; 131.6 MB in total: `final_submission`, `docs`, `configs`, Phase 4 frozen selection, final metrics, holdout ledger, execution contract and code snapshot, Phase 5 plan and execution, inventory, data-quality, EDA and Power BI reports, webapp export CSVs and Phase 7D evidence, Power BI PBIP source |
| Excluded | Raw Kaggle data (`data/raw`, `data/processed`), virtual environments, `node_modules`, build caches, `.env` files, PBIX binaries, Power BI `cache.abf` and `localSettings.json`, and the 6.5 GB Phase 4/5 model and prediction evidence (held in the verified Phase 4 and Phase 5 backups) |
| Manifest | `BACKUP_MANIFEST.json` (per-file path, bytes, SHA-256) and `SHA256SUMS.txt`; SHA-256 of `SHA256SUMS.txt` = `772d627c99c04dde553efa9011d7c79ab74ae8f4051e160185265cce61f0d281` |

### Read-back verification (separate script, after the build)

- 568 of 568 entries re-hashed from the destination bytes: 0 mismatches against `SHA256SUMS.txt` and 0 against the manifest.
- The SHA-256 of `SHA256SUMS.txt` equals the manifest value; the file uses LF line endings.
- `git bundle verify` passed; a clone of the bundle checks out `6c2aa24`; `git fsck` passed; the paper is present in the clone.
- Critical files present: paper, presentation, review record, traceability, frozen selection (`a71ab187…`), holdout ledger (`fa2af529…`), Phase 5 reconciliation and plan.
- Secret-pattern scan of every text file: 0 hits (database URLs with passwords, private keys, live API keys, JWT-like tokens, bypass headers).

### Build history (disclosed)

Two earlier attempts in this session (`…_0019`, `…_0021`) were superseded and then deleted:

- **`…_0019`:** the secret scanner matched its own pattern text (a false positive).
- **`…_0021`:** Windows newline translation made `SHA256SUMS.txt` differ from its manifest hash (the content was correct when normalised to LF).

Both builder defects are fixed. No pre-existing backup was modified.

## Existing backups (re-verified 2026-11-12, same device)

| Backup | Files | Result |
|---|---|---|
| `Demand_Forecasting_Phase4_Evidence_verified_20261108` (4.9 GB) | 4,592 | 0 missing or mismatched |
| `Demand_Forecasting_Phase5_Evidence_verified_20261108` (1.6 GB) | 2,593 | 0 missing or mismatched |
| `Demand_Forecasting_Phase6_PBIP_verified_20261110` | 129 | 0 missing or mismatched |
| `Demand_Forecasting_Phase7C_WebApp_verified_20261112` | 208 | 0 missing or mismatched |

`Demand_Forecasting_Phase4_Evidence` (5 KB) is the receipt of a failed first attempt from 2026-11-08 (0 files copied); the
verified copy sits beside it.

## Off-device status: OPEN (audit finding F-02)

All backups are on the laptop's internal drives (C: and D: are both fixed internal disks). OneDrive Personal is signed
in, but nothing was uploaded: copying project data to a cloud service needs the owner's explicit authorisation.

**One manual action for the owner.** Copy these three folders to an external USB drive or another cloud account:

- `C:\Project_Backups\Demand_Forecasting_Phase8_Final_verified_20261113_0022` (131.6 MB)
- `C:\Project_Backups\Demand_Forecasting_Phase4_Evidence_verified_20261108` (4.9 GB)
- `C:\Project_Backups\Demand_Forecasting_Phase5_Evidence_verified_20261108` (1.6 GB)

Then verify the copy from the project root:

```powershell
.\.venv\Scripts\python.exe final_submission\_verification\verify_backups.py verify_copy.json E:\Project_Backups
```

(`E:` stands for the drive letter; the script re-hashes the Phase 4, 5, 6 and 7C backups.) For the Phase 8 folder,
re-hash it against its `SHA256SUMS.txt`. F-02 can be closed only after that verification passes on the off-device copy.
