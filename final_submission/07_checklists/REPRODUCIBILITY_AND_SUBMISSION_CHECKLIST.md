# Reproducibility and submission checklist

Status as of 2026-11-12. A box is ticked only where the item was executed and verified.

## A. Scientific evidence

- [x] Raw and canonical data unchanged: 9 of 9 SHA-256 match the freeze record.
- [x] Selection fingerprint `a71ab187…` reproduces; holdout ledger has 12 events with the chain intact.
- [x] Phase 5 plan (`63efc59e…`) and execution (`b55ba4a0…`) freezes are unchanged (all 544 case records carry these hashes).
- [x] Validation MAE of selected and baseline models recomputed from saved forecasts (difference 0.0).
- [x] Phase 5 base results re-aggregated from raw outputs (difference 0.0).
- [x] Vendored engine identical to the frozen Phase 5 engine (`vendor_engine.py --check`).
- [x] No retraining, no final-holdout read and no evidence edit during Phase 8.
- [ ] Clean-machine retraining reproduction (optional; audit finding F-10, open).

## B. Software and deployment

- [x] Public application live: https://idf-web.vercel.app (`36da979`); engine `9a13fab`, protected.
- [x] Production QA: 21/21 byte-identical API responses, browser 15/15, security checks PASS.
- [x] Dependency audit: web production dependencies 0 vulnerabilities; engine pins 0 known vulnerabilities.
- [ ] Production outage behaviour (engine or database) and built-preview protection (not tested by design).

## C. Academic deliverables (`final_submission/`)

- [x] `03_paper/IDF_Research_Paper.docx`: 23 pages, about 7,100 words, 16 tables, 11 figures, 22 references. Opens in
  Word 16; TOC updated; rendered and inspected after the review fixes.
- [x] `04_presentation/IDF_Viva_Presentation.pptx`: 24 slides (23 plus an appendix) with speaker notes. Schema
  validation passed; rendered in PowerPoint 16 and inspected after the review fixes.
- [x] `05_speaker_notes/SPEAKER_NOTES_AND_DEMO_SCRIPT.md`: notes, demo script and Q&A.
- [x] `01_audits/`: scientific audit, technical and security audit, second-pass review by two separate AI contexts
  (all findings dispositioned).
- [ ] External validation by the supervisor or examiners (AI reviews do not substitute for it).
- [x] `02_traceability/EVIDENCE_TO_CLAIM_TRACEABILITY.md`.
- [x] `06_portfolio/PORTFOLIO_SUMMARY.md`: publication-safe, private, not published.
- [x] References verified (22 of 22).
- [ ] Owner to fill in the supervisor name on the paper's title page.
- [ ] Owner to confirm the required format and length with the programme regulations (not available in the repository).
- [ ] **Owner's recorded review of the Kaggle competition data-use terms (open since Phase 1).** It now also covers
  whether the public demonstrator may display curated daily sales (review finding R-01). Restricting the app would
  be a production change that needs separate approval.
- [ ] Owner to check whether the programme requires a declaration-of-originality page.

## D. Preservation

- [x] Existing local backups re-verified: Phase 4 (4,592 files), Phase 5 (2,593), Phase 6 PBIP (129), Phase 7C (208), 0 problems.
- [ ] Final Phase 8 local backup with Git bundle and SHA-256 manifest, verified (see `08_backup/BACKUP_REPORT.md`).
- [ ] **Off-device copy verified** (see the backup report for status; required before submission).

## E. Before the viva

- [ ] Open the application 10 minutes beforehand (Supabase Free may pause when idle).
- [ ] Check `/api/v1/health`: `status ok` and `engine.reachable true`.
- [ ] Have the screenshots and the Power BI report ready as fallbacks.
- [ ] Rehearse the demo with the script in `05_speaker_notes`.
